"""
Gradio interface for Deep Research Pro.
Provides an interactive web UI for the research assistant with file upload support.
"""

from __future__ import annotations

from pathlib import Path
import gradio as gr
import os
import asyncio

from app.core.settings import (
    PROJECT_NAME,
    OPENAI_API_KEY,
    UPLOAD_DIR,
    MAX_UPLOAD_FILES,
    SUPPORTED_FILE_TYPES,
)


from app.core.openai_client import make_async_client
from app.core.research_manager import ResearchManager
from app.agents.report_qa_agent import ReportQAAgent
from app.schemas.analytics import AnalyticsPayload
from app.ui.analytics_dashboard import create_analytics_tab
from app.ui.test_data import generate_fake_research_stream, generate_fake_sources, generate_fake_report
from app.ui.styles import get_css

# Ensure OPENAI_API_KEY is in environment for Agents SDK
# The SDK reads from os.environ, not just from dotenv
if OPENAI_API_KEY and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# -------------------------------------------------------------
# Utilities
# -------------------------------------------------------------

def save_uploads(files):
    """
    Save uploaded files to UPLOAD_DIR and return their paths.
    """
    if not files:
        return []
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    saved_paths = []
    for f in files:
        # Gradio file objects have a .name attribute with the temp file path
        if hasattr(f, 'name'):
            source_path = f.name
        elif isinstance(f, str):
            source_path = f
        else:
            continue
            
        fname = os.path.basename(source_path)
        dest = os.path.join(UPLOAD_DIR, fname)
        
        # Copy file to destination
        with open(source_path, "rb") as src:
            with open(dest, "wb") as out:
                out.write(src.read())
        
        saved_paths.append(dest)
    return saved_paths

def _trim_log(text: str, max_lines: int = 250) -> str:
    """Trim log to last N lines."""
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])

def _truncate_message(text: str, max_chars: int = 2000) -> str:
    """Truncate single status message if too long."""
    if len(text) > max_chars:
        return text[:max_chars] + "... (truncated)"
    return text

# -------------------------------------------------------------
# Research Execution Wrapper
# -------------------------------------------------------------

async def run_research_stream(
    topic: str,
    queries: list,
    num_sources: int,
    num_waves: int,
    uploaded_files: list,
    test_mode: bool = False,
):
    """
    Async generator → streamed output to Gradio.
    Yields: (report_md, status_text, analytics)
    """
    if not topic or topic.strip() == "":
        yield ("", "❌ Please provide a research topic.", None)
        return

    # Filter out empty queries
    # Handle both list of strings and list of lists (from Dataframe)
    if queries and isinstance(queries[0], list):
        # Extract strings from list of lists: [[q1], [q2]] -> [q1, q2]
        queries = [q[0].strip() if isinstance(q, list) and len(q) > 0 and q[0] else str(q).strip() for q in queries if q]
    else:
        # Handle list of strings: [q1, q2] -> [q1, q2]
        queries = [str(q).strip() for q in queries if q and str(q).strip()]
    
    if not queries:
        yield ("", "❌ Please provide at least one search query.", None)
        return
    
    # TEST MODE: Use fake data generator
    if test_mode:
        async for result in generate_fake_research_stream(
            topic=topic,
            queries=queries,
        num_sources=num_sources,
            num_waves=num_waves,
            uploaded_files=uploaded_files,
        ):
            report_md, status_text, analytics = result
            
            # Trim log to prevent excessive growth
            status_text = _truncate_message(status_text, max_chars=8000)
            status_text = _trim_log(status_text, max_lines=400)
            
            # Add auto-scroll anchor
            status_text += '\n\n<a href="#end"> </a><div id="end"></div>'
            
            yield (report_md, status_text, analytics)
        return

    # Save uploaded files to disk
    uploaded_paths = []
    if uploaded_files:
        try:
            uploaded_paths = save_uploads(uploaded_files)
        except Exception as e:
            yield ("", f"❌ Error saving uploaded files: {e}", None)
            return

    # Initialize ResearchManager
    try:
        manager = ResearchManager(
            client=make_async_client(),
            max_sources=num_sources,
            max_waves=num_waves,
            topk_per_query=5,
            num_sources=num_sources,  # For backward compatibility
        )
    except Exception as ex:
        yield ("", f"❌ Failed to initialize ResearchManager: {ex}", None)
        return

    # Run research pipeline
    try:
        async for result in manager.run(
            topic=topic,
            queries=queries,
            uploaded_files=uploaded_paths if uploaded_paths else None,
        ):
            report_md, status_text, analytics = result
            
            # Trim log to prevent excessive growth
            status_text = _truncate_message(status_text, max_chars=8000)
            status_text = _trim_log(status_text, max_lines=400)
            
            # Add auto-scroll anchor
            status_text += '\n\n<a href="#end"> </a><div id="end"></div>'
            
            yield (report_md, status_text, analytics)
    except Exception as e:
        yield ("", f"❌ Error during research: {str(e)}", None)

