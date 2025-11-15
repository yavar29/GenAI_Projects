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
    show_outline: bool = False,
):
    """
    Async generator → streamed output to Gradio.
    Yields: (report_md, sources_data, status_text, outline_update, analytics)
    """
    if not topic or topic.strip() == "":
        yield ("", [], "❌ Please provide a research topic.", gr.update(visible=False), None)
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
        yield ("", [], "❌ Please provide at least one search query.", gr.update(visible=False), None)
        return

    # Save uploaded files to disk
    uploaded_paths = []
    if uploaded_files:
        try:
            uploaded_paths = save_uploads(uploaded_files)
        except Exception as e:
            yield ("", [], f"❌ Error saving uploaded files: {e}", gr.update(visible=False), None)
            return

    # Initialize ResearchManager
    try:
        manager = ResearchManager(
            client=make_async_client(),
            max_sources=num_sources,
            max_waves=num_waves,
            topk_per_query=5,
            num_searches=len(queries),  # For backward compatibility
            num_sources=num_sources,  # For backward compatibility
        )
    except Exception as ex:
        yield ("", [], f"❌ Failed to initialize ResearchManager: {ex}", gr.update(visible=False), None)
        return

    # Run research pipeline
    try:
        async for result in manager.run(
            topic=topic,
            queries=queries,
            uploaded_files=uploaded_paths if uploaded_paths else None,
        ):
            report_md, sources_data, status_text, analytics = result
            
            # Trim log to prevent excessive growth
            status_text = _truncate_message(status_text, max_chars=8000)
            status_text = _trim_log(status_text, max_lines=400)
            
            # Add auto-scroll anchor
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
            
            yield (report_md, sources_data, status_text, outline_update, analytics)
    except Exception as e:
        yield ("", [], f"❌ Error during research: {str(e)}", gr.update(visible=False), None)

# -------------------------------------------------------------
# Callback: Generate Search Plan
# -------------------------------------------------------------

async def generate_plan_callback(topic: str, num_searches: int, num_sources: int):
    """
    Generate search plan (queries) for user review.
    """
    if not topic or topic.strip() == "":
        return None, None, "❌ Please enter a topic.", gr.update(visible=False)
    
    try:
        manager = ResearchManager(
            client=make_async_client(),
            max_sources=num_sources,
            max_waves=2,
            topk_per_query=5,
            num_searches=num_searches,
            num_sources=num_sources,
        )
        
        plan = await manager.generate_plan(topic)
        
        # plan.queries → list of strings
        # plan.thoughts → planner reasoning text
        df = [[q] for q in (plan.queries or [])]
        thoughts = plan.thoughts or "No thoughts provided."
        status = f"✅ Generated {len(df)} search queries. Review and edit them below, then click 'Start Research'."
        
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

def _sources_table_to_text(sources_table) -> str:
    """
    Convert the sources dataframe/list into a plain-text list with numeric IDs
    that the Q&A agent can cite as [1], [2], ...
    """
    # Handle None or empty list first
    if sources_table is None:
        return "No sources were provided."
    
    # Handle possible pandas DataFrame
    rows = sources_table
    try:
        import pandas as pd
        if isinstance(sources_table, pd.DataFrame):
            if sources_table.empty:
                return "No sources were provided."
            rows = sources_table.values.tolist()
    except (ImportError, AttributeError):
        pass
    
    # Check if rows is empty (for list case)
    if not rows or len(rows) == 0:
        return "No sources were provided."

    lines = []
    for i, row in enumerate(rows, 1):
        # Expect shape: [Title, URL, Type, Published]
        if not row:
            continue
        title = str(row[0]) if len(row) > 0 else ""
        url = str(row[1]) if len(row) > 1 else ""
        source_type = str(row[2]) if len(row) > 2 else ""
        published = str(row[3]) if len(row) > 3 else ""
        lines.append(f"[{i}] ({source_type}) {title} | {url} | {published}")
    return "\n".join(lines) if lines else "No sources were provided."


