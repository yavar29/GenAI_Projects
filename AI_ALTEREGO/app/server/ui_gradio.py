import gradio as gr
from app.core.personas import persona_manager
import os

# Photo URL/path - Set this to your photo URL or local file path
# Examples:
# PHOTO_URL = "https://example.com/path/to/your/photo.jpg"  # For URL
# PHOTO_URL = "me/photo.jpg"  # For local file in project directory
PHOTO_URL = "me/personal_photo.jpg"  # Photo for header and chatbot avatar (or None to hide)
SIDEBAR_PHOTO_URL = "me/personal_photo2.png"  # Photo for sidebar (or None to hide, uses PHOTO_URL if not set)

def create_persona_interface(chat_fn, photo_url=None, sidebar_photo_url=None):
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
    
    # Create the interface with modern theme
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="gray",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Poppins"), "system-ui", "sans-serif"],
    )
    
    with gr.Blocks(
        title="AI Alter Ego - Intelligent Personal Assistant",
        theme=theme,
        css="""
        * {
            font-family: 'Poppins', system-ui, sans-serif !important;
        }
        body {
            overflow: auto;
        }
        .gradio-container {
            max-width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            min-height: 100vh !important;
            overflow: auto !important;
        }
        /* Allow the root block to grow naturally so users can scroll if needed */
        #component-0 {
            height: auto !important;
            overflow: visible !important;
        }
        .main-container {
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .header {
            text-align: center;
            padding: 15px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 0;
            margin: 0;
            position: relative;
            overflow: hidden;
            flex-shrink: 0;
            box-sizing: border-box;
        }
        .header h1 {
            color: white;
            margin: 0;
            font-size: 1.8em;
            font-weight: 600;
        }
        .header p {
            color: rgba(255,255,255,0.9);
            margin: 5px 0 0 0;
            font-size: 0.9em;
        }
        .sidebar-photo {
            width: 180px;
            height: 180px;
            border-radius: 8px; /* square with slight rounding */
            border: 4px solid #667eea;
            overflow: hidden;
            margin: 0 auto 15px auto;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            background: white;
        }
        .sidebar-photo img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .header-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
            justify-content: center;
        }
        .header h1 {
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header p {
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
        .profile-photo-wrapper {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: 4px solid white;
            overflow: hidden;
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
            background: white;
            flex-shrink: 0;
        }
        .content-row {
            flex: 1;
            overflow: hidden;
            display: flex;
            min-height: 0;
            padding: 0 24px;
            box-sizing: border-box;
        }
        .sidebar-column {
            overflow-y: auto;
            max-height: calc(100vh - 150px);
            padding-right: 10px;
        }
        .chat-column {
            display: flex;
            flex-direction: column;
            min-height: 0;
            overflow: visible;
        }
        .chat-column .chatbot {
            flex: 1;
            min-height: 0;
            max-height: none;
            position: relative !important;
            overflow-y: auto !important;
        }
        /* Make chatbot label sticky - targets all possible label selectors */
        .chat-column .chatbot label,
        .chat-column .chatbot > div > label,
        .chat-column .chatbot > label,
        .chat-column label[for*="chatbot"],
        .chat-column .form > label,
        .chat-column [class*="chatbot"] label {
            position: sticky !important;
            top: 0 !important;
            z-index: 100 !important;
            background: var(--background-fill-primary, #ffffff) !important;
            padding: 12px 16px !important;
            margin: 0 !important;
            border-bottom: 1px solid var(--border-color-primary, #e0e0e0) !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
            width: 100% !important;
            display: block !important;
        }
        .chat-column > div {
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        /* Input container - relative positioning for embedded button */
        #input-container {
            position: relative !important;
            width: 100% !important;
        }
        /* Input textbox styling - full width, smaller height */
        #input-row {
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            position: relative !important;
        }
        #msg-box {
            width: 100% !important;
            flex: 1 !important;
            position: relative !important;
        }
        #msg-box .wrap {
            width: 100% !important;
            position: relative !important;
        }
        #msg-box textarea {
            width: 100% !important;
            min-height: 60px !important;
            max-height: 120px !important;
            font-size: 16px !important;
            padding: 12px 80px 12px 12px !important;
            resize: vertical !important;
            box-sizing: border-box !important;
        }
        /* Send button embedded inside textbox - moved up */
        #send-btn-embedded {
            position: absolute !important;
            right: 8px !important;
            bottom: 12px !important;
            top: auto !important;
            z-index: 10 !important;
            height: 36px !important;
            padding: 6px 16px !important;
            margin: 0 !important;
            width: auto !important;
        }
        /* Actions row for clear button */
        #actions-row {
            width: 100% !important;
            margin-top: 8px !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
        }
        /* Clear button - smaller size */
        #clear-btn {
            padding: 4px 10px !important;
            font-size: 12px !important;
            height: 28px !important;
            margin: 0 !important;
            width: auto !important;
        }
        .profile-photo-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .header-background-img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: 0.25;
            z-index: 0;
        }
        .header-overlay {
            position: relative;
            z-index: 1;
        }
        .header-text {
            flex: 1;
        }
        .feature-box {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
        }
        .example-question {
            padding: 8px 12px;
            margin: 5px 0;
            background: #e9ecef;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .example-question:hover {
            background: #dee2e6;
            transform: translateX(4px);
        }
        """
    ) as interface:
        
        # Use photo_url parameter or fallback to PHOTO_URL constant
        photo_path = photo_url if photo_url is not None else PHOTO_URL
        sidebar_photo_path = sidebar_photo_url if sidebar_photo_url is not None else SIDEBAR_PHOTO_URL
        # Fallback to main photo if sidebar photo not set
        if not sidebar_photo_path:
            sidebar_photo_path = photo_path
        
        # Prepare header with photo and avatar
        photo_html = ""
        avatar_image = "🤖"  # Default emoji avatar
        photo_src = None
        sidebar_photo_src = None
        
        if photo_path:
            from pathlib import Path
            import base64
            
            # Handle local files by converting to base64
            if not photo_path.startswith(('http://', 'https://')):
                abs_path = Path(photo_path).resolve()
                if abs_path.exists() and abs_path.is_file():
                    # Convert local image to base64
                    try:
                        with open(abs_path, 'rb') as f:
                            img_data = base64.b64encode(f.read()).decode()
                            ext = abs_path.suffix.lower().replace('.', '')
                            photo_src = f"data:image/{ext};base64,{img_data}"
                            # For avatar, use the file path (Gradio handles it better than base64)
                            avatar_image = str(abs_path)
                    except Exception:
                        photo_src = None
                else:
                    photo_src = None
            else:
                photo_src = photo_path  # URL
                avatar_image = photo_path  # Use URL for avatar
            
            if photo_src:
                photo_html = f"""
                    <div class="header header-overlay">
                        <div class="header-content">
                            <div class="profile-photo-wrapper">
                                <img src="{photo_src}" alt="Profile Photo">
                            </div>
                            <div class="header-text">
                                <h1>🤖 AI Alter Ego</h1>
                                <p>Intelligent Personal Assistant • Choose your interaction style and start chatting!</p>
                            </div>
                        </div>
                    </div>
                """
        
        if not photo_html:
            photo_html = """
                <div class="header">
                    <h1>🤖 AI Alter Ego</h1>
                    <p>Intelligent Personal Assistant • Choose your interaction style and start chatting!</p>
                </div>
            """
        
        # Process sidebar photo
        if sidebar_photo_path:
            from pathlib import Path
            import base64
            
            if not sidebar_photo_path.startswith(('http://', 'https://')):
                abs_path = Path(sidebar_photo_path).resolve()
                if abs_path.exists() and abs_path.is_file():
                    try:
                        with open(abs_path, 'rb') as f:
                            img_data = base64.b64encode(f.read()).decode()
                            ext = abs_path.suffix.lower().replace('.', '')
                            sidebar_photo_src = f"data:image/{ext};base64,{img_data}"
                    except Exception:
                        sidebar_photo_src = None
                else:
                    sidebar_photo_src = None
            else:
                sidebar_photo_src = sidebar_photo_path  # URL
        
        with gr.Row():
            with gr.Column():
                gr.HTML(photo_html)
        
        with gr.Row(elem_classes=["content-row"]):
            with gr.Column(scale=1, min_width=280, elem_classes=["sidebar-column"]):
                # Sidebar photo
                if sidebar_photo_src:
                    gr.HTML(f"""
                        <div class="sidebar-photo">
                            <img src="{sidebar_photo_src}" alt="Profile Photo">
                        </div>
                    """)
                
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
                
                # Example questions
                with gr.Group():
                    gr.Markdown("### 💡 Example Questions")
                    example_q1 = gr.Button("What are your career goals?", size="sm", variant="secondary")
                    example_q2 = gr.Button("Tell me about your projects", size="sm", variant="secondary")
                    example_q3 = gr.Button("What's your tech stack?", size="sm", variant="secondary")
                    example_q4 = gr.Button("How are you implemented?", size="sm", variant="secondary")
                
            with gr.Column(scale=3, elem_classes=["chat-column"]):
                # Chat interface
                chatbot = gr.Chatbot(
                    height=400,
                    label="💬 Chat with my AI Companion",
                    show_label=True,
                    type="messages",
                    avatar_images=(None, avatar_image),  # Use user's photo as bot avatar
                    container=True,
                    bubble_full_width=False,
                    show_copy_button=True,
                    scale=1
                )
                
                # Input container with textbox and embedded send button
                with gr.Column(elem_id="input-container"):
                    with gr.Row(elem_id="input-row"):
                        msg = gr.Textbox(
                            placeholder="Ask me anything about my background, skills, projects, or experience...",
                            label="",
                            lines=2,
                            max_lines=200,
                            show_label=False,
                            container=False,
                            elem_id="msg-box"      
                        )
                        send_btn_embedded = gr.Button("Send ➤", variant="primary", elem_id="send-btn-embedded", size="sm", scale=0, min_width=80)
                
                # Clear button below textbox
                with gr.Row(elem_id="actions-row"):
                    clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary", size="sm", elem_id="clear-btn")

                
        # Example question handlers
        def fill_example(question):
            return question
        
        example_q1.click(fn=lambda: "What are your career goals?", outputs=msg)
        example_q2.click(fn=lambda: "Tell me about your projects", outputs=msg)
        example_q3.click(fn=lambda: "What's your technical stack?", outputs=msg)
        example_q4.click(fn=lambda: "How are you implemented?", outputs=msg)
        
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
        
        # Handle send button (embedded) and enter key
        send_btn_embedded.click(
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

def launch_ui(chat_fn, assistant_instance=None, photo_url=None, sidebar_photo_url=None):
    """Launch the enhanced UI with persona switching
    
    Args:
        chat_fn: The chat function from the assistant
        assistant_instance: Optional assistant instance for persona switching
        photo_url: Optional URL/path to profile photo for header/avatar (can be URL or local file path)
        sidebar_photo_url: Optional URL/path to profile photo for sidebar (can be URL or local file path)
    """
    interface = create_persona_interface(chat_fn, photo_url=photo_url, sidebar_photo_url=sidebar_photo_url)
    
    # Set assistant reference if provided
    if assistant_instance is not None:
        interface.assistant_ref[0] = assistant_instance
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True
    )