# -------------------------------------------------------------
# Callback: Generate Search Plan
# -------------------------------------------------------------

async def generate_plan_callback(topic: str, num_sources: int, test_mode: bool = False):
    """
    Generate search plan (queries) for user review.
    """
    if not topic or topic.strip() == "":
        return None, None, "❌ Please enter a topic.", gr.update(visible=False)
    
    # TEST MODE: Generate fake plan
    if test_mode:
        fake_queries = [
            f"{topic}: Overview and Introduction",
            f"{topic}: Current Trends and Developments",
            f"{topic}: Key Challenges and Solutions",
            f"{topic}: Future Outlook and Predictions",
            f"{topic}: Case Studies and Examples",
        ]
        
        fake_thoughts = f"""
## Planning Thoughts (Test Mode)

I've generated {len(fake_queries)} search queries to comprehensively cover the topic of **{topic}**.

### Query Strategy:
1. **Overview Query**: Provides foundational understanding
2. **Current Trends**: Captures recent developments
3. **Challenges**: Identifies key problems and solutions
4. **Future Outlook**: Explores predictions and trends
5. **Case Studies**: Includes practical examples

### Expected Sources:
- Academic papers and research articles
- Industry reports and whitepapers
- News articles and blog posts
- Government and institutional publications

**Note**: This is test mode - no API calls are being made.
"""
        
        df = [[q] for q in fake_queries]
        status = f"✅ Generated {len(df)} search queries (TEST MODE). Review and edit them below, then click 'Approve & Start Research'."
        
        return (
            df,                         # Query table
            fake_thoughts,              # Planner Thoughts
            status,                     # Status
            gr.update(visible=True)     # Show query editor
        )
    
    try:
        manager = ResearchManager(
            client=make_async_client(),
            max_sources=num_sources,
            max_waves=2,
            topk_per_query=5,
            num_sources=num_sources,  # For backward compatibility
        )
        
        plan = await manager.generate_plan(topic)
        
        # plan.queries → list of strings
        # plan.thoughts → planner reasoning text
        df = [[q] for q in (plan.queries or [])]
        thoughts = plan.thoughts or "No thoughts provided."
        status = f"✅ Generated {len(df)} search queries. Review and edit them below, then click 'Approve & Start Research'."
        
        return (
            df,                         # Query table
            thoughts,                   # Planner Thoughts
            status,                     # Status
            gr.update(visible=True)     # Show query editor
        )
    except Exception as ex:
        return None, None, f"❌ Error: {ex}", gr.update(visible=False)

# -------------------------------------------------------------
# Callback: Q&A on top of the final report
# -------------------------------------------------------------

