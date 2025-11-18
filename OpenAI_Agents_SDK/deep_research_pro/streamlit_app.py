"""
Streamlit interface for Deep Research Pro.
Provides an interactive web UI for the research assistant with file upload support.
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st
import os
import asyncio
from typing import Optional, List, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
from app.ui.test_data import generate_fake_research_stream, generate_fake_sources, generate_fake_report
from app.core.render import render_html_from_markdown, render_pdf_from_markdown

# Ensure OPENAI_API_KEY is in environment for Agents SDK
if OPENAI_API_KEY and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# -------------------------------------------------------------
# Page Configuration
# -------------------------------------------------------------

st.set_page_config(
    page_title=f"{PROJECT_NAME}",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# Styling
# -------------------------------------------------------------

def apply_styling():
    """Apply styling to Streamlit."""
    st.markdown(
        """
        <style>
            .stApp {
                background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
                background-attachment: fixed;
            }
            
            .main .block-container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 2rem;
                margin: 2rem auto;
                max-width: 1400px;
                box-shadow: 0 20px 60px rgba(249, 115, 22, 0.15);
                border: 1px solid rgba(249, 115, 22, 0.1);
            }
            
            .stMarkdown h1 {
                color: #1e293b;
                font-size: 3.5rem;
                font-weight: 800;
                text-align: center;
                margin-bottom: 1rem;
                background: linear-gradient(135deg, rgba(249, 115, 22, 0.95) 0%, rgba(234, 88, 12, 0.95) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .stMarkdown h3 {
                color: #334155;
                text-align: center;
                margin-bottom: 2rem;
            }
            
            /* Input fields */
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea {
                background: white !important;
                border: 2px solid rgba(249, 115, 22, 0.2) !important;
                border-radius: 8px !important;
            }
            
            .stTextInput > div > div > input:focus,
            .stTextArea > div > div > textarea:focus {
                border-color: #f97316 !important;
                box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1) !important;
            }
            
            /* Buttons */
            .stButton > button {
                background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 2px 8px rgba(249, 115, 22, 0.3) !important;
            }
            
            .stButton > button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(249, 115, 22, 0.4) !important;
            }
            
            /* Cards and containers */
            .stExpander {
                background: rgba(255, 255, 255, 0.9) !important;
                border-radius: 12px !important;
                border: 1px solid rgba(249, 115, 22, 0.2) !important;
            }
            
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {
                background: rgba(255, 255, 255, 0.95) !important;
                border-radius: 12px !important;
                padding: 0.5rem !important;
            }
            
            .stTabs [data-baseweb="tab"] {
                border-radius: 8px !important;
            }
            
            .stTabs [aria-selected="true"] {
                background: rgba(249, 115, 22, 0.1) !important;
                color: #ea580c !important;
            }
            
            /* Report styling */
            .report-container {
                background: white;
                border: 2px solid rgba(249, 115, 22, 0.2);
                border-radius: 16px;
                padding: 3rem 2.5rem;
                margin: 1.5rem 0;
                box-shadow: 0 8px 24px rgba(249, 115, 22, 0.12);
            }
            
            .report-container h1 {
                font-size: 2.5rem;
                font-weight: 700;
                color: #1e293b;
                border-bottom: 3px solid #f97316;
                padding-bottom: 1rem;
                margin-bottom: 1.5rem;
            }
            
            .report-container h2 {
                font-size: 1.875rem;
                font-weight: 600;
                color: #1e293b;
                margin-top: 2.5rem;
                border-bottom: 2px solid rgba(249, 115, 22, 0.2);
                padding-bottom: 0.75rem;
            }
            
            .report-container p {
                font-size: 1.0625rem;
                line-height: 1.85;
                color: #334155;
                margin-bottom: 1.25rem;
                text-align: justify;
            }
            
            .report-container a {
                color: #ea580c;
                text-decoration: none;
            }
            
            .report-container a:hover {
                text-decoration: underline;
            }
            
            /* Data editor */
            .stDataEditor {
                background: white !important;
                border-radius: 8px !important;
            }
            
            /* File uploader */
            .stFileUploader {
                background: rgba(255, 255, 255, 0.9) !important;
                border-radius: 12px !important;
                padding: 1rem !important;
            }
            
            /* Metrics */
            [data-testid="stMetricValue"] {
                color: #ea580c !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

apply_styling()

# -------------------------------------------------------------
# Utilities
# -------------------------------------------------------------

def save_uploads(uploaded_files) -> List[str]:
    """Save uploaded files to UPLOAD_DIR and return their paths."""
    if not uploaded_files:
        return []
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    saved_paths = []
    
    for uploaded_file in uploaded_files:
        fname = uploaded_file.name
        dest = os.path.join(UPLOAD_DIR, fname)
        
        with open(dest, "wb") as out:
            out.write(uploaded_file.getbuffer())
        
        saved_paths.append(dest)
    
    return saved_paths

# -------------------------------------------------------------
# State Management
# -------------------------------------------------------------

if 'report_md' not in st.session_state:
    st.session_state.report_md = "# Your research report will appear here...\n\nEnter a topic above and click 'Approve & Start Research' to begin."

if 'sources_data' not in st.session_state:
    st.session_state.sources_data = []

if 'analytics' not in st.session_state:
    st.session_state.analytics = None

if 'live_log' not in st.session_state:
    st.session_state.live_log = "Ready."

if 'qa_history' not in st.session_state:
    st.session_state.qa_history = []

if 'research_in_progress' not in st.session_state:
    st.session_state.research_in_progress = False

if 'queries' not in st.session_state:
    st.session_state.queries = []

if 'plan_thoughts' not in st.session_state:
    st.session_state.plan_thoughts = ""

# -------------------------------------------------------------
# Research Execution
# -------------------------------------------------------------

async def run_research_stream(
    topic: str,
    queries: list,
    num_sources: int,
    num_waves: int,
    uploaded_files: list,
    test_mode: bool = False,
):
    """Async generator for research stream."""
    if not topic or topic.strip() == "":
        yield ("", [], "❌ Please provide a research topic.", None)
        return

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
            yield result
        return

    # Save uploaded files
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
            num_searches=len(queries),
            num_sources=num_sources,
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
            yield result
    except Exception as e:
        yield ("", [], f"❌ Error during research: {str(e)}", None)

# -------------------------------------------------------------
# UI Components
# -------------------------------------------------------------

# Hero Header
st.markdown(f"# 🔬 {PROJECT_NAME}")
st.markdown("### AI-Powered Research Assistant")
st.markdown("Enter a research topic below and get a comprehensive research report with citations. Upload PDFs, DOCX, or TXT files to include them in your research.")

# Research Topic Input
topic = st.text_input(
    "Research Topic",
    value="AI in Healthcare",
    placeholder="e.g., AI in Healthcare, Climate Change Solutions, Quantum Computing",
    help="Enter the topic you want to research"
)

# Advanced Options
with st.expander("Advanced Options", expanded=False):
    test_mode = st.checkbox(
        "🧪 Test Mode (No API Calls)",
        value=False,
        help="Enable to test the UI with fake data without making API calls that cost money"
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num_searches = st.slider(
            "Number of Searches",
            min_value=3,
            max_value=10,
            value=5,
            step=1,
            help="Number of search queries to generate"
        )
    
    with col2:
        num_sources = st.slider(
            "Max Source Limit",
            min_value=5,
            max_value=50,
            value=25,
            step=1,
            help="Maximum number of sources to include in the report"
        )
    
    with col3:
        max_waves = st.slider(
            "Max Research Waves",
            min_value=1,
            max_value=3,
            value=2,
            step=1,
            help="Maximum number of research iterations"
        )
    
    uploaded_files = st.file_uploader(
        f"📁 Upload Documents (PDF, DOCX, TXT) - Up to {MAX_UPLOAD_FILES} files",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )
    
    st.info("💾 **Cache Information**: Results are cached for 24 hours. Time-sensitive queries automatically bypass cache.")

# Plan Generation
if topic and topic.strip() and not st.session_state.get('research_in_progress', False):
    if st.button("🔍 Generate Search Plan", type="primary"):
        with st.spinner("Generating search plan..."):
            try:
                if test_mode:
                    # Fake plan for test mode
                    fake_queries = [
                        f"{topic}: Overview and Introduction",
                        f"{topic}: Current Trends and Developments",
                        f"{topic}: Key Challenges and Solutions",
                        f"{topic}: Future Outlook and Predictions",
                        f"{topic}: Case Studies and Examples",
                    ][:num_searches]
                    st.session_state.queries = fake_queries
                    st.session_state.plan_thoughts = f"Generated {len(fake_queries)} search queries in test mode."
                else:
                    manager = ResearchManager(
                        client=make_async_client(),
                        max_sources=num_sources,
                        max_waves=2,
                        topk_per_query=5,
                        num_searches=num_searches,
                        num_sources=num_sources,
                    )
                    plan = asyncio.run(manager.generate_plan(topic))
                    st.session_state.queries = plan.queries or []
                    st.session_state.plan_thoughts = plan.thoughts or "No thoughts provided."
                
                st.success(f"✅ Generated {len(st.session_state.queries)} search queries!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error generating plan: {e}")

# Display Plan
if st.session_state.queries and not st.session_state.get('research_in_progress', False):
    st.markdown("### ✏️ Edit Search Queries")
    
    if st.session_state.plan_thoughts:
        with st.expander("Planning Thoughts", expanded=False):
            st.markdown(st.session_state.plan_thoughts)
    
    # Editable queries
    queries_df = pd.DataFrame({
        "Search Query": st.session_state.queries
    })
    edited_queries_df = st.data_editor(
        queries_df,
        use_container_width=True,
        num_rows="dynamic",
        key="queries_editor"
    )
    
    if st.button("✅ Approve & Start Research", type="primary"):
        queries = edited_queries_df["Search Query"].tolist()
        queries = [q.strip() for q in queries if q and str(q).strip()]
        
        if not queries:
            st.error("❌ Please provide at least one search query.")
        else:
            # Store queries for async execution
            st.session_state.pending_queries = queries
            st.session_state.pending_topic = topic
            st.session_state.pending_num_sources = num_sources
            st.session_state.pending_max_waves = max_waves
            st.session_state.pending_uploaded_files = list(uploaded_files) if uploaded_files else []
            st.session_state.pending_test_mode = test_mode
            st.session_state.research_in_progress = True
            st.rerun()

# Tabs for Results
if st.session_state.report_md and not st.session_state.report_md.startswith("# Your research report"):
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Report", "📚 Sources", "📊 Analytics", "💬 Q&A"])
    
    with tab1:
        # Render markdown to HTML for better styling
        from app.core.render import render_html_from_markdown
        html_content = render_html_from_markdown(st.session_state.report_md)
        st.markdown(html_content, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Export Markdown"):
                try:
                    path = Path("data/exported_report.md")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(st.session_state.report_md, encoding="utf-8")
                    with open(path, "rb") as f:
                        st.download_button(
                            "Download Markdown",
                            f.read(),
                            file_name="research_report.md",
                            mime="text/markdown"
                        )
                except Exception as e:
                    st.error(f"Error exporting: {e}")
        
        with col2:
            if st.button("🌐 Export HTML"):
                try:
                    html = render_html_from_markdown(st.session_state.report_md)
                    path = Path("data/exported_report.html")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(html, encoding="utf-8")
                    with open(path, "rb") as f:
                        st.download_button(
                            "Download HTML",
                            f.read(),
                            file_name="research_report.html",
                            mime="text/html"
                        )
                except Exception as e:
                    st.error(f"Error exporting: {e}")
        
        with col3:
            if st.button("📄 Export PDF"):
                try:
                    path = Path("data/exported_report.pdf")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    render_pdf_from_markdown(st.session_state.report_md, str(path.resolve()))
                    with open(path, "rb") as f:
                        st.download_button(
                            "Download PDF",
                            f.read(),
                            file_name="research_report.pdf",
                            mime="application/pdf"
                        )
                except ImportError:
                    st.error("weasyprint is required for PDF export. Install it with: pip install weasyprint")
                except Exception as e:
                    st.error(f"Error exporting: {e}")
    
    with tab2:
        if st.session_state.sources_data:
            sources_df = pd.DataFrame(
                st.session_state.sources_data,
                columns=["Title", "URL", "Type"]
            )
            st.dataframe(sources_df, use_container_width=True, hide_index=True)
        else:
            st.info("No sources available yet.")
    
    with tab3:
        if st.session_state.analytics:
            analytics = st.session_state.analytics
            
            # Overview
            st.markdown("## 📈 Session Overview")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Word Count", analytics.overview.word_count)
            with col2:
                st.metric("Sections", analytics.overview.num_sections)
            with col3:
                st.metric("Sources", analytics.overview.num_sources)
            with col4:
                st.metric("Web Sources", analytics.overview.num_web_sources)
            
            # Charts
            if analytics.domain_stats:
                st.markdown("### Domain Distribution")
                df = pd.DataFrame([d.dict() for d in analytics.domain_stats])
                fig = px.bar(df, x='domain', y='count', title="Sources by Domain")
                st.plotly_chart(fig, use_container_width=True)
            
            if analytics.publication_stats:
                st.markdown("### Publication Timeline")
                df = pd.DataFrame([d.dict() for d in analytics.publication_stats if d.bucket != "Unknown"])
                if not df.empty:
                    fig = px.bar(df, x='bucket', y='count', title="Sources by Publication Year")
                    st.plotly_chart(fig, use_container_width=True)
            
            if analytics.wave_stats:
                st.markdown("### Wave Statistics")
                df = pd.DataFrame([w.dict() for w in analytics.wave_stats])
                fig = px.line(df, x='wave_index', y='num_sources_discovered', title="Sources Discovered per Wave")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No analytics available yet. Run a research session to see analytics.")
    
    with tab4:
        st.markdown("### Ask questions about this report")
        
        # Display chat history
        for message in st.session_state.qa_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Question input
        question = st.chat_input("Ask a question about the report...")
        
        if question:
            # Add user message
            st.session_state.qa_history.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            
            # Get answer
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        # Convert sources to text format
                        sources_text = "\n".join([
                            f"[{i+1}] ({row[2]}) {row[0]} | {row[1]}"
                            for i, row in enumerate(st.session_state.sources_data)
                        ]) if st.session_state.sources_data else "No sources available."
                        
                        qa_agent = ReportQAAgent(client=make_async_client())
                        answer = asyncio.run(qa_agent.answer_async(
                            question=question,
                            report_markdown=st.session_state.report_md,
                            sources_text=sources_text
                        ))
                        
                        st.markdown(answer)
                        st.session_state.qa_history.append({"role": "assistant", "content": answer})
                    except Exception as e:
                        error_msg = f"❌ Error: {e}"
                        st.error(error_msg)
                        st.session_state.qa_history.append({"role": "assistant", "content": error_msg})
        
        if st.button("Clear Chat"):
            st.session_state.qa_history = []
            st.rerun()

# Research Execution (runs when research_in_progress is True)
if st.session_state.get('research_in_progress', False):
    progress_bar = st.progress(0)
    status_text = st.empty()
    report_placeholder = st.empty()
    log_placeholder = st.empty()
    
    try:
        status_text.info("🚀 Starting research...")
        
        # Run research and update UI
        async def run_and_update():
            last_report = ""
            async for result in run_research_stream(
                topic=st.session_state.pending_topic,
                queries=st.session_state.pending_queries,
                num_sources=st.session_state.pending_num_sources,
                num_waves=st.session_state.pending_max_waves,
                uploaded_files=st.session_state.pending_uploaded_files,
                test_mode=st.session_state.pending_test_mode,
            ):
                report_md, sources_data, status, analytics = result
                
                # Update session state
                st.session_state.report_md = report_md
                st.session_state.sources_data = sources_data
                st.session_state.analytics = analytics
                st.session_state.live_log = status
                
                # Update UI in real-time
                log_placeholder.markdown(f"```\n{status}\n```")
                if report_md and report_md != last_report and not report_md.startswith("# Your research report"):
                    # Use markdown with HTML for styling
                    from app.core.render import render_html_from_markdown
                    html_content = render_html_from_markdown(report_md)
                    report_placeholder.markdown(html_content, unsafe_allow_html=True)
                    last_report = report_md
        
        # Run async function
        asyncio.run(run_and_update())
        
        # Mark research as complete
        st.session_state.research_in_progress = False
        status_text.success("✅ Research complete!")
        st.rerun()
        
    except Exception as e:
        st.session_state.research_in_progress = False
        status_text.error(f"❌ Error: {e}")
        import traceback
        st.error(traceback.format_exc())

# Live Log
with st.expander("📊 Live Log", expanded=True):
    st.code(st.session_state.live_log, language=None)

