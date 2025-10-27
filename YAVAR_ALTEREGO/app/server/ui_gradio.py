import gradio as gr

def launch_ui(chat_fn):
    gr.ChatInterface(chat_fn, type="messages").launch()