def _extract_sources_from_report(report_md: str) -> str:
    """
    Extract sources from the References section of the report markdown.
    Returns a plain-text list with numeric IDs that the Q&A agent can cite as [1], [2], ...
    """
    if not report_md:
        return "No sources were provided."
    
    import re
    
    # Look for the References section (collapsible details)
    # Pattern: <details>...<summary>References</summary>...references...</details>
    refs_pattern = r'<details>.*?<summary>.*?References.*?</summary>(.*?)</details>'
    match = re.search(refs_pattern, report_md, re.DOTALL | re.IGNORECASE)
    
    if not match:
        # Try markdown format: ## References
        refs_pattern = r'##\s+References\s*\n(.*?)(?=\n##|\Z)'
        match = re.search(refs_pattern, report_md, re.DOTALL | re.IGNORECASE)
    
    if not match:
        return "No sources were provided."
    
    refs_content = match.group(1)
    
    # Extract individual references
    # Pattern: [id] Title or [id] <a href="url">Title</a>
    ref_pattern = r'\[(\d+)\]\s*(?:<a[^>]*>)?([^<]+)(?:</a>)?'
    matches = re.findall(ref_pattern, refs_content)
    
    if not matches:
        return "No sources were provided."
    
    lines = []
    for ref_id, title in matches:
        title = title.strip()
        if title:
            lines.append(f"[{ref_id}] {title}")
    
    return "\n".join(lines) if lines else "No sources were provided."


async def qa_answer_callback(
    question: str,
    report_md: str,
    chat_history: list,
):
    """
    Answer a user question based on the current report.
    Sources are extracted from the References section of the report.
    Returns updated chat history and clears the question box.
    """
    # Normalize history
    chat_history = chat_history or []

    # Validate input
    if not question or not question.strip():
        # Just echo a gentle message
        chat_history.append(
            ("", "❌ Please enter a non-empty question.")
        )
        return chat_history, ""

    if not report_md or report_md.startswith("# Your research report will appear here"):
        chat_history.append(
            ("", "❌ Please run a research and generate a report before asking questions.")
        )
        return chat_history, ""

    # Extract sources from the References section of the report
    sources_text = _extract_sources_from_report(report_md)

    # Instantiate Q&A agent
    qa_agent = ReportQAAgent(openai_client=make_async_client())

    try:
        answer = await qa_agent.answer_async(
            question=question.strip(),
            report_markdown=report_md,
            sources_text=sources_text,
        )
    except Exception as ex:
        chat_history.append(
            (question, f"❌ Error while answering: {ex}")
        )
        return chat_history, ""

    chat_history.append((question, answer))
    return chat_history, ""  # clear input

# -------------------------------------------------------------
# Callback: Start Research
# -------------------------------------------------------------

async def start_research_callback(
    topic: str,
    df_queries: list,
    num_sources: int,
    num_waves: int,
    files: list,
    test_mode: bool = False,
):
    """
    Start the main research pipeline.
    """
    queries = [row[0] for row in (df_queries or []) if row and row[0].strip()]
    
    if not queries:
        yield ("", [], "❌ No queries found. Please generate or enter queries.", None)
        return

    # Run generator
    async for result in run_research_stream(
        topic,
        queries,
        num_sources,
        num_waves,
        files or [],
        test_mode=test_mode,
    ):
        yield result

# -------------------------------------------------------------
# BUILD GRADIO INTERFACE
# -------------------------------------------------------------

