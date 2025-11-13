"""
Gradio interface for Deep Research Pro.
Provides an interactive web UI for the research assistant.
"""

from __future__ import annotations

from pathlib import Path

import gradio as gr
import os

from app.core.settings import PROJECT_NAME, OPENAI_API_KEY
from app.core.openai_client import make_async_client
from app.core.research_manager import ResearchManager

# Ensure OPENAI_API_KEY is in environment for Agents SDK
# The SDK reads from os.environ, not just from dotenv
if OPENAI_API_KEY and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


async def generate_plan_async(topic: str, num_searches: int, num_sources: int):
    """
    Generate search plan (queries) for user review.
    
    Returns:
        Tuple of (queries_list, thoughts_text, status_text)
    """
    if not topic or not topic.strip():
        return ([], "", "❌ Please enter a research topic")
    
    try:
        manager = ResearchManager(
            openai_client=make_async_client(),
            num_searches=num_searches,
            num_sources=num_sources
        )
        
        query_response = await manager.generate_plan(topic)
        
        # Format queries as list for editable textboxes
        queries_list = query_response.queries if query_response.queries else []
        thoughts = query_response.thoughts or "No thoughts provided."
        status = f"✅ Generated {len(queries_list)} search queries. Review and edit them below, then click 'Approve & Start Research'."
        
        # Truncate status message
        status = _truncate_message(status, max_chars=4000)
        
        return (queries_list, thoughts, status)
    except Exception as e:
        return ([], "", f"❌ Error generating plan: {str(e)}")


def _trim_log(text: str, max_lines: int = 250) -> str:
    """Trim log to last N lines."""
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])

def _truncate_message(text: str, max_chars: int = 2000) -> str:
    """Truncate single status message if too long."""
    if len(text) > max_chars:
        return text[:max_chars] + "... (truncated)"
    return text