async def qa_answer_callback(
    question: str,
    report_md: str,
    sources_table,
    chat_history: list,
):
    """
    Answer a user question based on the current report and sources.
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

    # Prepare sources text
    sources_text = _sources_table_to_text(sources_table)

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
    show_outline: bool,
):
    """
    Start the main research pipeline.
    """
    queries = [row[0] for row in (df_queries or []) if row and row[0].strip()]
    
    if not queries:
        yield ("", [], "❌ No queries found. Please generate or enter queries.", gr.update(visible=False))
        return

    # Run generator
    async for result in run_research_stream(
        topic,
        queries,
        num_sources,
        num_waves,
        files or [],
        show_outline,
    ):
        yield result

# -------------------------------------------------------------
# BUILD GRADIO INTERFACE
# -------------------------------------------------------------

def create_interface():
    with gr.Blocks(
        title="Deep Research Pro",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1200px !important;
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
            Upload PDFs, DOCX, or TXT files to include them in your research.
            """
        )
        
        with gr.Row():
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
                info="Number of search queries to generate"
            )
            
            num_sources = gr.Slider(
                minimum=5,
                maximum=50,
                value=25,
                step=1,
                label="Max Source Limit",
                info="Maximum number of sources to include in the report"
            )
            
            max_waves = gr.Slider(
                minimum=1,
                maximum=3,
                value=2,
                step=1,
                label="Max Research Waves",
                info="Maximum number of research iterations"
            )
            
            show_outline = gr.Checkbox(
                label="Show Outline Preview",
                value=False,
                info="Preview the report outline in the Live Log"
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
        with gr.Group(visible=False) as plan_section:
            plan_thoughts = gr.Markdown(
                label="Planning Thoughts",
                value=""
            )
            
            query_inputs = gr.Dataframe(
                headers=["Search Query"],
                datatype=["str"],
                row_count=5,
                col_count=1,
                wrap=True,
                label="Edit Search Queries",
                interactive=True,
            )
            
            with gr.Row():
                approve_btn = gr.Button("✅ Approve & Start Research", variant="primary")
                skip_btn = gr.Button("⏭️ Skip & Use Original", variant="secondary")
        
        with gr.Row():
            generate_plan_btn = gr.Button("📋 Generate Search Plan", variant="primary")
        
        # Hidden state for plan
        plan_state = gr.State(value={})
        analytics_state = gr.State(value=None)  # Will hold AnalyticsPayload
        
        # --- Live Log and Outline ---
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
                    placeholder="e.g., Summarize the key risks, or Compare the traditional vs AI-based approaches...",
                    lines=2,
                )
                with gr.Row():
                    qa_ask_btn = gr.Button("Ask", variant="primary")
                    qa_clear_btn = gr.Button("Clear", variant="secondary")
        
        # --- Execution ---
        with gr.Row():
            research_btn = gr.Button("🚀 Start Research", variant="primary")
        
        # --- Event Handlers ---
        
        # Generate plan button
        async def handle_generate_plan(topic, num_searches, num_sources):
            """Handle plan generation and show editing UI."""
            queries, thoughts, status, visibility = await generate_plan_callback(topic, num_searches, num_sources)
            
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
        
        # Start research button (direct start without plan)
        research_btn.click(
            fn=start_research_callback,
            inputs=[topic_input, query_inputs, num_sources, max_waves, file_upload, show_outline],
            outputs=[report_display, sources_table, live_log, outline_md, analytics_state],
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
        
        async def start_research_with_queries(topic, queries_df, num_searches, num_sources, max_waves, files, show_outline):
            """Extract queries and start research."""
            queries = extract_queries_from_df(queries_df)
            
            # Empty queries guard - show friendly error
            if not queries:
                yield ("", [], "❌ Please provide at least one search query. All queries are empty.", gr.update(visible=False), None)
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
            async for result in run_research_stream(topic, queries, num_sources, max_waves, files or [], show_outline):
                # Prepend status message to first status update if queries were capped
                if first_yield and status_msg:
                    report_md, sources_data, status, outline_update, analytics = result
                    if status:
                        status = status_msg + status
                    yield (report_md, sources_data, status, outline_update, analytics)
                    first_yield = False
                else:
                    yield result
                    first_yield = False
        
        approve_btn.click(
            fn=start_research_with_queries,
            inputs=[topic_input, query_inputs, num_searches, num_sources, max_waves, file_upload, show_outline],
            outputs=[report_display, sources_table, live_log, outline_md, analytics_state]
        )
        
        # Skip button - start research with original queries from state
        async def use_original_queries_and_start(state, topic, num_searches, num_sources, max_waves, files, show_outline):
            """Use original queries from state and start research."""
            queries = (state.get("queries") if state and "queries" in state else []) or []
            
            # Normalize queries format - handle both list of strings and list of lists
            if queries:
                if isinstance(queries[0], list):
                    # Extract strings from list of lists: [[q1], [q2]] -> [q1, q2]
                    queries = [q[0].strip() if isinstance(q, list) and len(q) > 0 and q[0] else str(q).strip() for q in queries if q]
                else:
                    # Handle list of strings: [q1, q2] -> [q1, q2]
                    queries = [str(q).strip() for q in queries if q and str(q).strip()]
            
            # Cap queries to num_searches (defensive)
            if len(queries) > num_searches:
                queries = queries[:num_searches]
                preface = f"ℹ️ Using first {num_searches} saved queries.\n\n"
            else:
                preface = ""
            
            first_yield = True
            async for result in run_research_stream(topic, queries, num_sources, max_waves, files or [], show_outline):
                report_md, sources_data, status_text, outline_update, analytics = result
                if first_yield and preface:
                    status_text = preface + status_text
                    preface = ""
                yield (report_md, sources_data, status_text, outline_update, analytics)
                first_yield = False
        
        skip_btn.click(
            fn=use_original_queries_and_start,
            inputs=[plan_state, topic_input, num_searches, num_sources, max_waves, file_upload, show_outline],
            outputs=[report_display, sources_table, live_log, outline_md, analytics_state]
        )
        
        # --- Q&A Handlers ---
        
        # Ask button → use current report + sources + chat history
        qa_ask_btn.click(
            fn=qa_answer_callback,
            inputs=[qa_question, report_display, sources_table, qa_chat],
            outputs=[qa_chat, qa_question],
        )
        
        # Allow Enter key to submit Q&A question
        qa_question.submit(
            fn=qa_answer_callback,
            inputs=[qa_question, report_display, sources_table, qa_chat],
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
                - ✅ User-guided query planning with review and editing
                - ✅ File upload support (PDF, DOCX, TXT) with semantic chunking and parallel processing
                - ✅ Parallel search execution with concurrent API calls (50x speedup)
                - ✅ Two-level caching system (L1: in-memory, L2: SQLite persistent) with 24h TTL and LRU management
                - ✅ Time-sensitive query detection (auto-bypasses cache for "latest", "today", "breaking")
                
                **Report Generation:**
                - ✅ Structured outputs with Pydantic schemas and validation
                - ✅ Cross-source synthesis with multi-citation support ([1][2][3])
                - ✅ Comprehensive 2000-5000 word reports with adaptive section structures
                - ✅ Styled citation boxes with clickable links
                - ✅ Source deduplication and intelligent filtering (top-K by content richness)
                - ✅ Subtopic extraction and theme analysis for better organization
                - ✅ Output quality validation with automatic retry on failure
                
                **UI & Analytics:**
                - ✅ Real-time streaming updates with Live Log
                - ✅ Analytics dashboard with Plotly visualizations (sources, citations, efficiency metrics)
                - ✅ Interactive Q&A about generated reports (ReportQAAgent)
                - ✅ Export to Markdown and HTML with full citations
                - ✅ Query-level summaries for better context integration
                
                **Technical Features:**
                - ✅ Token estimation and prompt optimization (3000 char summary limit)
                - ✅ URL normalization and citation management
                - ✅ Database migration logic for cache schema evolution
                - ✅ Source credibility scoring based on domain analysis
                - ✅ Safe async execution with comprehensive error handling
                
                ### How It Works
                
                1. **Planning**: QueryGeneratorAgent creates diverse search queries covering multiple research angles (background, stats, trends, case studies, risks, etc.)
                2. **Query Review** (optional): Review and edit AI-generated queries before execution
                3. **File Processing** (optional): Processes uploaded documents using LLM-based semantic chunking and parallel summarization
                4. **Search Waves**: Searches the web in parallel for relevant sources with query-level summaries
                5. **Follow-Up Decision**: FollowUpDecisionAgent analyzes findings and decides if additional research waves are needed
                6. **Source Processing**: Deduplicates sources, filters to top-K by content richness, and normalizes URLs
                7. **Writing**: WriterAgent synthesizes sources into structured 2000-5000 word research reports with inline citations
                8. **Validation**: Validates output quality and retries with simplified prompt if needed
                9. **Rendering**: Converts to markdown with styled citations and generates References section
                
                ### Tips
                
                - Use specific topics for better results (e.g., "AI in Healthcare: diagnostics, treatment, and ethics")
                - The system uses GPT-4o for all agent operations with advanced prompt engineering
                - Upload relevant documents to enhance your research (processed in parallel)
                - Review and edit queries in the planning phase for better control
                - Check the Analytics tab after research for detailed metrics and visualizations
                - Use the Q&A tab to explore your generated report interactively
                
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
