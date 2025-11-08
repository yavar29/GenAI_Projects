"""
Hugging Face Spaces entry point for Deep Research Pro.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.ui.gradio_app import create_interface

demo = create_interface()

if __name__ == "__main__":
    demo.launch()