async def run_research_stream(
    topic: str,
    approved_queries: list,
    num_searches: int,
    num_sources: int,
    max_waves: int,
    show_outline: bool,
):
    """
    Async generator for research pipeline using ResearchManager.
    Uses pre-approved queries from user.
    
    Args:
        topic: Research topic/query
        approved_queries: List of approved/edited queries
        num_searches: Number of search queries to perform
        num_sources: Maximum number of sources to return
        max_waves: Maximum number of research waves
        show_outline: Whether to show outline preview
    """
    # Filter out empty queries
    queries = [q.strip() for q in approved_queries if q and q.strip()]
    
    if not queries:
        yield ("", [], "❌ Please provide at least one search query", gr.update(visible=False))
        return
    
    # Create ResearchManager with settings
    manager = ResearchManager(
        openai_client=make_async_client(),
        num_searches=num_searches,
        num_sources=num_sources,
        max_waves=max_waves
    )
    
    # Show waves/sources in first log line
    first_status = f"Max Waves: {max_waves} | Max Sources: {num_sources}\n\n"
    
    # Delegate to ResearchManager with approved queries
    async for result in manager.run(topic, approved_queries=queries):
        report_md, sources_data, status_text = result
        
        # Prepend first status line if this is the first yield
        if first_status:
            status_text = first_status + status_text
            first_status = None
        
        # Trim log to prevent excessive growth
        status_text = _truncate_message(status_text, max_chars=8000)
        status_text = _trim_log(status_text, max_lines=400)
        
        # Add auto-scroll anchor (best effort)
        status_text += '\n\n<a href="#end"> </a><div id="end"></div>'
        
        # Extract outline from report if available and show_outline is True
        outline_update = gr.update(visible=False)
        if show_outline and report_md:
            # Robust outline extraction - handles variations in heading format
            lines = report_md.split("\n")
            outline_lines, in_outline = [], False
            for line in lines:
                h2 = line.strip().lower().startswith("## ")
                if h2 and "outline" in line.strip().lower():
                    in_outline = True
                    outline_lines.append(line)
                    continue
                if in_outline:
                    if h2 and "outline" not in line.strip().lower():
                        break
                    if line.strip().startswith(("-", "*")) or line.strip() == "":
                        outline_lines.append(line)
            if outline_lines:
                outline_text = "\n".join(outline_lines).strip()
                outline_update = gr.update(value=outline_text, visible=True)
        
        yield (report_md, sources_data, status_text, outline_update)






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
        #live-log {
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 12px;
            background: #f9fafb !important;
            color: #111827 !important;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
            font-size: 0.9rem;
            line-height: 1.5;
        }
        #live-log * {
            color: #111827 !important;
        }
        .report-markdown a[href] {
            display: inline-block;
            padding: 2px 6px;
            margin: 0 2px;
            background-color: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 3px;
            color: #1976d2;
            text-decoration: none;
            font-size: 0.9em;
            font-weight: 500;
        }
        .report-markdown a[href]:hover {
            background-color: #bbdefb;
            border-color: #1976d2;
        }
        """
    ) as demo:
        gr.Markdown(
            f"""
            # 🔬 {PROJECT_NAME}
                ### AI-Powered Research Assistant
            
                Enter a research topic below and get a comprehensive research report with citations.
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
                    
                    num_searches = gr.Slider(
                        minimum=3,
                        maximum=10,
                        value=5,
                        step=1,
                        label="Number of Searches",
                        info="Number of search queries to perform"
                    )
                    
                    num_sources = gr.Slider(
                        minimum=5,
                        maximum=20,
                        value=8,
                        step=1,
                        label="Max Sources",
                        info="Maximum number of sources to return from all queries (not the number of queries)"
                    )
                    
                    max_waves = gr.Slider(
                        minimum=1,
                        maximum=3,
                        value=3,
                        step=1,
                        label="Max Waves",
                        info="Maximum number of research waves (Wave 1 + follow-ups)"
                    )
                    
                    show_outline = gr.Checkbox(
                        label="Show Outline (preview)",
                        value=True,
                        info="Preview the report outline before final synthesis"
                    )
                
                # State to store generated queries
                plan_state = gr.State(value={"queries": [], "topic": "", "thoughts": ""})
                
                generate_plan_btn = gr.Button(
                    "📋 Generate Search Plan",
                    variant="primary"
                )
                
                # Query editing section (initially hidden)
                with gr.Group(visible=False) as plan_section:
                    gr.Markdown("### 📝 Review & Edit Search Queries")
                    
                    plan_thoughts = gr.Textbox(
                        label="Planning Thoughts",
                        lines=3,
                        interactive=False,
                        info="The AI's reasoning for these queries"
                    )
                    
                    query_inputs = gr.Dataframe(
                        headers=["Search Query"],
                        label="Search Queries (editable)",
                        interactive=True,
                        wrap=True,
                        type="array",
                        col_count=(1, "fixed"),
                    )
                    
                    with gr.Row():
                        approve_btn = gr.Button(
                            "✅ Approve & Start Research",
                            variant="primary"
                        )
                        skip_btn = gr.Button(
                            "⏭️ Skip & Use Original",
                            variant="secondary"
                        )
        
        # Live Log in its own row below controls
        with gr.Row():
            with gr.Column():
                with gr.Accordion("📊 Live Log (streaming)", open=True):
                    live_log = gr.Markdown(value="Ready.", elem_id="live-log")
                
                outline_md = gr.Markdown(visible=False, label="Outline Preview")
        
        with gr.Tabs():
            with gr.Tab("📄 Report"):
                report_display = gr.Markdown(
                    label="Research Report",
                    value="# Your research report will appear here...\n\nClick 'Start Research' to begin.",
                    elem_classes=["report-markdown"]
                )
                
                with gr.Row():
                    export_md_btn = gr.Button("💾 Export Markdown")
                    export_html_btn = gr.Button("🌐 Export HTML")
                
                export_md_file = gr.File(label="Download Markdown", visible=False)
                export_html_file = gr.File(label="Download HTML", visible=False)
                
                def export_markdown(md_text: str):
                    if not md_text or md_text.startswith("# Your research report"):
                        return gr.File(visible=False)
                    try:
                        path = Path("data/exported_report.md")
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(md_text, encoding="utf-8")
                        return gr.File(value=str(path.resolve()), visible=True)
                    except Exception:
                        return gr.File(visible=False)
                
                def export_html(md_text: str):
                    if not md_text or md_text.startswith("# Your research report"):
                        return gr.File(visible=False)
                    try:
                        from app.core.render import render_html_from_markdown
                        html = render_html_from_markdown(md_text)
                        path = Path("data/exported_report.html")
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(html, encoding="utf-8")
                        return gr.File(value=str(path.resolve()), visible=True)
                    except Exception:
                        return gr.File(visible=False)
                
                export_md_btn.click(
                    fn=export_markdown,
                    inputs=[report_display],
                    outputs=[export_md_file]
                )
                
                export_html_btn.click(
                    fn=export_html,
                    inputs=[report_display],
                    outputs=[export_html_file]
                )
            
            with gr.Tab("📚 Sources"):
                sources_table = gr.Dataframe(
                    headers=["Title", "URL", "Type", "Published"],
                    label="Sources",
                    interactive=False,
                    wrap=True,
                )
            
            with gr.Tab("ℹ️ About"):
                gr.Markdown(
                    """
                    ## About Deep Research Pro
                    
                    Deep Research Pro is an AI-powered research assistant that:
                    
                    - **Plans** research strategies with multiple search queries
                    - **Searches** the web for relevant sources
                    - **Writes** comprehensive research reports with citations
                    
                    ### Features
                    
                    - ✅ Multi-agent architecture (Planner, Search, Writer)
                    - ✅ Parallel search execution
                    - ✅ Structured outputs with citations
                    
                    ### How It Works
                    
                    1. **Planning**: Creates a research plan with subtopics and search queries
                    2. **Search**: Searches the web in parallel for relevant sources
                    3. **Writing**: Generates a structured research report with citations
                    
                    ### Tips
                    
                    - Use specific topics for better results
                    - The system uses LLM planning and deep search for high-quality research
                    
                    ### API Key
                    
                    Make sure your `OPENAI_API_KEY` is set in your environment or `.env` file.
                    """
                )
        
        # Generate plan button
        async def handle_generate_plan(topic, num_searches, num_sources):
            """Handle plan generation and show editing UI."""
            queries, thoughts, status = await generate_plan_async(topic, num_searches, num_sources)
            
            # Convert queries list to dataframe format (list of lists)
            queries_df = [[q] for q in queries] if queries else []
            
            return (
                gr.update(visible=True),  # Show plan section
                queries_df,  # Query inputs
                thoughts,  # Planning thoughts
                status,  # Status
                {"queries": queries, "topic": topic, "thoughts": thoughts}  # State
            )
        
        generate_plan_btn.click(
            fn=handle_generate_plan,   
            inputs=[topic_input, num_searches, num_sources],
            outputs=[plan_section, query_inputs, plan_thoughts, live_log, plan_state],
        )
        
        # Approve button - start research with edited queries
        def extract_queries_from_df(queries_df):
            """Extract queries from dataframe format."""
            if not queries_df:
                return []
            # queries_df is list of lists: [[query1], [query2], ...]
            queries = [row[0] if row and len(row) > 0 and row[0] else "" for row in queries_df]
            # Filter out empty queries
            return [q.strip() for q in queries if q and q.strip()]
        
        async def start_research_with_queries(topic, queries_df, num_searches, num_sources, max_waves, show_outline):
            """Extract queries and start research."""
            queries = extract_queries_from_df(queries_df)
            
            # Empty queries guard - show friendly error
            if not queries:
                yield ("", [], "❌ Please provide at least one search query. All queries are empty.", gr.update(visible=False))
                return
            
            # Cap queries to num_searches if user provided more
            original_count = len(queries)
            if len(queries) > num_searches:
                queries = queries[:num_searches]
                status_msg = f"ℹ️ Using first {num_searches} of {original_count} edited queries.\n\n"
            else:
                status_msg = ""
            
            # Start research with (possibly capped) queries
            first_yield = True
            async for result in run_research_stream(topic, queries, num_searches, num_sources, max_waves, show_outline):
                # Prepend status message to first status update if queries were capped
                if first_yield and status_msg:
                    report_md, sources_data, status, outline_update = result
                    if status:
                        status = status_msg + status
                    yield (report_md, sources_data, status, outline_update)
                    first_yield = False
                else:
                    yield result
                    first_yield = False
        
        approve_btn.click(
            fn=start_research_with_queries,
            inputs=[topic_input, query_inputs, num_searches, num_sources, max_waves, show_outline],
            outputs=[report_display, sources_table, live_log, outline_md]
        )
        
        # Skip button - start research with original queries from state
        async def use_original_queries_and_start(state, topic, num_searches, num_sources, max_waves, show_outline):
            """Use original queries from state and start research."""
            queries = (state.get("queries") if state and "queries" in state else []) or []
            
            # Cap queries to num_searches (defensive)
            if len(queries) > num_searches:
                queries = queries[:num_searches]
                preface = f"ℹ️ Using first {num_searches} saved queries.\n\n"
            else:
                preface = ""
            
            first_yield = True
            async for result in run_research_stream(topic, queries, num_searches, num_sources, max_waves, show_outline):
                report_md, sources_data, status_text, outline_update = result
                if first_yield and preface:
                    status_text = preface + status_text
                    preface = ""
                yield (report_md, sources_data, status_text, outline_update)
                first_yield = False
        
        skip_btn.click(
            fn=use_original_queries_and_start,
            inputs=[plan_state, topic_input, num_searches, num_sources, max_waves, show_outline],
            outputs=[report_display, sources_table, live_log, outline_md]
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
                btn = gr.Button(topic)
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

