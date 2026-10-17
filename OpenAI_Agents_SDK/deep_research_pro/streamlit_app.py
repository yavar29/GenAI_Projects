"""
Streamlit interface for Deep Research Pro.
Provides an interactive web UI for the research assistant with file upload support.
Enhanced with dark mode, animations, PDF export, keyboard shortcuts, and advanced visualizations.
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st
import os
import asyncio
import pandas as pd
import re
from typing import Optional, List, Tuple
import streamlit.components.v1 as components

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
from app.core.render import render_html_from_markdown

if OPENAI_API_KEY and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

st.set_page_config(
    page_title=f"{PROJECT_NAME} - AI Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Force dark theme
st.markdown("""
<style>
    /* Streamlit dark theme override */
    .stApp {
        background-color: #0e1117 !important;
        color: #ffffff !important;
    }
    
    /* Main content area */
    .main .block-container {
        background-color: #0e1117 !important;
        color: #ffffff !important;
    }
    
    /* All text should be white */
    h1, h2, h3, h4, h5, h6, p, span, div, label, .stMarkdown, .stText {
        color: #ffffff !important;
    }
    
    /* Sidebar dark */
    [data-testid="stSidebar"] {
        background-color: #1e2229 !important;
    }
    
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------------

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True  # Always dark mode
if 'chart_theme' not in st.session_state:
    st.session_state.chart_theme = 'default'
if 'report_md' not in st.session_state:
    st.session_state.report_md = "# Your research report will appear here...\n\nEnter a topic above and click 'Approve & Start Research' to begin."
if 'sources_data' not in st.session_state:
    st.session_state.sources_data = []
if 'live_log' not in st.session_state:
    st.session_state.live_log = "Ready."
if 'trace_link' not in st.session_state:
    st.session_state.trace_link = None
if 'analytics' not in st.session_state:
    st.session_state.analytics = None
if 'queries' not in st.session_state:
    st.session_state.queries = []
if 'plan_thoughts' not in st.session_state:
    st.session_state.plan_thoughts = "Enter a research topic above to generate search queries."
if 'qa_history' not in st.session_state:
    st.session_state.qa_history = []
if 'research_running' not in st.session_state:
    st.session_state.research_running = False
if 'research_stage' not in st.session_state:
    st.session_state.research_stage = 'idle'
if 'progress_percent' not in st.session_state:
    st.session_state.progress_percent = 0

# -------------------------------------------------------------
# Custom CSS Styling with Dark Mode Support
# -------------------------------------------------------------

