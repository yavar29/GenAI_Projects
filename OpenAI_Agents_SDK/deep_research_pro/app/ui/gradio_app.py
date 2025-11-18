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
    Yields: (report_md, sources_data, status_text, analytics)
    """
    if not topic or topic.strip() == "":
        yield ("", [], "❌ Please provide a research topic.", None)
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
        yield ("", [], "❌ Please provide at least one search query.", None)
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
            report_md, sources_data, status_text, analytics = result
            
            # Trim log to prevent excessive growth
            status_text = _truncate_message(status_text, max_chars=8000)
            status_text = _trim_log(status_text, max_lines=400)
            
            # Add auto-scroll anchor
            status_text += '\n\n<a href="#end"> </a><div id="end"></div>'
            
            yield (report_md, sources_data, status_text, analytics)
        return

    # Save uploaded files to disk
    uploaded_paths = []
    if uploaded_files:
        try:
            uploaded_paths = save_uploads(uploaded_files)
        except Exception as e:
            yield ("", [], f"❌ Error saving uploaded files: {e}", None)
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
        yield ("", [], f"❌ Failed to initialize ResearchManager: {ex}", None)
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
            
            yield (report_md, sources_data, status_text, analytics)
    except Exception as e:
        yield ("", [], f"❌ Error during research: {str(e)}", None)

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
        # Expect shape: [Title, URL, Type]
        if not row:
            continue
        title = str(row[0]) if len(row) > 0 else ""
        url = str(row[1]) if len(row) > 1 else ""
        source_type = str(row[2]) if len(row) > 2 else ""
        lines.append(f"[{i}] ({source_type}) {title} | {url}")
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
    
    # Build CSS with background image URL (using placeholder replacement)
    css_template = """
        /* Background Image - 123.jpeg */
        body {
            background-image: url('__BG_IMAGE_URL__') !important;
            background-size: cover !important;
            background-position: center center !important;
            background-attachment: fixed !important;
            background-repeat: no-repeat !important;
            min-height: 100vh !important;
        }
        
        /* Ensure background is visible */
        #root {
            background: transparent !important;
        }
        
        /* Make sure body shows the background */
        body {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* Overlay for readability - one shade lighter than header */
        .gradio-container {
            background: rgba(60, 60, 70, 0.95) !important;
            backdrop-filter: blur(10px) !important;
            border-radius: 20px !important;
            padding: 2rem !important;
            margin: 2rem auto !important;
            max-width: 1400px !important;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(80, 80, 90, 0.3);
        }
        
        /* Hero Header with dark background and image */
        .gradio-container > div:first-child {
            background: linear-gradient(135deg, #2d2d35 0%, #1f1f28 100%) !important;
            padding: 3rem 2.5rem !important;
            border-radius: 16px !important;
            margin: -2rem -2rem 2rem -2rem !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5) !important;
            display: flex !important;
            align-items: center !important;
            gap: 3rem !important;
            flex-wrap: wrap !important;
        }
        
        /* Header image container - much bigger */
        .header-image-container {
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .header-image-container img {
            max-width: 250px;
            max-height: 250px;
            width: auto;
            height: auto;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            object-fit: contain;
        }
        
        /* Header text container */
        .header-text-container {
            flex: 1;
            min-width: 300px;
        }
        
        .gradio-container > div:first-child h1 {
            color: #ffffff !important;
            font-size: 4rem !important;
            font-weight: 900 !important;
            margin: 0 !important;
            letter-spacing: -0.03em !important;
            line-height: 1.1 !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
            text-align: left !important;
        }
        
        .gradio-container > div:first-child h3 {
            color: rgba(255, 255, 255, 0.9) !important;
            font-size: 1.75rem !important;
            font-weight: 500 !important;
            margin: 1rem 0 0 0 !important;
            text-align: left !important;
        }
        
        .gradio-container > div:first-child p {
            color: rgba(255, 255, 255, 0.85) !important;
            font-size: 1.15rem !important;
            margin-top: 1.5rem !important;
            text-align: left !important;
            line-height: 1.6 !important;
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
        /* Report Display - Professional Document Box */
        .report-markdown {
            background: white !important;
            border: 2px solid rgba(249, 115, 22, 0.2) !important;
            border-radius: 16px !important;
            padding: 3rem 2.5rem !important;
            margin: 1.5rem 0 !important;
            box-shadow: 0 8px 24px rgba(249, 115, 22, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08) !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Inter', 'Helvetica Neue', Arial, sans-serif !important;
            line-height: 1.8 !important;
            color: #1e293b !important;
            max-width: 100% !important;
        }
        
        /* Report Typography */
        .report-markdown h1 {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            color: #1e293b !important;
            margin-top: 0 !important;
            margin-bottom: 1.5rem !important;
            padding-bottom: 1rem !important;
            border-bottom: 3px solid #f97316 !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            letter-spacing: -0.02em !important;
        }
        
        .report-markdown h2 {
            font-size: 1.875rem !important;
            font-weight: 600 !important;
            color: #1e293b !important;
            margin-top: 2.5rem !important;
            margin-bottom: 1.25rem !important;
            padding-bottom: 0.75rem !important;
            border-bottom: 2px solid rgba(249, 115, 22, 0.2) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }
        
        .report-markdown h3 {
            font-size: 1.5rem !important;
            font-weight: 600 !important;
            color: #334155 !important;
            margin-top: 2rem !important;
            margin-bottom: 1rem !important;
        }
        
        .report-markdown p {
            font-size: 1.0625rem !important;
            line-height: 1.85 !important;
            color: #334155 !important;
            margin-bottom: 1.25rem !important;
            text-align: justify !important;
        }
        
        .report-markdown ul, .report-markdown ol {
            margin: 1.25rem 0 !important;
            padding-left: 2rem !important;
            color: #334155 !important;
        }
        
        .report-markdown li {
            margin-bottom: 0.75rem !important;
            line-height: 1.75 !important;
            color: #334155 !important;
        }
        
        .report-markdown strong {
            font-weight: 600 !important;
            color: #1e293b !important;
        }
        
        .report-markdown em {
            font-style: italic !important;
            color: #475569 !important;
        }
        
        /* Table of Contents Styling */
        .report-markdown h2 + ul {
            background: #fff7ed !important;
            border: 1px solid rgba(249, 115, 22, 0.15) !important;
            border-radius: 8px !important;
            padding: 1.5rem !important;
            margin: 1.5rem 0 !important;
        }
        
        .report-markdown ul li a[href^="#"] {
            color: #ea580c !important;
            text-decoration: none !important;
            font-weight: 500 !important;
            transition: color 0.2s ease !important;
        }
        
        .report-markdown ul li a[href^="#"]:hover {
            color: #f97316 !important;
            text-decoration: underline !important;
        }
        
        /* Citation Links - Plain text style, no background, but clickable */
        .report-markdown a[href] {
            display: inline;
            padding: 0;
            margin: 0;
            background-color: transparent !important;
            border: none !important;
            border-radius: 0;
            color: inherit !important;
            text-decoration: none;
            font-size: inherit;
            font-weight: inherit;
            transition: color 0.2s ease;
        }
        .report-markdown a[href]:hover {
            background-color: transparent !important;
            border: none !important;
            color: #ea580c !important;
            text-decoration: underline;
            transform: none;
        }
        /* Only style non-citation links (like in references) */
        .report-markdown p[id^="ref-"] a[href] {
            color: #ea580c !important;
            text-decoration: underline;
        }
        .report-markdown p[id^="ref-"] a[href]:hover {
            color: #f97316 !important;
        }
        
        /* Code blocks */
        .report-markdown code {
            background: #fff7ed !important;
            color: #ea580c !important;
            padding: 0.2rem 0.5rem !important;
            border-radius: 4px !important;
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace !important;
            font-size: 0.9em !important;
            border: 1px solid rgba(249, 115, 22, 0.2) !important;
        }
        
        .report-markdown pre {
            background: #fff7ed !important;
            border: 1px solid rgba(249, 115, 22, 0.2) !important;
            border-radius: 8px !important;
            padding: 1.25rem !important;
            overflow-x: auto !important;
            margin: 1.5rem 0 !important;
        }
        
        .report-markdown pre code {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
        }
        
        /* Tables */
        .report-markdown table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin: 1.5rem 0 !important;
            background: white !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important;
        }
        
        .report-markdown th {
            background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important;
            color: white !important;
            padding: 1rem !important;
            text-align: left !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
        }
        
        .report-markdown td {
            padding: 0.875rem 1rem !important;
            border-bottom: 1px solid rgba(249, 115, 22, 0.1) !important;
            color: #334155 !important;
        }
        
        .report-markdown tr:hover {
            background: #fff7ed !important;
        }
        
        /* Blockquotes */
        .report-markdown blockquote {
            border-left: 4px solid #f97316 !important;
            padding-left: 1.5rem !important;
            margin: 1.5rem 0 !important;
            color: #475569 !important;
            font-style: italic !important;
            background: #fff7ed !important;
            padding: 1rem 1.5rem !important;
            border-radius: 0 8px 8px 0 !important;
        }
        
        /* Horizontal rules */
        .report-markdown hr {
            border: none !important;
            border-top: 2px solid rgba(249, 115, 22, 0.2) !important;
            margin: 2.5rem 0 !important;
        }
        
        /* References dropdown section */
        .report-markdown details {
            margin: 2rem 0 !important;
            padding: 1rem 0 !important;
            border-top: 2px solid rgba(249, 115, 22, 0.2) !important;
        }
        
        .report-markdown details summary {
            cursor: pointer;
            padding: 0.75rem 0 !important;
            font-weight: 600;
            color: #1e293b !important;
            user-select: none;
            list-style: none;
        }
        
        .report-markdown details summary::-webkit-details-marker {
            display: none;
        }
        
        .report-markdown details summary::before {
            content: "▶ ";
            display: inline-block;
            margin-right: 0.5rem;
            transition: transform 0.2s ease;
            color: #f97316;
        }
        
        .report-markdown details[open] summary::before {
            transform: rotate(90deg);
        }
        
        .report-markdown details summary h2 {
            display: inline !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        .report-markdown details p[id^="ref-"] {
            padding: 0.75rem 0 !important;
            border-bottom: 1px solid rgba(249, 115, 22, 0.1) !important;
            margin: 0 !important;
        }
        
        .report-markdown details p[id^="ref-"]:last-of-type {
            border-bottom: none !important;
        }
        /* Plan section - add padding to prevent content from touching borders */
        .plan-section {
            padding: 1.5rem !important;
            background: rgba(255, 255, 255, 0.8) !important;
            border-radius: 12px !important;
            backdrop-filter: blur(5px) !important;
        }
        .plan-section .dataframe,
        .plan-section .gr-df {
            margin: 1rem 0 !important;
            padding: 0.5rem !important;
        }
        
        /* Cards and sections with better visibility */
        .gr-group,
        .gr-accordion,
        .gr-tab {
            background: rgba(255, 255, 255, 0.9) !important;
            backdrop-filter: blur(5px) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            margin: 1rem 0 !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Input fields with better visibility */
        .gr-textbox,
        .gr-textarea,
        .gr-slider {
            background: rgba(255, 255, 255, 0.95) !important;
            border: 2px solid rgba(249, 115, 22, 0.3) !important;
            border-radius: 8px !important;
            color: #1e293b !important;
        }
        
        .gr-textbox:focus,
        .gr-textarea:focus {
            border-color: #f97316 !important;
            box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.2) !important;
        }
        
        /* Labels and text inside container - light colors for dark background */
        .gradio-container label,
        .gradio-container .gr-label,
        .gradio-container .gr-markdown,
        .gradio-container p:not(.report-markdown p),
        .gradio-container span:not(.report-markdown span) {
            color: rgba(255, 255, 255, 0.9) !important;
        }
        
        /* Ensure input text is dark */
        .gr-textbox input,
        .gr-textarea textarea {
            color: #1e293b !important;
        }
        
        /* Buttons with better styling */
        .gr-button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        }
        
        .gr-button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3) !important;
        }
        
        /* Tabs with better styling */
        .gr-tabs {
            background: rgba(255, 255, 255, 0.95) !important;
            border-radius: 12px !important;
            padding: 1rem !important;
            margin: 1rem 0 !important;
        }
        
        /* Live log with better visibility */
        #live-log {
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(5px) !important;
            border: 2px solid rgba(249, 115, 22, 0.2) !important;
        }
        
        /* File upload area */
        .gr-file {
            background: rgba(255, 255, 255, 0.9) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
        }
        """
    
    # Replace placeholder with actual background image URL
    css_content = css_template.replace('__BG_IMAGE_URL__', bg_image_url)
    
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
                    with gr.Column(scale=0, min_width=280):
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
        
        with gr.Row():
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
                        return gr.File(visible=False)
                    except Exception as e:
                        # Log error but don't crash
                        import traceback
                        print(f"PDF export error: {e}")
                        print(traceback.format_exc())
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
            
            with gr.Tab("📚 Sources"):
                sources_table = gr.Dataframe(
                    headers=["Title", "URL", "Type"],
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
                yield ("", [], "❌ Please provide at least one search query. All queries are empty.", None)
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
            yield (placeholder_report, [], status_msg, None)
            status_msg = ""
            
            # Start research with queries from the table
            first_yield = False
            async for result in run_research_stream(topic, queries, num_sources, max_waves, files or [], test_mode=test_mode):
                # Prepend status message to first status update if queries were capped
                if first_yield and status_msg:
                    report_md, sources_data, status, analytics = result
                    if status:
                        status = status_msg + status
                    yield (report_md, sources_data, status, analytics)
                    first_yield = False
                else:
                    yield result
                    first_yield = False
        
        approve_btn.click(
            fn=start_research_with_queries,
            inputs=[topic_input, query_inputs, num_sources, max_waves, file_upload, test_mode],
            outputs=[report_display, sources_table, live_log, analytics_state]
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
                - ✅ Export to Markdown, HTML, and PDF with full citations
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
