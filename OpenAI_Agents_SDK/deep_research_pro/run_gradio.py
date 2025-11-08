#!/usr/bin/env python3
"""
Run the Gradio UI for Deep Research Pro.

Configuration options via environment variables:
- GRADIO_SERVER_NAME: Server hostname (default: "0.0.0.0" for all interfaces)
- GRADIO_SERVER_PORT: Server port (default: 7860)
- GRADIO_SHARE: Enable public sharing (default: False, set to "true" to enable)
- GRADIO_AUTH: Authentication in format "username:password" (optional)
"""
# run_gradio.py (very top)
import os
from dotenv import load_dotenv, find_dotenv

# Find .env relative to current working directory, and override empty/unset env
load_dotenv(find_dotenv(usecwd=True), override=True)

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.ui.gradio_app import create_interface

if __name__ == "__main__":
    # Configuration from environment variables
    server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    share = os.getenv("GRADIO_SHARE", "false").lower() == "true"
    auth = os.getenv("GRADIO_AUTH")  # Format: "username:password"
    
    # Parse authentication if provided
    auth_tuple = None
    if auth:
        if ":" in auth:
            username, password = auth.split(":", 1)
            auth_tuple = (username, password)
        else:
            print("Warning: GRADIO_AUTH should be in format 'username:password'")
    
    demo = create_interface()
    
    launch_kwargs = {
        "server_name": server_name,
        "server_port": server_port,
        "share": share,
    }
    
    if auth_tuple:
        launch_kwargs["auth"] = auth_tuple
    
    print(f"🚀 Starting Gradio server on {server_name}:{server_port}")
    if share:
        print("🌐 Public sharing enabled - you'll get a public URL")
    if auth_tuple:
        print(f"🔐 Authentication enabled for user: {auth_tuple[0]}")
    
    # Enable queue for streaming robustness
    demo.queue().launch(**launch_kwargs)