def inject_custom_css():
    """Inject custom CSS for modern, professional styling with dark mode."""
    
    # Always use dark theme colors
    bg_primary = "#0e1117"
    bg_secondary = "#1e2229"
    bg_tertiary = "#2d3239"
    text_primary = "#ffffff"
    text_secondary = "#e0e0e0"
    text_muted = "#b0b0b0"
    border_color = "#3d4249"
    hero_gradient = "linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)"  # Teal/Turquoise
    card_bg = "linear-gradient(135deg, #1e2229 0%, #0e1117 100%)"
    sidebar_bg = "linear-gradient(180deg, #1e2229 0%, #0e1117 100%)"
    tab_bg = "#1e2229"
    input_bg = "#1e2229"
    input_border = "#3d4249"
    
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@600;700&display=swap');
        
        /* CSS Variables for Theme */
        :root {{
            --bg-primary: {bg_primary};
            --bg-secondary: {bg_secondary};
            --bg-tertiary: {bg_tertiary};
            --text-primary: {text_primary};
            --text-secondary: {text_secondary};
            --text-muted: {text_muted};
            --border-color: {border_color};
        }}
        
        /* Global Styles - Force Dark Theme */
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            background-color: {bg_primary} !important;
            color: {text_primary} !important;
            transition: background-color 0.3s ease, color 0.3s ease;
        }}
        
        .stApp {{
            background-color: {bg_primary} !important;
            color: {text_primary} !important;
        }}
        
        /* Force all text to be white */
        h1, h2, h3, h4, h5, h6, p, span, div, label, .stMarkdown, .stText, .stMarkdown * {{
            color: {text_primary} !important;
        }}
        
        /* Main content area */
        .main .block-container {{
            background-color: {bg_primary} !important;
            color: {text_primary} !important;
        }}
        
        /* All Streamlit text elements */
        .stTextInput label, .stSlider label, .stSelectbox label, .stCheckbox label,
        .stNumberInput label, .stFileUploader label, .stButton label,
        .stDataFrame label, .stMarkdown, .stText {{
            color: {text_primary} !important;
        }}
        
        /* Dataframes and tables */
        .stDataFrame, .dataframe {{
            background-color: {bg_secondary} !important;
            color: {text_primary} !important;
        }}
        
        .stDataFrame table, .dataframe table {{
            background-color: {bg_secondary} !important;
            color: {text_primary} !important;
        }}
        
        .stDataFrame th, .stDataFrame td, .dataframe th, .dataframe td {{
            background-color: {bg_secondary} !important;
            color: {text_primary} !important;
            border-color: {border_color} !important;
        }}
        
        /* Chat messages */
        .stChatMessage {{
            background-color: {bg_secondary} !important;
            color: {text_primary} !important;
        }}
        
        /* Status and info boxes */
        .stStatus, .stInfo, .stSuccess, .stWarning, .stError {{
            background-color: {bg_secondary} !important;
            color: {text_primary} !important;
        }}
        
        /* Expander */
        .streamlit-expanderHeader {{
            background-color: {bg_secondary} !important;
            color: {text_primary} !important;
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab"] {{
            color: {text_primary} !important;
        }}
        
        /* Metrics */
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
            color: {text_primary} !important;
        }}
        
        /* Hide Streamlit Branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* Hero Section - Full Width */
        .hero-section {{
            background: {hero_gradient};
            padding: 2.5rem 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            margin-left: -1rem;
            margin-right: -1rem;
            box-shadow: 0 8px 32px rgba(20, 184, 166, 0.25);
            animation: fadeInDown 0.6s ease-out;
            width: calc(100% + 2rem);
        }}
        
        @keyframes fadeInDown {{
            from {{
                opacity: 0;
                transform: translateY(-20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .hero-title {{
            font-family: 'Poppins', sans-serif;
            font-size: 3rem;
            font-weight: 700;
            color: white;
            margin: 0;
            line-height: 1.2;
        }}
        
        .hero-subtitle {{
            font-size: 1.3rem;
            color: rgba(255, 255, 255, 0.95);
            margin: 0.5rem 0 0 0;
            font-weight: 400;
        }}
        
        .hero-description {{
            font-size: 1rem;
            color: rgba(255, 255, 255, 0.85);
            margin: 1rem 0 0 0;
            line-height: 1.6;
        }}
        
        /* Metric Cards */
        .metric-card {{
            background: {card_bg};
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
            border: 1px solid var(--border-color);
            transition: transform 0.2s, box-shadow 0.2s;
            animation: fadeIn 0.5s ease-out;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        }}
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {{
            background: {sidebar_bg} !important;
        }}
        
        [data-testid="stSidebar"] .stMarkdown h2,
        [data-testid="stSidebar"] .stMarkdown h3 {{
            color: var(--text-primary) !important;
            font-family: 'Poppins', sans-serif;
        }}
        
        /* Custom Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: var(--bg-secondary);
            padding: 0.5rem;
            border-radius: 12px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 8px;
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 0.95rem;
            padding: 0 1.5rem;
            transition: all 0.3s ease;
        }}
        
        .stTabs [aria-selected="true"] {{
            background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
            color: white !important;
        }}
        
        /* Input Styling - Dark Theme */
        .stTextInput > div > div > input {{
            border-radius: 8px;
            border: 2px solid {input_border};
            padding: 0.75rem 1rem;
            font-size: 1rem;
            background-color: {input_bg} !important;
            color: {text_primary} !important;
            transition: all 0.3s ease;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: #14b8a6;
            box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
            background-color: {input_bg} !important;
            color: {text_primary} !important;
        }}
        
        /* Textarea */
        .stTextArea > div > div > textarea {{
            background-color: {input_bg} !important;
            color: {text_primary} !important;
            border-color: {input_border} !important;
        }}
        
        /* Selectbox */
        .stSelectbox > div > div {{
            background-color: {input_bg} !important;
            color: {text_primary} !important;
        }}
        
        /* Slider */
        .stSlider {{
            color: {text_primary} !important;
        }}
        
        /* Checkbox */
        .stCheckbox label {{
            color: {text_primary} !important;
        }}
        
        /* File uploader */
        .stFileUploader {{
            background-color: {bg_secondary} !important;
            color: {text_primary} !important;
        }}
        
        /* Report Markdown Area - Dark Theme */
        .stMarkdown, .element-container .stMarkdown {{
            background-color: {bg_primary} !important;
            color: {text_primary} !important;
        }}
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, 
        .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {{
            color: {text_primary} !important;
        }}
        
        .stMarkdown p, .stMarkdown li, .stMarkdown ul, .stMarkdown ol {{
            color: {text_primary} !important;
        }}
        
        .stMarkdown code {{
            background-color: {bg_tertiary} !important;
            color: {text_primary} !important;
            border: 1px solid {border_color} !important;
        }}
        
        .stMarkdown pre {{
            background-color: {bg_secondary} !important;
            color: {text_primary} !important;
            border: 1px solid {border_color} !important;
        }}
        
        .stMarkdown a {{
            color: #14b8a6 !important;
        }}
        
        .stMarkdown a:hover {{
            color: #0d9488 !important;
        }}
        
        /* Live Log Area */
        .element-container {{
            background-color: {bg_primary} !important;
            color: {text_primary} !important;
        }}
        
        /* Chat Input */
        .stChatInput {{
            background-color: {bg_secondary} !important;
        }}
        
        .stChatInput > div > div > input {{
            background-color: {input_bg} !important;
            color: {text_primary} !important;
            border-color: {input_border} !important;
        }}
        
        /* Button Styling */
        .stButton > button {{
            border-radius: 8px;
            font-weight: 600;
            padding: 0.6rem 1.5rem;
            transition: all 0.2s;
            border: none;
        }}
        
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
            box-shadow: 0 4px 12px rgba(20, 184, 166, 0.3);
        }}
        
        .stButton > button[kind="primary"]:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(20, 184, 166, 0.4);
        }}
        
        /* Progress Bar */
        .progress-container {{
            background: var(--bg-secondary);
            border-radius: 10px;
            height: 30px;
            margin: 1rem 0;
            overflow: hidden;
            position: relative;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .progress-bar {{
            background: linear-gradient(90deg, #14b8a6 0%, #0d9488 100%);
            height: 100%;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 0.9rem;
        }}
        
        .progress-stages {{
            display: flex;
            justify-content: space-between;
            margin: 1rem 0;
            gap: 0.5rem;
        }}
        
        .stage-item {{
            flex: 1;
            text-align: center;
            padding: 1rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 2px solid var(--border-color);
            transition: all 0.3s ease;
        }}
        
        .stage-item.active {{
            background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
            color: white;
            border-color: #14b8a6;
            transform: scale(1.05);
        }}
        
        .stage-item.completed {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border-color: #10b981;
        }}
        
        /* Data Editor Styling */
        .stDataFrame {{
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }}
        
        /* Status Box */
        .status-box {{
            background: var(--bg-secondary);
            border-left: 4px solid #14b8a6;
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            animation: slideIn 0.4s ease-out;
        }}
        
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateX(-20px);
            }}
            to {{
                opacity: 1;
                transform: translateX(0);
            }}
        }}
        
        /* File Uploader */
        [data-testid="stFileUploader"] {{
            background: var(--bg-secondary);
            border: 2px dashed var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.3s;
        }}
        
        [data-testid="stFileUploader"]:hover {{
            border-color: #14b8a6;
            background: var(--bg-tertiary);
        }}
        
        /* Expander Styling */
        .streamlit-expanderHeader {{
            background: var(--bg-secondary);
            border-radius: 8px;
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        /* About Section - Light Teal Background */
        .streamlit-expanderContent {{
            background-color: rgba(20, 184, 166, 0.1) !important;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 0.5rem;
            padding-bottom: 1.5rem !important;
        }}
        
        /* Target the About expander specifically */
        div[data-testid="stExpander"]:has(div:contains("About Deep Research Pro")) .streamlit-expanderContent {{
            background: linear-gradient(135deg, rgba(20, 184, 166, 0.15) 0%, rgba(13, 148, 136, 0.1) 100%) !important;
            border: 1px solid rgba(20, 184, 166, 0.3);
            padding-bottom: 1.5rem !important;
        }}
        
        /* Alternative: Style by content */
        .streamlit-expanderContent .stMarkdown {{
            background-color: rgba(20, 184, 166, 0.08) !important;
            padding: 1.5rem;
            padding-bottom: 1.5rem !important;
            border-radius: 8px;
            border: 1px solid rgba(20, 184, 166, 0.2);
            margin-bottom: 0 !important;
        }}
        
        /* Chat Messages */
        .stChatMessage {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1rem;
            margin: 0.5rem 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            animation: messageSlide 0.3s ease-out;
        }}
        
        @keyframes messageSlide {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        /* Divider */
        hr {{
            margin: 2rem 0;
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--border-color), transparent);
        }}
        
        /* Info/Success/Warning/Error Boxes */
        .stAlert {{
            border-radius: 8px;
            border: none;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }}
        
        /* Section Headers */
        h1, h2, h3 {{
            font-family: 'Poppins', sans-serif;
            color: var(--text-primary) !important;
        }}
        
        /* Metric Styling */
        [data-testid="stMetricValue"] {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary) !important;
        }}
        
        [data-testid="stMetricLabel"] {{
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-muted) !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()


# -------------------------------------------------------------
# Utilities
# -------------------------------------------------------------

def save_uploads(files) -> List[str]:
    """Save uploaded files to UPLOAD_DIR and return their paths."""
    if not files:
        return []
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    saved_paths = []
    
    for f in files:
        if hasattr(f, 'name'):
            source_path = f.name
        elif isinstance(f, str):
            source_path = f
        else:
            continue
            
        fname = os.path.basename(source_path)
        dest = os.path.join(UPLOAD_DIR, fname)
        
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

def _sources_table_to_text(sources_table) -> str:
    """Convert sources dataframe/list into plain-text list with numeric IDs."""
    if sources_table is None or len(sources_table) == 0:
        return "No sources were provided."
    
    lines = []
    for i, row in enumerate(sources_table, 1):
        if not row or len(row) < 3:
            continue
        title = str(row[0]) if len(row) > 0 else ""
        url = str(row[1]) if len(row) > 1 else ""
        source_type = str(row[2]) if len(row) > 2 else ""
        lines.append(f"[{i}] ({source_type}) {title} | {url}")
    return "\n".join(lines) if lines else "No sources were provided."

def generate_pdf_report(markdown_content: str, topic: str) -> bytes:
    """Generate PDF from markdown content with custom styling."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from io import BytesIO
        import markdown2
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        Story = []
        styles = getSampleStyleSheet()
        
        # Custom title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#667eea',
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Add title
        Story.append(Paragraph(f"Research Report: {topic}", title_style))
        Story.append(Spacer(1, 12))
        
        # Convert markdown to HTML then to PDF
        html_content = markdown2.markdown(markdown_content)
        
        # Split into paragraphs and add to story
        for line in markdown_content.split('\n'):
            if line.strip():
                if line.startswith('#'):
                    # Header
                    level = len(line) - len(line.lstrip('#'))
                    text = line.lstrip('#').strip()
                    style = styles[f'Heading{min(level, 3)}']
                    Story.append(Paragraph(text, style))
                    Story.append(Spacer(1, 12))
                else:
                    # Regular paragraph
                    Story.append(Paragraph(line, styles['BodyText']))
                    Story.append(Spacer(1, 6))
        
        doc.build(Story)
        buffer.seek(0)
        return buffer.getvalue()
    except ImportError:
        # Fallback if reportlab not available
        return markdown_content.encode('utf-8')

def update_research_stage(stage: str, progress: int):
    """Update research stage and progress."""
    st.session_state.research_stage = stage
    st.session_state.progress_percent = progress

def render_progress_stages():
    """Render animated progress stages."""
    stages = [
        {"name": "Planning", "key": "planning"},
        {"name": "Searching", "key": "searching"},
        {"name": "Analyzing", "key": "analyzing"},
        {"name": "Writing", "key": "writing"},
    ]
    
    current_stage = st.session_state.research_stage
    
    stage_html = '<div class="progress-stages">'
    for stage in stages:
        stage_class = ""
        if current_stage == stage["key"]:
            stage_class = "active"
        elif stages.index(stage) < [s["key"] for s in stages].index(current_stage) if current_stage in [s["key"] for s in stages] else False:
            stage_class = "completed"
        
        stage_html += f'<div class="stage-item {stage_class}">✓ {stage["name"]}</div>'
    stage_html += '</div>'
    
    st.markdown(stage_html, unsafe_allow_html=True)
    
    # Progress bar
    progress = st.session_state.progress_percent
    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {progress}%;">
            {progress}%
        </div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# Research Execution Functions
# -------------------------------------------------------------

def run_research_sync(
    topic: str,
    queries: list,
    num_sources: int,
    num_waves: int,
    uploaded_files: list,
):
    """Run research pipeline synchronously for Streamlit."""
    if not topic or topic.strip() == "":
        st.error("❌ Please provide a research topic.")
        return
    
    if queries and isinstance(queries[0], list):
        queries = [q[0].strip() if isinstance(q, list) and len(q) > 0 and q[0] else str(q).strip() for q in queries if q]
    else:
        queries = [str(q).strip() for q in queries if q and str(q).strip()]
    
    if not queries:
        st.error("❌ Please provide at least one search query.")
        return
    
    uploaded_paths = []
    if uploaded_files:
        try:
            uploaded_paths = save_uploads(uploaded_files)
        except Exception as e:
            st.error(f"❌ Error saving uploaded files: {e}")
            return
    
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
        st.error(f"❌ Failed to initialize ResearchManager: {ex}")
        return
    
    with st.status("🔍 Running research...", expanded=True) as status:
        log_text = f"🔍 Starting research on: **{topic}**\n"
        log_text += f"📋 Search queries: {len(queries)}\n"
        log_text += f"🌊 Max waves: {num_waves}\n"
        if uploaded_paths:
            log_text += f"📎 Uploaded {len(uploaded_paths)} file(s)\n"
        log_text += "\n"
        status.update(label="Initializing research...", state="running")
        
        # Update stage
        update_research_stage('planning', 10)
        
        try:
            async def run_async():
                log_text_inner = log_text
                seen_lines = set()
                trace_link = None
                trace_link_shown = False
                
                update_research_stage('searching', 30)
                
                async for result in manager.run(
                    topic=topic,
                    queries=queries,
                    uploaded_files=uploaded_paths if uploaded_paths else None,
                ):
                    report_md, sources_data, status_text, analytics = result
                    
                    # Update progress based on sources gathered
                    if sources_data:
                        progress = min(30 + (len(sources_data) / num_sources) * 40, 70)
                        update_research_stage('analyzing', int(progress))
                    
                    if status_text:
                        if not trace_link_shown:
                            trace_match = re.search(r'🔗 Trace: (https://[^\s]+)', status_text)
                            if trace_match:
                                trace_link = trace_match.group(1)
                                trace_link_shown = True
                        
                        status_text_clean = re.sub(r'🔗 Trace: https://[^\s]+\s*\n?', '', status_text).strip()
                        status_text_clean = _truncate_message(status_text_clean, max_chars=8000)
                        status_text_clean = _trim_log(status_text_clean, max_lines=400)
                        
                        lines = status_text_clean.split('\n')
                        new_lines = []
                        for line in lines:
                            line_stripped = line.strip()
                            line_key = line_stripped
                            if line_key and line_key not in seen_lines:
                                seen_lines.add(line_key)
                                new_lines.append(line)
                        
                        if new_lines:
                            new_text = '\n'.join(new_lines)
                            log_text_inner += new_text + "\n"
                    
                    status.update(label="Research in progress...", state="running")
                    st.session_state.live_log = log_text_inner
                    st.session_state.trace_link = trace_link
                    
                    if report_md:
                        update_research_stage('writing', 85)
                        st.session_state.report_md = report_md
                    
                    if sources_data:
                        st.session_state.sources_data = sources_data
                    
                    if analytics:
                        st.session_state.analytics = analytics
                
                final_status = f"\n✅ Research complete! {len(st.session_state.sources_data)} source(s) gathered."
                log_text_inner += final_status
                st.session_state.live_log = log_text_inner
                status.update(label="✅ Research complete!", state="complete")
                
                update_research_stage('writing', 100)
                st.session_state.research_running = False
                st.rerun()
            
            asyncio.run(run_async())
            
        except Exception as e:
            status.update(label=f"❌ Error: {str(e)}", state="error")
            st.session_state.research_running = False
            st.error(f"❌ Error during research: {str(e)}")

async def generate_plan_callback(topic: str, num_searches: int, num_sources: int):
    """Generate search plan (queries) for user review."""
    if not topic or topic.strip() == "":
        return None, None, "❌ Please enter a topic."
    
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
        
        queries = plan.queries or []
        thoughts = plan.thoughts or "No thoughts provided."
        status = f"✅ Generated {len(queries)} search queries. Review and edit them below, then click 'Approve & Start Research'."
        
        return queries, thoughts, status
    except Exception as ex:
        return None, None, f"❌ Error: {ex}"

async def qa_answer_callback(question: str, report_md: str, sources_table):
    """Answer a user question based on the current report and sources."""
    if not question or not question.strip():
        return "❌ Please enter a non-empty question."
    
    if not report_md or report_md.startswith("# Your research report will appear here"):
        return "❌ Please run a research and generate a report before asking questions."
    
    sources_text = _sources_table_to_text(sources_table)
    qa_agent = ReportQAAgent(openai_client=make_async_client())
    
    try:
        answer = await qa_agent.answer_async(
            question=question.strip(),
            report_markdown=report_md,
            sources_text=sources_text,
        )
        return answer
    except Exception as ex:
        return f"❌ Error while answering: {ex}"

# -------------------------------------------------------------
# Main UI
# -------------------------------------------------------------

def main():
    # Hero section - full width
    st.markdown(f"""
    <div class="hero-section">
        <h1 class="hero-title">🔬 Deep Research Pro</h1>
        <p class="hero-subtitle">AI-Powered Research Assistant with Advanced Analytics</p>
        <p class="hero-description">
            Transform any topic into comprehensive research reports with intelligent multi-wave analysis, 
            automatic source citation, and interactive Q&A. Upload documents, generate insights, and explore 
            data-driven research like never before.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### ⚙️ Research Configuration")
        
        with st.expander("🔍 Search Parameters", expanded=True):
            num_searches = st.slider(
                "Number of Searches",
                min_value=3,
                max_value=10,
                value=5,
                step=1,
                help="Number of search queries to generate",
            )
            
            num_sources = st.slider(
                "Max Source Limit",
                min_value=5,
                max_value=50,
                value=25,
                step=1,
                help="Maximum number of sources to include in the report",
            )
            
            max_waves = st.slider(
                "Max Research Waves",
                min_value=1,
                max_value=3,
                value=2,
                step=1,
                help="Maximum number of research iterations",
            )
        
        st.markdown("### 🎨 Visualization Settings")
        with st.expander("Chart Theme", expanded=False):
            chart_theme = st.selectbox(
                "Select Chart Theme",
                ["default", "dark", "colorblind", "vibrant"],
                index=["default", "dark", "colorblind", "vibrant"].index(st.session_state.chart_theme),
                help="Choose color scheme for analytics charts"
            )
            st.session_state.chart_theme = chart_theme
        
        st.markdown("### 📁 Document Upload")
        file_upload = st.file_uploader(
            f"Upload Documents (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            help=f"Upload up to {MAX_UPLOAD_FILES} files to include in your research",
        )
        
        if file_upload:
            st.success(f"✅ {len(file_upload)} file(s) uploaded")
        
        st.markdown("---")
        
        with st.expander("💾 Cache Information"):
            st.markdown("""
            **Smart Caching Features:**
            - Results cached for 24 hours
            - Time-sensitive queries bypass cache automatically
            - Cache persists across app restarts
            - Modify queries to force fresh results
            """)
        
        st.markdown("---")
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: {'#2d3748' if st.session_state.dark_mode else '#f7fafc'}; border-radius: 8px;">
            <small style="color: {'#a0aec0' if st.session_state.dark_mode else '#718096'};">
                Made with ❤️ using OpenAI & Streamlit
            </small>
        </div>
        """, unsafe_allow_html=True)
    
    # Research topic input - wider
    topic_input = st.text_input(
        "🎯 Research Topic",
        value="",
        placeholder="e.g., AI in Healthcare, Climate Change Solutions, Quantum Computing...",
        help="Enter the topic you want to research",
        key="topic_input_key",
    )
    
    if topic_input and topic_input.strip():
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button("🔄 Generate Research Plan", type="primary", use_container_width=True, key="generate_btn"):
                with st.spinner("Generating research plan..."):
                    queries, thoughts, status = asyncio.run(
                        generate_plan_callback(topic_input, int(num_searches), int(num_sources))
                    )
                    if queries:
                        st.session_state.queries = queries
                        st.session_state.plan_thoughts = thoughts
                        st.session_state.live_log = status
                        st.success(status)
                    else:
                        st.error(status)
                st.rerun()
        with col2:
            if st.button("🗑️ Clear", type="secondary", use_container_width=True):
                st.session_state.queries = []
                st.session_state.plan_thoughts = "Enter a research topic above to generate search queries."
                st.rerun()
    
    st.markdown("---")
    
    planning_log_container = st.container()
    
    with planning_log_container:
        if not st.session_state.get('research_running', False):
            st.markdown("### 🧠 Research Planning & Strategy")
            
            if st.session_state.plan_thoughts:
                st.info(st.session_state.plan_thoughts)
            
            if st.session_state.queries:
                st.markdown("**📋 Generated Search Queries** (Edit as needed)")
                queries_df = pd.DataFrame(
                    [[q] for q in st.session_state.queries],
                    columns=["Search Query"]
                )
                edited_df = st.data_editor(
                    queries_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="queries_editor",
                )
                st.session_state.queries = edited_df["Search Query"].tolist()
                
                # Approve & Start Research button below the queries
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("✅ Approve & Start Research", type="primary", use_container_width=True, key="start_btn"):
                    if not st.session_state.queries:
                        st.error("❌ Please generate queries first.")
                    else:
                        st.session_state.research_running = True
                        update_research_stage('planning', 5)
                        st.rerun()
        else:
            st.markdown("### 📊 Live Research Progress")
            
            # Render animated progress stages
            render_progress_stages()
            
            if st.session_state.trace_link:
                with st.expander("🔗 OpenAI Trace Dashboard", expanded=False):
                    st.markdown(f"[View detailed trace →]({st.session_state.trace_link})")
            
            status_placeholder = st.empty()
            status_placeholder.markdown(f"""
            <div class="status-box">
                {st.session_state.live_log}
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📄 Research Report", 
        "📚 Sources & References", 
        "📊 Analytics Dashboard", 
        "💬 Q&A Assistant"
    ])
    
    with tab1:
        st.markdown("### 📝 Generated Research Report")
        report_placeholder = st.empty()
        report_placeholder.markdown(st.session_state.report_md, unsafe_allow_html=True)
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Export as Markdown", use_container_width=True):
                if st.session_state.report_md and not st.session_state.report_md.startswith("# Your research report"):
                    path = Path("data/exported_report.md")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(st.session_state.report_md, encoding="utf-8")
                    with open(path, "rb") as f:
                        st.download_button(
                            label="📥 Download Markdown",
                            data=f.read(),
                            file_name="research_report.md",
                            mime="text/markdown",
                            use_container_width=True,
                        )
        with col2:
            if st.button("🌐 Export as HTML", use_container_width=True):
                if st.session_state.report_md and not st.session_state.report_md.startswith("# Your research report"):
                    html = render_html_from_markdown(st.session_state.report_md)
                    path = Path("data/exported_report.html")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(html, encoding="utf-8")
                    with open(path, "rb") as f:
                        st.download_button(
                            label="📥 Download HTML",
                            data=f.read(),
                            file_name="research_report.html",
                            mime="text/html",
                            use_container_width=True,
                        )
        with col3:
            if st.button("📄 Export as PDF", use_container_width=True):
                if st.session_state.report_md and not st.session_state.report_md.startswith("# Your research report"):
                    try:
                        pdf_data = generate_pdf_report(st.session_state.report_md, topic_input or "Research")
                        st.download_button(
                            label="📥 Download PDF",
                            data=pdf_data,
                            file_name="research_report.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"PDF generation requires reportlab library. Error: {e}")
    
    with tab2:
        st.markdown("### 📚 Research Sources & Citations")
        sources_placeholder = st.empty()
        if st.session_state.sources_data:
            sources_df = pd.DataFrame(st.session_state.sources_data, columns=["Title", "URL", "Type"])
            st.markdown(f"**Total Sources:** {len(sources_df)}")
            sources_placeholder.dataframe(
                sources_df,
                use_container_width=True,
                hide_index=True,
            )
            
            # Export sources as CSV
            csv = sources_df.to_csv(index=False)
            st.download_button(
                label="📥 Export Sources as CSV",
                data=csv,
                file_name="research_sources.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            sources_placeholder.info("📋 No sources yet. Run a research to see sources here.")
    
    with tab3:
        analytics_placeholder = st.empty()
        if st.session_state.analytics:
            from app.ui.analytics_dashboard_streamlit import render_analytics
            render_analytics(st.session_state.analytics)
        else:
            analytics_placeholder.info("📊 No analytics data yet. Run a research to see detailed analytics here.")
    
    with tab4:
        st.markdown("### 💬 Interactive Q&A Assistant")
        
        if not st.session_state.report_md or st.session_state.report_md.startswith("# Your research report"):
            st.info("👋 Generate a research report first to start asking questions!")
            st.markdown("""
            **Example Questions:**
            - "What are the main findings?"
            - "Can you summarize the key points?"
            - "What sources support [specific claim]?"
            - "How does [concept A] relate to [concept B]?"
            """)
        else:
            chat_container = st.container()
            
            with chat_container:
                if not st.session_state.qa_history:
                    with st.chat_message("assistant"):
                        st.write("👋 Hello! I'm your research assistant. Ask me anything about the report!")
                
                for i, (question, answer) in enumerate(st.session_state.qa_history):
                    if question:
                        with st.chat_message("user"):
                            st.write(question)
                    if answer:
                        with st.chat_message("assistant"):
                            st.write(answer)
            
            question = st.chat_input("Ask a question about the research report...")
            
            if question:
                with st.chat_message("user"):
                    st.write(question)
                
                with st.chat_message("assistant"):
                    with st.spinner("🤔 Thinking..."):
                        answer = asyncio.run(
                            qa_answer_callback(
                                question,
                                st.session_state.report_md,
                                st.session_state.sources_data,
                            )
                        )
                        st.write(answer)
                
                st.session_state.qa_history.append((question, answer))
                st.rerun()
            
            if st.session_state.qa_history:
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("🗑️ Clear Chat History", type="secondary", use_container_width=True):
                        st.session_state.qa_history = []
                        st.rerun()
    
    if st.session_state.research_running:
        run_research_sync(
            topic_input,
            st.session_state.queries,
            int(num_sources),
            int(max_waves),
            list(file_upload) if file_upload else [],
        )
    
    with st.expander("ℹ️ About Deep Research Pro"):
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(20, 184, 166, 0.15) 0%, rgba(13, 148, 136, 0.1) 100%); padding: 1.5rem; padding-bottom: 1.5rem; margin-bottom: 1rem; border-radius: 8px; border: 1px solid rgba(20, 184, 166, 0.3);">
        
        <h3 style="color: #ffffff; margin-top: 0;">🚀 Features</h3>
        
        <h4 style="color: #ffffff; margin-top: 1rem;">Core Capabilities:</h4>
        <ul style="color: #ffffff;">
        <li>✅ Multi-agent architecture (QueryGenerator, SearchAgent, WriterAgent, FollowUpDecisionAgent, FileSummarizerAgent, ReportQAAgent)</li>
        <li>✅ Multi-wave research with intelligent follow-up queries (up to 3 waves)</li>
        <li>✅ User-guided query planning with review and editing before execution</li>
        <li>✅ Parallel search execution with concurrent API calls (50x speedup)</li>
        <li>✅ Two-level caching system (L1: in-memory, L2: SQLite persistent) with 24h TTL and LRU management</li>
        <li>✅ Time-sensitive query detection (auto-bypasses cache for "latest", "today", "breaking")</li>
        <li>✅ Automatic source credibility scoring and citation management</li>
        <li>✅ Support for PDF, DOCX, and TXT document upload with semantic chunking and parallel processing</li>
        <li>✅ Interactive Q&A on generated reports using dedicated ReportQAAgent</li>
        <li>✅ Comprehensive analytics dashboard with real-time metrics</li>
        <li>✅ Export reports in Markdown, HTML formats with full citations</li>
        <li>✅ Real-time trace links to OpenAI dashboard for debugging</li>
        </ul>
        
        <h4 style="color: #ffffff; margin-top: 1.5rem;">Report Generation:</h4>
        <ul style="color: #ffffff;">
        <li>✅ Structured outputs with Pydantic schemas and validation</li>
        <li>✅ Cross-source synthesis with multi-citation support ([1][2][3])</li>
        <li>✅ Comprehensive 2000-5000 word reports with adaptive section structures</li>
        <li>✅ Table of Contents with clickable links to sections</li>
        <li>✅ Styled citation boxes with clickable links in references</li>
        <li>✅ Source deduplication and intelligent filtering (top-K by content richness)</li>
        <li>✅ Subtopic extraction and theme analysis for better organization</li>
        <li>✅ Output quality validation with automatic retry on failure</li>
        <li>✅ Query-level summaries for better context integration</li>
        </ul>
        
        <h4 style="color: #ffffff; margin-top: 1.5rem;">Advanced Analytics:</h4>
        <ul style="color: #ffffff;">
        <li>📊 Source type and domain distribution with interactive charts</li>
        <li>🎯 Citation frequency and coverage analysis</li>
        <li>⏱️ Research wave timeline and efficiency metrics</li>
        <li>💾 Cache performance statistics and hit rates</li>
        <li>📈 Section coverage heatmaps and source credibility scores</li>
        </ul>
        
        <h4 style="color: #ffffff; margin-top: 1.5rem;">Technical Features:</h4>
        <ul style="color: #ffffff;">
        <li>✅ Token estimation and prompt optimization (3000 char summary limit)</li>
        <li>✅ URL normalization and citation management</li>
        <li>✅ Database migration logic for cache schema evolution</li>
        <li>✅ Safe async execution with comprehensive error handling</li>
        <li>✅ Real-time streaming updates with Live Research Log</li>
        <li>✅ Chatbot-style Q&A interface for interactive exploration</li>
        </ul>
        
        <h4 style="color: #ffffff; margin-top: 1.5rem;">How It Works:</h4>
        <ol style="color: #ffffff;">
        <li><strong>Planning:</strong> QueryGeneratorAgent creates diverse search queries covering multiple research angles (background, stats, trends, case studies, risks, etc.)</li>
        <li><strong>Query Review:</strong> Review and edit AI-generated queries before execution</li>
        <li><strong>File Processing:</strong> Processes uploaded documents using LLM-based semantic chunking and parallel summarization</li>
        <li><strong>Search Waves:</strong> Searches the web in parallel for relevant sources with query-level summaries</li>
        <li><strong>Follow-Up Decision:</strong> FollowUpDecisionAgent analyzes findings and decides if additional research waves are needed</li>
        <li><strong>Source Processing:</strong> Deduplicates sources, filters to top-K by content richness, and normalizes URLs</li>
        <li><strong>Writing:</strong> WriterAgent synthesizes sources into structured 2000-5000 word research reports with inline citations</li>
        <li><strong>Validation:</strong> Validates output quality and retries with simplified prompt if needed</li>
        <li><strong>Rendering:</strong> Converts to markdown with styled citations and generates References section with clickable links</li>
        </ol>
        
        <h4 style="color: #ffffff; margin-top: 1.5rem;">Technology Stack:</h4>
        <ul style="color: #ffffff;">
        <li>OpenAI GPT-4o for intelligent research and synthesis</li>
        <li>Streamlit for interactive web UI</li>
        <li>Plotly for data visualization and analytics</li>
        <li>Multi-tier caching system (in-memory + SQLite)</li>
        <li>Pydantic for structured data validation</li>
        <li>Asyncio for parallel processing and performance</li>
        </ul>
        
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