def create_interface():
    # Get absolute paths to images and convert to base64
    project_root = Path(__file__).parent.parent.parent
    bg_image_path = project_root / "_.jpeg"  # Background image
    header_image_path = project_root / "Background_photo.png"  # Header image
    
    # Convert background image to base64
    import base64
    bg_image_url = ""
    if bg_image_path.exists():
        with open(bg_image_path, "rb") as img_file:
            img_data = img_file.read()
            bg_image_base64 = base64.b64encode(img_data).decode('utf-8')
            bg_image_url = f"data:image/jpeg;base64,{bg_image_base64}"
    
    # Convert header image to base64
    header_image_url = ""
    if header_image_path.exists():
        with open(header_image_path, "rb") as img_file:
            img_data = img_file.read()
            header_image_base64 = base64.b64encode(img_data).decode('utf-8')
            header_image_url = f"data:image/png;base64,{header_image_base64}"
    
    # Get CSS from styles module
    css_content = get_css(bg_image_url)
    
    with gr.Blocks(
        title="Deep Research Pro",
        theme=gr.themes.Soft(),
        css=css_content
    ) as demo:
        # Hero Header Section with image
        with gr.Group(elem_classes=["hero-header"]):
            # Create a row for header image and text
            with gr.Row():
                # Header image - much bigger
                if header_image_url:
                    with gr.Column(scale=0, min_width=420):
                        gr.HTML(
                            f"""
                            <div class="header-image-container">
                                <img src="{header_image_url}" alt="Deep Research Pro Logo" />
                            </div>
                            """
                        )
                
                # Header text
                with gr.Column(scale=1):
                    gr.Markdown(
                        f"""
                        # 🔬 {PROJECT_NAME}
                        ### AI-Powered Research Assistant
                        
                        Enter a research topic below and get a comprehensive research report with citations.
                        Upload PDFs, DOCX, or TXT files to include them in your research.
                        """
                    )
        
        topic_input = gr.Textbox(
            label="Research Topic",
            placeholder="e.g., AI in Healthcare, Climate Change Solutions, Quantum Computing",
            value="AI in Healthcare",
            lines=2,
        )
        
        with gr.Accordion("Advanced Options", open=False):
            test_mode = gr.Checkbox(
                label="🧪 Test Mode (No API Calls)",
                value=False,
                info="Enable to test the UI with fake data without making API calls that cost money"
            )
            
            num_sources = gr.Slider(
                minimum=5,
                maximum=100,
                value=25,
                step=1,
                label="Max Source Limit (Optional)",
                info="Maximum number of sources to include. Leave at default (25) to let AI decide based on query complexity, or set explicitly for cost/time control."
            )
            
            max_waves = gr.Slider(
                minimum=1,
                maximum=3,
                value=2,
                step=1,
                label="Max Research Waves",
                info="Maximum number of research iterations"
            )
            
            file_upload = gr.Files(
                label=f"📁 Upload Documents (PDF, DOCX, TXT) - Up to {MAX_UPLOAD_FILES} files",
                file_count="multiple",
                file_types=[".pdf", ".docx", ".txt"],
            )
            
            gr.Markdown(
                """
                ### 💾 Cache Information
                - **Results are cached for 24 hours** to improve performance
                - Time-sensitive queries (e.g., "news today", "latest updates") automatically bypass cache
                - Cache persists across app restarts
                - To force fresh results, slightly modify your query or wait 24 hours
                """
            )
        
        # --- Planner Section ---
        with gr.Group(visible=True, elem_classes=["plan-section"]) as plan_section:
            plan_thoughts = gr.Markdown(
                label="Planning Thoughts",
                value="Enter a research topic above to generate search queries."
            )
            
            query_inputs = gr.Dataframe(
                headers=["Search Query"],
                datatype=["str"],
                row_count="dynamic",
                col_count=1,
                wrap=True,
                label="✏️ Edit Search Queries",
                interactive=True,
                value=[[""] for _ in range(5)],
            )
            
            with gr.Row():
                approve_btn = gr.Button("✅ Approve & Start Research", variant="primary")
        
        # Hidden state for plan
        plan_state = gr.State(value={})
        analytics_state = gr.State(value=None)  # Will hold AnalyticsPayload
        
        # --- Live Log ---
        with gr.Accordion("📊 Live Log (streaming)", open=True):
            live_log = gr.Markdown(value="Ready.", elem_id="live-log")
        
        with gr.Tabs():
            with gr.Tab("📄 Report"):
                report_display = gr.Markdown(
                    label="Research Report",
                    value="# Your research report will appear here...\n\nEnter a topic above and click 'Approve & Start Research' to begin.",
                    elem_classes=["report-markdown"]
                )
                
                with gr.Row():
                    export_md_btn = gr.Button("💾 Export Markdown")
                    export_html_btn = gr.Button("🌐 Export HTML")
                    export_pdf_btn = gr.Button("📄 Export PDF")
                
                export_md_file = gr.File(label="Download Markdown", visible=False)
                export_html_file = gr.File(label="Download HTML", visible=False)
                export_pdf_file = gr.File(label="Download PDF", visible=False)
                
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
                
                def export_pdf(md_text: str):
                    if not md_text or md_text.startswith("# Your research report"):
                        return gr.File(visible=False)
                    try:
                        from app.core.render import render_pdf_from_markdown
                        path = Path("data/exported_report.pdf")
                        path.parent.mkdir(parents=True, exist_ok=True)
                        render_pdf_from_markdown(md_text, str(path.resolve()))
                        return gr.File(value=str(path.resolve()), visible=True)
                    except ImportError as e:
                        # Return error message if weasyprint is not installed
                        error_msg = "❌ PDF export requires weasyprint. Install with: pip install weasyprint"
                        print(error_msg)
                        print(f"Details: {e}")
                        return gr.File(visible=False)
                    except OSError as e:
                        # Handle missing system libraries (libpango, libcairo, etc.)
                        error_msg = str(e)
                        print("❌ PDF Export Error - Missing System Libraries")
                        print(error_msg)
                        # Show user-friendly message
                        if "libpango" in error_msg or "libcairo" in error_msg:
                            print("\n💡 To fix on macOS:")
                            print("   brew install pango cairo gdk-pixbuf libffi")
                            print("   pip install --upgrade --force-reinstall weasyprint")
                        return gr.File(visible=False)
                    except Exception as e:
                        # Log error but don't crash
                        import traceback
                        print(f"❌ PDF export error: {e}")
                        traceback.print_exc()
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
            
                export_pdf_btn.click(
                    fn=export_pdf,
                    inputs=[report_display],
                    outputs=[export_pdf_file]
                )
            
            # 📊 Analytics tab
            create_analytics_tab(analytics_state)
            
            # 💬 New Q&A tab
            with gr.Tab("💬 Q&A on this Report"):
                qa_chat = gr.Chatbot(
                    label="Ask questions about this report",
                    value=[],
                )
                qa_question = gr.Textbox(
                    label="Your question",
                    placeholder="e.g., Summarize the report in 4 lines",
                    lines=2,
                )
                with gr.Row():
                    qa_ask_btn = gr.Button("Ask", variant="primary")
                    qa_clear_btn = gr.Button("Clear", variant="secondary")
        
        # --- Event Handlers ---
        
        # Auto-generate plan when topic changes
        async def handle_topic_change(topic, num_sources, test_mode):
            """Auto-generate plan when topic is entered."""
            if not topic or not topic.strip():
                return (
                    gr.update(visible=True),
                    [],
                    "Enter a research topic above to generate search queries.",
                    "Ready.",
                    {}
                )
            
            try:
                queries, thoughts, status, visibility = await generate_plan_callback(topic, num_sources, test_mode)
                queries_df = [[q] for q in queries] if queries else []
                return (
                    gr.update(visible=True),
                    queries_df,
                    thoughts or "Planning in progress...",
                    status or "✅ Plan generated. Review and edit queries below.",
                    {"queries": queries, "topic": topic, "thoughts": thoughts}
                )
            except Exception as e:
                return (
                    gr.update(visible=True),
                    [],
                    f"❌ Error generating plan: {e}",
                    f"❌ Error: {e}",
                    {}
                )
        
        # Auto-generate plan when topic or settings change
        topic_input.change(
            fn=handle_topic_change,
            inputs=[topic_input, num_sources, test_mode],
            outputs=[plan_section, query_inputs, plan_thoughts, live_log, plan_state],
        )
        
        num_sources.change(
            fn=handle_topic_change,
            inputs=[topic_input, num_sources, test_mode],
            outputs=[plan_section, query_inputs, plan_thoughts, live_log, plan_state],
        )
        
        test_mode.change(
            fn=handle_topic_change,
            inputs=[topic_input, num_sources, test_mode],
            outputs=[plan_section, query_inputs, plan_thoughts, live_log, plan_state],
        )
        
        # Approve button - start research with edited queries
        def extract_queries_from_df(queries_df):
            """Extract queries from dataframe format."""
            # Handle None, empty list, or empty DataFrame
            if queries_df is None:
                return []
            
            # Check if it's a pandas DataFrame
            try:
                import pandas as pd
                if isinstance(queries_df, pd.DataFrame):
                    if queries_df.empty:
                        return []
                    # Convert DataFrame to list of lists
                    queries_df = queries_df.values.tolist()
            except (ImportError, AttributeError):
                pass
            
            # Handle empty list
            if not queries_df or len(queries_df) == 0:
                return []
            
            # queries_df is list of lists: [[query1], [query2], ...]
            queries = []
            for row in queries_df:
                if row and len(row) > 0:
                    query = row[0] if isinstance(row, (list, tuple)) else str(row)
                    if query:
                        queries.append(str(query).strip())
            
            # Filter out empty queries
            return [q for q in queries if q]
        
        async def start_research_with_queries(topic, queries_df, num_sources, max_waves, files, test_mode):
            """Extract queries and start research."""
            queries = extract_queries_from_df(queries_df)
            
            # Empty queries guard - show friendly error
            if not queries:
                yield ("", "❌ Please provide at least one search query. All queries are empty.", None)
                return
            
            # Use all provided queries from the table
            status_msg = ""
            placeholder_report = (
                "### 🔄 Research in progress...\n\n"
                "Live updates are streaming in the Log panel. Your final report will appear here once the research completes."
            )
            
            # Add test mode indicator
            if test_mode:
                status_msg += "🧪 TEST MODE: Using fake data (no API calls)\n\n"
            
            status_msg += "🚀 Starting research with your approved queries..."
            yield (placeholder_report, status_msg, None)
            status_msg = ""
            
            # Start research with queries from the table
            first_yield = False
            async for result in run_research_stream(topic, queries, num_sources, max_waves, files or [], test_mode=test_mode):
                # Prepend status message to first status update if queries were capped
                if first_yield and status_msg:
                    report_md, status, analytics = result
                    if status:
                        status = status_msg + status
                    yield (report_md, status, analytics)
                    first_yield = False
                else:
                    yield result
                    first_yield = False
        
        approve_btn.click(
            fn=start_research_with_queries,
            inputs=[topic_input, query_inputs, num_sources, max_waves, file_upload, test_mode],
            outputs=[report_display, live_log, analytics_state]
        )
        
        # --- Q&A Handlers ---
        
        # Ask button → use current report + chat history (sources extracted from report)
        qa_ask_btn.click(
            fn=qa_answer_callback,
            inputs=[qa_question, report_display, qa_chat],
            outputs=[qa_chat, qa_question],
        )
        
        # Allow Enter key to submit Q&A question
        qa_question.submit(
            fn=qa_answer_callback,
            inputs=[qa_question, report_display, qa_chat],
            outputs=[qa_chat, qa_question],
        )
        
        # Clear button → reset chat + input
        def clear_qa():
            return [], ""
        
        qa_clear_btn.click(
            fn=clear_qa,
            inputs=[],
            outputs=[qa_chat, qa_question],
        )
        
        # --- About Section ---
        with gr.Accordion("ℹ️ About This App", open=False):
            gr.Markdown(
                """
                ### Features
                
                **Core Capabilities:**
                - ✅ Multi-agent architecture (QueryGenerator, SearchAgent, WriterAgent, FollowUpDecisionAgent, FileSummarizerAgent, ReportQAAgent)
                - ✅ Multi-wave research with intelligent follow-up queries (up to 3 waves)
                - ✅ Dynamic query generation: Planner automatically determines optimal query count based on topic complexity
                - ✅ User-guided query planning with review and editing (fully editable query table)
                - ✅ File upload support (PDF, DOCX, TXT) with semantic chunking and parallel processing
                - ✅ Parallel search execution with concurrent API calls (50x speedup)
                - ✅ Two-level caching system (L1: in-memory, L2: SQLite persistent) with 24h TTL and LRU management
                - ✅ Time-sensitive query detection (auto-bypasses cache for "latest", "today", "breaking")
                - ✅ Intelligent source limits: AI recommends optimal source count based on query complexity
                
                **Report Generation:**
                - ✅ Structured outputs with Pydantic schemas and validation
                - ✅ Cross-source synthesis with multi-citation support ([1][2][3])
                - ✅ Comprehensive long-form reports with adaptive section structures and nested subsections
                - ✅ Plain clickable citations (no background highlighting) for clean readability
                - ✅ Source deduplication and intelligent filtering (top-K by content richness)
                - ✅ Subtopic extraction and theme analysis for better organization
                - ✅ Output quality validation with automatic retry on failure
                
                **UI & Analytics:**
                - ✅ Real-time streaming updates with Live Log
                - ✅ Analytics dashboard with Plotly visualizations (sources, citations, efficiency metrics)
                - ✅ Workflow graph visualization showing agent architecture and tool interactions
                - ✅ Interactive Q&A about generated reports (ReportQAAgent)
                - ✅ Export to Markdown, HTML, and PDF with full citations
                - ✅ Query-level summaries for better context integration
                - ✅ Collapsible References section for cleaner report display
                
                **Technical Features:**
                - ✅ Uses GPT-4o-mini for all tasks to optimize cost while maintaining quality
                - ✅ Token estimation and prompt optimization (5000 char query-level summary limit)
                - ✅ URL normalization and citation management
                - ✅ Database migration logic for cache schema evolution
                - ✅ Source credibility scoring based on domain analysis
                - ✅ Safe async execution with comprehensive error handling
                - ✅ Follow-up query deduplication to prevent redundant research waves
                
                ### How It Works
                
                1. **Planning**: QueryGeneratorAgent analyzes topic complexity and creates diverse search queries (typically 3-12 queries) covering multiple research angles (background, stats, trends, case studies, risks, etc.)
                2. **Query Review** (optional): Review and edit AI-generated queries in the interactive table before execution
                3. **File Processing** (optional): Processes uploaded documents using LLM-based semantic chunking and parallel summarization
                4. **Search Waves**: Searches the web in parallel for relevant sources with detailed query-level summaries
                5. **Follow-Up Decision**: FollowUpDecisionAgent analyzes findings, identifies gaps, and decides if additional research waves are needed (with deduplication against previous queries)
                6. **Source Processing**: Deduplicates sources, filters to recommended count (or user-specified limit), and normalizes URLs
                7. **Writing**: WriterAgent synthesizes sources into comprehensive long-form research reports with nested subsections and inline citations
                8. **Validation**: Validates output quality and retries with simplified prompt if needed
                9. **Rendering**: Converts to markdown with plain clickable citations and generates collapsible References section
                
                ### Tips
                
                - Use specific topics for better results (e.g., "AI in Healthcare: diagnostics, treatment, and ethics")
                - The system uses GPT-4o-mini for all tasks to optimize cost while maintaining quality
                - Upload relevant documents to enhance your research (processed in parallel)
                - Review and edit queries in the planning phase for better control (queries are fully editable)
                - The planner automatically determines the optimal number of queries based on topic complexity
                - Check the Analytics tab after research for detailed metrics, visualizations, and workflow graph
                - Use the Q&A tab to explore your generated report interactively
                - Reports support nested subsections for hierarchical organization of complex topics
                
                ### Caching
                
                - Results are cached for 24 hours to improve performance
                - Time-sensitive queries automatically bypass cache
                - Cache persists across app restarts (SQLite disk storage)
                - Cache statistics visible in Analytics dashboard
                
                ### API Key
                
                Make sure your `OPENAI_API_KEY` is set in your environment or `.env` file.
                """
                )
    
    return demo

def main():
    demo = create_interface()
    demo.queue()
    demo.launch()

if __name__ == "__main__":
    main()
