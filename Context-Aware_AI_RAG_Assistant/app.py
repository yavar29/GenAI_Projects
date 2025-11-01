# app.py
from main import build_kb_store, load_me
from app.tools import kb_search
from app.agents.assistant import Assistant
from app.config.settings import OPENAI_MODEL
from app.server.ui_gradio import launch_ui

# 1) build / load vector store
store = build_kb_store()
kb_search.KB_STORE = store

# 2) load personal data
name, summary_text, linkedin_text = load_me()

# 3) create assistant + launch Gradio
assistant = Assistant(
    name=name,
    summary_text=summary_text,
    linkedin_text=linkedin_text,
    model=OPENAI_MODEL,
)

# HF expects Gradio to start on import
launch_ui(assistant.chat, assistant_instance=assistant)
