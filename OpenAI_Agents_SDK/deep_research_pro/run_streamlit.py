"""
Simple launcher for Streamlit app.
Usage: 
  - With uv: uv run streamlit run streamlit_app.py
  - Or: python run_streamlit.py
"""

import subprocess
import sys
import os

if __name__ == "__main__":
    # Check if uv is available
    uv_available = os.system("which uv > /dev/null 2>&1") == 0
    
    if uv_available:
        # Use uv run to ensure correct environment
        subprocess.run(["uv", "run", "streamlit", "run", "streamlit_app.py"])
    else:
        # Fallback to direct streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"])

