#!/usr/bin/env python3
"""
Run the Streamlit UI for Deep Research Pro.

Configuration options via environment variables:
- STREAMLIT_SERVER_PORT: Server port (default: 8501)
- STREAMLIT_SERVER_ADDRESS: Server address (default: "0.0.0.0")
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Find .env relative to current working directory
load_dotenv(find_dotenv(usecwd=True), override=True)

# Add the project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    # Configuration from environment variables
    port = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    address = os.getenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
    
    print(f"🚀 Starting Streamlit server on {address}:{port}")
    print(f"📄 App file: streamlit_app.py")
    
    # Run streamlit
    os.system(f"streamlit run streamlit_app.py --server.port {port} --server.address {address}")

