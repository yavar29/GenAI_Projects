"""
Gradio interface for Deep Research Pro.
Provides an interactive web UI for the research assistant.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the project root to Python path if running directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

import gradio as gr
import os
import asyncio
import random
from openai import APIConnectionError, APITimeoutError

from app.core.settings import PROJECT_NAME, OPENAI_API_KEY
from app.core.openai_client import make_async_client

# Ensure OPENAI_API_KEY is in environment for Agents SDK
# The SDK reads from os.environ, not just from dotenv
if OPENAI_API_KEY and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

from app.tools.hosted_tools import get_search_provider
from app.agents.planner_agent import PlannerAgent
from app.agents.search_agent import SearchAgent
from app.agents.writer_agent import WriterAgent
from app.agents.verifier_agent import VerifierAgent
from app.core.render import render_markdown

# Retry backoff times
BACKOFFS = [0.5, 1.0, 2.0, 4.0]

async def with_retry(coro_factory):
    """Retry a coroutine with exponential backoff."""
    for i, b in enumerate(BACKOFFS, 1):
        try:
            return await coro_factory()
        except (APIConnectionError, APITimeoutError):
            if i == len(BACKOFFS):
                raise
            await asyncio.sleep(b + random.random() * 0.25)


async def run_research_stream(
    topic: str,
    num_sources: int,
    provider: str,
    strict_verify: bool,
    use_sdk_planner: bool,
):
    """
    Async generator for research pipeline with hardened client and retry logic.
    Yields status updates and final results - Gradio handles async natively.
    """
    if not topic or not topic.strip():
        yield ("", [], "", "❌ Please enter a research topic")
        return
    
    # Create single hardened OpenAI client for all agents
    openai_client = make_async_client()
    
    # Ensure API key is in environment for Agents SDK
    if OPENAI_API_KEY and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    
    status = ["🔄 Initializing..."]
    yield ("", [], "", "\n".join(status))
    
    try:
        # Check API key if using hosted provider
        if provider == "hosted":
            if not OPENAI_API_KEY:
                yield ("", [], "", "❌ Error: OPENAI_API_KEY not set. Required for 'hosted' provider.\n\nPlease check:\n1. Your .env file exists in the project root\n2. It contains: OPENAI_API_KEY=sk-...\n3. The API key is valid and not expired")
                return
            
            # Verify API key format
            if not OPENAI_API_KEY.startswith(("sk-", "sk-proj-")):
                yield ("", [], "", f"❌ Error: Invalid API key format. Should start with 'sk-' or 'sk-proj-'\n\nCurrent key starts with: {OPENAI_API_KEY[:10] if len(OPENAI_API_KEY) > 10 else 'too short'}...")
                return
        
        web_search = get_search_provider(provider, debug=False)
        
        status.append("📋 Planning research strategy...")
        yield ("", [], "", "\n".join(status))
        
        planner = PlannerAgent(use_sdk=use_sdk_planner, openai_client=openai_client)
        plan = await (planner.plan_async(topic) if use_sdk_planner else asyncio.to_thread(planner.plan, topic))
        
        status.append(f"✅ Planned {len(plan.queries)} search queries")
        yield ("", [], "", "\n".join(status))
        
        status.append(f"🔍 Searching {len(plan.queries)} queries...")
        yield ("", [], "", "\n".join(status))
        
        searcher = SearchAgent(search_func=web_search)
        sources = await searcher.search_many_async(plan.queries, limit_total=num_sources)
        
        status.append(f"✅ Found {len(sources)} sources")
        yield ("", [], "", "\n".join(status))
        
        status.append("✍️ Writing research report...")
        yield ("", [], "", "\n".join(status))
        
        writer = WriterAgent(openai_client=openai_client)
        report = await with_retry(lambda: writer.draft_async(topic, plan.subtopics, sources))
        
        status.append(f"✅ Generated report with {len(report.sections)} sections")
        yield ("", [], "", "\n".join(status))
        
        status.append("🔍 Verifying claims and sources...")
        yield ("", [], "", "\n".join(status))
        
        verifier = VerifierAgent(strict=strict_verify, openai_client=openai_client)
        verification = await with_retry(lambda: verifier.verify_async(report))
        
        status.append(f"✅ Verification complete (confidence: {verification.overall_confidence:.2f})")
        yield ("", [], "", "\n".join(status))
        
        # render + tables
        md = render_markdown(report, verification)
        
        sources_data = []
        for s in sources:
            title = s.title if len(s.title) <= 80 else s.title[:80] + "..."
            sources_data.append([title, str(s.url), s.source_type, s.published or "N/A"])
        
        verification_md = f"# Verification Results\n\n**Overall Confidence:** {verification.overall_confidence:.2f}\n\n## Section Reviews\n\n"
        for r in verification.reviews:
            verification_md += f"### {r.section_title}\n\n- **Confidence:** {r.confidence:.2f}\n- **Reasoning:** {r.reasoning}\n\n"
            if getattr(r, "issues", None):
                verification_md += "**Issues:**\n" + "\n".join(f"- {i}" for i in r.issues) + "\n\n"
            if getattr(r, "metrics", None):
                m = r.metrics
                verification_md += f"**Metrics:**\n- LLM Confidence: {m.llm_conf:.2f}\n- Coverage: {m.coverage:.2f}\n- Quality: {m.quality:.2f}\n- Recency: {m.recency:.2f}\n- **Final Score:** {m.final:.2f}\n\n"
        
        verification_md += f"\n**Methodology:** {verification.methodology}"
        
        status.append("✅ Complete!")
        yield (md, sources_data, verification_md, "\n".join(status))
        
    except Exception as e:
        emsg = str(e)
        error_type = type(e).__name__
        
        if "Connection error" in emsg or "APIConnectionError" in error_type:
            yield ("", [], "", f"❌ Connection Error: check internet/API key.\n\nDetails: {emsg}")
        elif "Event loop" in emsg or "no current event loop" in emsg:
            yield ("", [], "", f"❌ Event Loop Error: internal async issue.\n\nDetails: {emsg}")
        else:
            yield ("", [], "", f"❌ Error ({error_type}): {emsg}")






def create_interface():
    """Create and return the Gradio interface."""
    
    with gr.Blocks(
        title="Deep Research Pro",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1200px !important;
        }
        .status-box {
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
        }
        """
    ) as demo:
        gr.Markdown(
            f"""
            # 🔬 {PROJECT_NAME}
            ### AI-Powered Research Assistant with Verification
            
            Enter a research topic below and get a comprehensive, verified research report with citations.
            """
        )
        
        with gr.Row():
            with gr.Column(scale=2):
                topic_input = gr.Textbox(
                    label="Research Topic",
                    placeholder="e.g., AI in Healthcare, Climate Change Solutions, Quantum Computing",
                    value="AI in Healthcare",
                    lines=2,
                )
                
                with gr.Accordion("Advanced Options", open=False):
                    num_sources = gr.Slider(
                        minimum=5,
                        maximum=20,
                        value=8,
                        step=1,
                        label="Max Sources",
                        info="Maximum number of sources to return from all queries (not the number of queries)"
                    )
                    
                    provider = gr.Radio(
                        choices=["stub", "hosted"],
                        value="hosted",
                        label="Search Provider",
                        info="'stub' for testing, 'hosted' for real OpenAI search"
                    )
                    
                    strict_verify = gr.Checkbox(
                        value=True,
                        label="Strict Verification",
                        info="Enable advanced verification with coverage, quality, and recency metrics"
                    )
                    
                    use_sdk_planner = gr.Checkbox(
                        value=False,
                        label="Use LLM Planner",
                        info="Use AI-powered planning (slower but smarter) vs. fast heuristic planning"
                    )
                
                research_btn = gr.Button(
                    "🔍 Start Research",
                    variant="primary",
                    size="lg"
                )
            
            with gr.Column(scale=1):
                status_display = gr.Textbox(
                    label="Status",
                    value="Ready to research",
                    lines=5,
                    interactive=False,
                    elem_classes=["status-box"]
                )
        
        with gr.Tabs():
            with gr.Tab("📄 Report"):
                report_display = gr.Markdown(
                    label="Research Report",
                    value="# Your research report will appear here...\n\nClick 'Start Research' to begin."
                )
                
                with gr.Row():
                    export_md_btn = gr.Button("💾 Export Markdown")
                    export_md_file = gr.File(label="Download", visible=False)
                    
                    def export_markdown(md: str):
                        if not md or md.startswith("# Your research report"):
                            return gr.File(visible=False)
                        try:
                            path = Path("data/exported_report.md")
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_text(md, encoding="utf-8")
                            return gr.File(value=str(path.resolve()), visible=True)
                        except Exception:
                            return gr.File(visible=False)
                    
                    export_md_btn.click(
                        fn=export_markdown,
                        inputs=[report_display],
                        outputs=[export_md_file]
                    )
            
            with gr.Tab("📚 Sources"):
                sources_table = gr.Dataframe(
                    headers=["Title", "URL", "Type", "Published"],
                    label="Sources",
                    interactive=False,
                    wrap=True,
                )
            
            with gr.Tab("✅ Verification"):
                verification_display = gr.Markdown(
                    label="Verification Results",
                    value="# Verification results will appear here..."
                )
            
            with gr.Tab("ℹ️ About"):
                gr.Markdown(
                    """
                    ## About Deep Research Pro
                    
                    Deep Research Pro is an AI-powered research assistant that:
                    
                    - **Plans** research strategies with multiple search queries
                    - **Searches** the web for relevant sources
                    - **Writes** comprehensive research reports with citations
                    - **Verifies** claims with advanced metrics (coverage, quality, recency)
                    
                    ### Features
                    
                    - ✅ Multi-agent architecture (Planner, Search, Writer, Verifier)
                    - ✅ Parallel search execution
                    - ✅ Source credibility scoring
                    - ✅ Advanced verification metrics
                    - ✅ Structured outputs with citations
                    
                    ### How It Works
                    
                    1. **Planning**: Creates a research plan with subtopics and search queries
                    2. **Search**: Searches the web in parallel for relevant sources
                    3. **Writing**: Generates a structured research report with citations
                    4. **Verification**: Verifies claims and scores source quality
                    
                    ### Tips
                    
                    - Use specific topics for better results
                    - Enable "Strict Verification" for detailed metrics
                    - Use "LLM Planner" for complex topics (slower but smarter)
                    - Check the "Verification" tab for confidence scores
                    
                    ### API Key
                    
                    Make sure your `OPENAI_API_KEY` is set in your environment or `.env` file.
                    """
                )
        
        # Connect the research button
        # Use async generator with hardened client and retry logic
        research_btn.click(
            fn=run_research_stream,
            inputs=[topic_input, num_sources, provider, strict_verify, use_sdk_planner],
            outputs=[report_display, sources_table, verification_display, status_display]
        )
        
        # Example topics
        gr.Markdown("### 💡 Example Topics")
        example_topics = [
            "AI in Healthcare",
            "Climate Change Solutions",
            "Quantum Computing Applications",
            "Sustainable Energy Technologies",
            "Cybersecurity Best Practices",
        ]
        
        with gr.Row():
            for topic in example_topics:
                btn = gr.Button(topic, size="sm")
                btn.click(
                    fn=lambda t=topic: t,
                    outputs=[topic_input]
                )
    
    return demo


if __name__ == "__main__":
    demo = create_interface()
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )

