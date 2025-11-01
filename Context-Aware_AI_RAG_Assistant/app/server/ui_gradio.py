import gradio as gr
from app.core.personas import persona_manager
import os

# Photo URL/path - Set this to your photo URL or local file path
# Examples:
# PHOTO_URL = "https://example.com/path/to/your/photo.jpg"  # For URL
# PHOTO_URL = "me/photo.jpg"  # For local file in project directory
PHOTO_URL = "me/personal_photo6.png"  # Photo for header and chatbot avatar (or None to hide)
SIDEBAR_PHOTO_URL = "me/personal_photo.jpg"  # Photo for sidebar (or None to hide, uses PHOTO_URL if not set)

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
        title="Context-Aware AI RAG Assistant",
        theme=theme,
        css="""
        * {
            font-family: 'Poppins', system-ui, sans-serif !important;
        }
        body {
            overflow: auto;
        }
        .gradio-container {
            max-width: 1400px !important;
            margin: 0 auto !important;
            padding: 16px 24px !important;
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
            padding: 18px 24px;
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
            overflow: visible;
            display: block;
            min-height: 0;
            padding: 0 0;
            box-sizing: border-box;
        }
        .sidebar-column { display:none; }
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
        /* Career gallery */
        .gallery { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-top:18px; }
        .gallery .card { border-radius:16px; overflow:hidden; box-shadow:0 16px 32px rgba(0,0,0,0.12); border:1px solid rgba(255,255,255,0.25); background:rgba(255,255,255,0.12); }
        .gallery img { width:100%; height:220px; object-fit:cover; display:block; }
        .section-title { margin:28px 0 10px; font-weight:800; font-size:1.25rem; color:#1f2937; }
        .chat-section { margin-top:28px; padding:0; }
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
        
        /* Persona selector - purple background matching bio page */
        .persona-selector-container {
            background: radial-gradient(1200px 600px at 10% 10%, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.02) 40%),
                        linear-gradient(135deg, #6b7bff 0%, #9b64e8 50%, #e48bf8 100%) !important;
            border-radius: 22px !important;
            padding: 24px !important;
            margin-bottom: 20px !important;
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
        /* New hero + stat cards (inspired, not identical) */
        .hero {
            background: linear-gradient(135deg, #5b76ea 0%, #8a63e6 100%);
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            color: #fff;
        }
        .hero-content {
            display: flex;
            gap: 28px;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        .hero-left {
            display: flex;
            align-items: center;
            gap: 18px;
            min-width: 280px;
        }
        .hero .profile-photo-wrapper {
            width: 84px;
            height: 84px;
        }
        .hero h2 {
            margin: 0;
            font-size: 1.6rem;
            font-weight: 800;
            letter-spacing: 0.2px;
        }
        .hero p {
            margin: 4px 0 0 0;
            font-size: 0.95rem;
            opacity: 0.95;
        }
        .stat-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            width: 100%;
            margin-top: 14px;
        }
        .stat-card {
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.25);
            border-radius: 12px;
            padding: 12px 14px;
            color: #fff;
            backdrop-filter: blur(6px);
        }
        .stat-card h4 { margin: 0 0 6px 0; font-size: 0.95rem; font-weight: 700; }
        .stat-card p { margin: 0; font-size: 0.9rem; opacity: 0.95; }
        .stat-card p.tag { margin: 4px 0 8px 0; font-size: 0.75rem; opacity: 0.8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
        /* Features section (separate from bio) */

        .features-section {
            background: radial-gradient(1200px 600px at 10% 10%, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.02) 40%),
                        linear-gradient(135deg, #6b7bff 0%, #9b64e8 50%, #e48bf8 100%);
            border-radius: 22px;
            padding: 32px 32px 26px 32px;
            box-shadow: 0 36px 72px rgba(0,0,0,0.14);
            margin-top: 24px;
            border: 1px solid rgba(255,255,255,0.18);
        }

        .features-section .stat-cards {
            margin-top: 0;
        }
        
        .features-section .stat-card {
            background: rgba(225, 216, 238, 0.95) !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            color: #1f2937 !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15) !important;
        }
        
        .features-section .stat-card h4 {
            color: #111827 !important;
        }
        
        .features-section .stat-card p.tag {
            color: #4b5563 !important;
        }
        
        .features-section .stat-card p {
            color: #374151 !important;
        }
        
        /* Mega hero (two-column) */
        .mega-hero {
            background: radial-gradient(1200px 600px at 10% 10%, rgba(255,255,255,0.14) 0%, rgba(255,255,255,0.02) 40%),
                        linear-gradient(135deg, #6b7bff 0%, #9b64e8 50%, #e48bf8 100%);
            border-radius: 22px;
            /* more height + more breathing space at bottom */
            padding: 60px 42px 50px 42px;
            min-height: 360px;
            box-shadow: 0 36px 72px rgba(0,0,0,0.14);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.22);
        }

        .mega-hero .content {
            display: grid;
            grid-template-columns: 1.15fr 0.85fr;
            gap: 32px; /* slightly more gap */
            align-items: center;
        }

        .mega-hero .left .avatar {
            width: 170px;
            height: 170px;
            border-radius: 50%;
            border: 6px solid rgba(255,255,255,0.95);
            overflow: hidden;
            box-shadow: 0 24px 48px rgba(0,0,0,0.35);
            background: #fff;
        }

        .mega-hero .left h1 {
            margin: 0 0 14px 0;
            font-size: 2.6rem;
            line-height: 1.08;
            font-weight: 900;
            letter-spacing: 0.3px;
            text-shadow: 0 4px 18px rgba(0,0,0,0.28);
        }
        .mega-hero .left p {
            margin: 0;
            font-size: 1.08rem;
            line-height: 1.75;
            opacity: 0.97;
            font-weight: 300;
            max-width: 640px;
        }
        .mega-hero .right .glass-card {
            border-radius: 20px;
            background: rgba(255,255,255,0.16);
            border: 1px solid rgba(255,255,255,0.35);
            padding: 18px;
            box-shadow: 0 30px 60px rgba(0,0,0,0.28);
            backdrop-filter: blur(10px);
        }
        .mega-hero .right .glass-card img {
            width: 100%; height: 320px; object-fit: cover; border-radius: 14px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.35);
            display: block;
        }
        .mega-hero .caption {
            color: #fff; text-align: left; margin-top: 14px;
        }
        .mega-hero .caption h4 { margin: 0 0 6px; font-size: 1.05rem; font-weight: 800; }
        .mega-hero .caption p { margin: 0; font-size: 0.95rem; opacity: 0.95; }
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
                                <h1>🤖 Context-Aware AI RAG Assistant</h1>
                                <p>Intelligent Personal Assistant • Choose your interaction style and start chatting!</p>
                            </div>
                        </div>
                    </div>
                """
        
        if not photo_html:
            photo_html = """
                <div class="header">
                    <h1>🤖 Context-Aware AI RAG Assistant</h1>
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
        
        # Top header removed per request
        
        # Helper function to convert image to base64
        def img_to_base64(img_path):
            from pathlib import Path
            import base64
            try:
                abs_path = Path(img_path).resolve()
                if abs_path.exists() and abs_path.is_file():
                    with open(abs_path, 'rb') as f:
                        img_data = base64.b64encode(f.read()).decode()
                        ext = abs_path.suffix.lower().replace('.', '')
                        return f"data:image/{ext};base64,{img_data}"
            except Exception:
                pass
            return None
        
       
        avatar_left_src = img_to_base64("me/personal_photo2.png")
        right_hero_src = img_to_base64("me/personal_photo11.jpg")
        gallery_photos = [
            img_to_base64("me/yk.jpg"),
            img_to_base64("me/image.png"),
            img_to_base64("me/personal_photo5.png")
        ]
        gallery_photos = [p for p in gallery_photos if p]  # Remove any None values
        
        # Lightweight hero + stat cards (non-intrusive, no logic changes)
        with gr.Row():
            with gr.Column():
                # Build avatar HTML safely
                avatar_img_tag = f'<img src="{avatar_left_src}" alt="Profile" style="width:100%;height:100%;object-fit:cover;">' if avatar_left_src else '🤖'
                right_img_tag = f'<img src="{right_hero_src}" alt="Profile" style="width:100%;height:320px;object-fit:cover;">' if right_hero_src else ''
                
                hero_html = f"""
                <div class="mega-hero">
                  <div class="content">
                    <div class="left">
                      <div class="avatar">{avatar_img_tag}</div>
                      <div>
                        <h1>Yavar Khan</h1>
                        <p>Master's in Computer Science - AI/ML Track at SUNY Buffalo with a focus on Generative AI and Agentic Systems. Former Software Engineer exploring RAG, multi-agent orchestration, and Model Context Protocol for adaptive, data-driven AI systems.</p>
                      </div>
                    </div>
                    <div class="right">
                      <div class="glass-card">
                        {right_img_tag}
                      </div>
                    </div>
                  </div>
                </div>
                """
                gr.HTML(hero_html)
        
        # Feature cards section (separate from bio)
        with gr.Row():
            with gr.Column():
                features_html = """
                <div class="features-section">
                  <div class="stat-cards">
                    <div class="stat-card glass-card"><h4>Knowledge Engine</h4><p class="tag">FAISS + KB Orchestration</p><p>Context-aware semantic retrieval over curated Knowledge Base.</p></div>
                    <div class="stat-card glass-card"><h4>Adaptive Personas</h4><p class="tag">Dynamic Persona Switching</p><p>Professional, Mentor, Technical & Casual modes with tone adaptation.</p></div>
                    <div class="stat-card glass-card"><h4>Conversational Intelligence</h4><p class="tag">Contextual Reasoning Engine</p><p>Logical reasoning + contextual inference to handle unseen questions.</p></div>
                  </div>
                </div>
                """
                gr.HTML(features_html)

        with gr.Row(elem_classes=["content-row"]):
            with gr.Column():
                # Photo gallery (3 photos in bottom row)
                if gallery_photos:
                    _cards = "".join([f'<div class="card"><img src="{p}" alt="photo" style="width:100%;height:220px;object-fit:cover;"></div>' for p in gallery_photos[:3]])
                    gr.HTML(f"<div class='gallery'>{_cards}</div>")

                # Persona selector above chatbot
                with gr.Row(elem_classes=["persona-selector-container"]):
                    persona_dropdown = gr.Dropdown(
                        choices=persona_choices,
                        value="professional",
                        label="🎭 Select Persona",
                        info="Choose how the AI should respond"
                    )
                
                with gr.Row():
                    persona_description = gr.Markdown(
                        value=get_persona_description("professional"),
                        label="Persona Description"
                    )
                
                persona_dropdown.change(
                    fn=get_persona_description,
                    inputs=[persona_dropdown],
                    outputs=[persona_description]
                )
                
                gr.Markdown("### 💬 Start a conversation")
                # Full-width chatbot
                chatbot = gr.Chatbot(
                    height=520,
                    label="Chat with Yavar",
                    show_label=True,
                    type="messages",
                    avatar_images=(None, avatar_image),
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

                
        # Example question handlers removed (no example buttons in new layout)
        
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
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        share=False,
        show_error=True
    )