import gradio as gr
from app.core.personas import persona_manager

def create_persona_interface(chat_fn):
    """Create a Gradio interface with persona switching"""
    
    # Get available personas
    personas = persona_manager.get_available_personas()
    persona_choices = [(f"{p['icon']} {p['display_name']}", p['name']) for p in personas]
    
    # Global assistant reference (will be set by main.py)
    assistant_ref = [None]
    
    def chat_with_persona(message, history, persona):
        """Chat function that handles persona switching"""
        if assistant_ref[0] is not None:
            # Switch persona if different from current
            if persona != assistant_ref[0].current_persona:
                assistant_ref[0].switch_persona(persona)
            
            # Get current persona info for context
            persona_info = assistant_ref[0].get_current_persona_info()
            
            # Add persona context to message if needed
            if persona != "professional":
                message = f"[{persona_info['name']} Mode] {message}"
            
            # Use the history as-is since it's already in the correct format
            response = chat_fn(message, history)
            return response
        else:
            return "Assistant not initialized"
    
    def get_persona_description(persona):
        """Get description for selected persona"""
        if persona:
            persona_info = persona_manager.get_persona(persona)
            return f"**{persona_info['name']}**: {persona_info['description']}"
        return "Select a persona to see its description"
    
    # Create the interface
    with gr.Blocks(title="AI Alter Ego - Persona Switching", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🤖 AI Alter Ego - Intelligent Personal Assistant")
        gr.Markdown("Choose your interaction style and start chatting!")
        
        with gr.Row():
            with gr.Column(scale=1):
                # Persona selection
                persona_dropdown = gr.Dropdown(
                    choices=persona_choices,
                    value="professional",
                    label="🎭 Select Persona",
                    info="Choose how the AI should respond"
                )
                
                # Persona description
                persona_description = gr.Markdown(
                    value=get_persona_description("professional"),
                    label="Persona Description"
                )
                
                # Update description when persona changes
                persona_dropdown.change(
                    fn=get_persona_description,
                    inputs=[persona_dropdown],
                    outputs=[persona_description]
                )
                
                # Stats and info
                gr.Markdown("""
                ### 📊 Features
                - **FAISS Vector Store**: Persistent memory with fast similarity search
                - **Multi-Persona Support**: Switch between different interaction styles
                - **RAG Pipeline**: Retrieval-augmented generation for accurate responses
                - **Pushover Notifications**: Real-time alerts for important interactions
                """)
                
            with gr.Column(scale=3):
                # Chat interface
                chatbot = gr.Chatbot(
                    height=500,
                    label="Chat with AI Alter Ego",
                    show_label=True,
                    type="messages"
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Ask me anything about my background, skills, or projects...",
                        label="Message",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                
                # Clear button
                clear_btn = gr.Button("Clear Chat", variant="secondary")
        
        # Event handlers
        def user_message(message, history, persona):
            if message.strip():
                return "", history + [{"role": "user", "content": message}]
            return message, history
        
        def bot_response(history, persona):
            if history and history[-1]["role"] == "user":
                user_msg = history[-1]["content"]
                bot_msg = chat_with_persona(user_msg, history[:-1], persona)
                history.append({"role": "assistant", "content": bot_msg})
            return history
        
        # Handle send button and enter key
        send_btn.click(
            fn=user_message,
            inputs=[msg, chatbot, persona_dropdown],
            outputs=[msg, chatbot]
        ).then(
            fn=bot_response,
            inputs=[chatbot, persona_dropdown],
            outputs=[chatbot]
        )
        
        msg.submit(
            fn=user_message,
            inputs=[msg, chatbot, persona_dropdown],
            outputs=[msg, chatbot]
        ).then(
            fn=bot_response,
            inputs=[chatbot, persona_dropdown],
            outputs=[chatbot]
        )
        
        # Clear chat
        clear_btn.click(
            fn=lambda: [],
            outputs=[chatbot]
        )
        
        # Persona change handler
        def on_persona_change(persona):
            if assistant_ref[0] is not None:
                assistant_ref[0].switch_persona(persona)
            return f"Switched to {persona} persona"
        
        persona_dropdown.change(
            fn=on_persona_change,
            inputs=[persona_dropdown],
            outputs=[]
        )
    
    # Store assistant reference for the interface
    interface.assistant_ref = assistant_ref
    
    return interface

def launch_ui(chat_fn, assistant_instance=None):
    """Launch the enhanced UI with persona switching"""
    interface = create_persona_interface(chat_fn)
    
    # Set assistant reference if provided
    if assistant_instance is not None:
        interface.assistant_ref[0] = assistant_instance
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True
    )