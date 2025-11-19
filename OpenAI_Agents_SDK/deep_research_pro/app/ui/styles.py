"""
CSS styles for Gradio UI.
Separated from gradio_app.py for better code organization.
"""

def get_css_template() -> str:
    """
    Returns the CSS template with placeholder for background image.
    The placeholder '__BG_IMAGE_URL__' should be replaced with actual base64 image URL.
    """
    return """
        /* Background Image */
        body {
            background-image: url('__BG_IMAGE_URL__') !important;
            background-size: cover !important;
            background-position: center center !important;
            background-attachment: fixed !important;
            background-repeat: no-repeat !important;
            min-height: 100vh !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* Ensure background is visible */
        #root {
            background: transparent !important;
        }
        
        /* Overlay for readability - one shade lighter than header */
        .gradio-container {
            background: rgba(60, 60, 70, 0.95) !important;
            backdrop-filter: blur(10px) !important;
            border-radius: 20px !important;
            padding: 2rem !important;
            margin: 2rem auto !important;
            max-width: 1600px !important;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(80, 80, 90, 0.3);
        }
        
        /* Hero Header with dark background and image */
        .gradio-container > div:first-child {
            background: linear-gradient(135deg, #2d2d35 0%, #1f1f28 100%) !important;
            padding: 4rem 3.5rem !important;
            border-radius: 16px !important;
            margin: -2rem -2rem 2rem -2rem !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5) !important;
            display: flex !important;
            align-items: center !important;
            gap: 4rem !important;
            flex-wrap: wrap !important;
            width: calc(100% + 4rem) !important;
            max-width: none !important;
        }
        
        /* Header image container */
        .header-image-container {
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .header-image-container img {
            max-width: 400px !important;
            max-height: 400px !important;
            width: auto;
            height: auto;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            object-fit: contain;
        }
        
        /* Header text container */
        .header-text-container {
            flex: 1;
            min-width: 400px;
        }
        
        .gradio-container > div:first-child h1 {
            color: #ffffff !important;
            font-size: 5rem !important;
            font-weight: 900 !important;
            margin: 0 !important;
            letter-spacing: -0.03em !important;
            line-height: 1.1 !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
            text-align: left !important;
        }
        
        .gradio-container > div:first-child h3 {
            color: rgba(255, 255, 255, 0.9) !important;
            font-size: 2.25rem !important;
            font-weight: 500 !important;
            margin: 1.5rem 0 0 0 !important;
            text-align: left !important;
        }
        
        .gradio-container > div:first-child p {
            color: rgba(255, 255, 255, 0.85) !important;
            font-size: 1.4rem !important;
            margin-top: 2rem !important;
            text-align: left !important;
            line-height: 1.7 !important;
        }
        
        /* Live Log */
        #live-log {
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 12px;
            background: #f9fafb !important;
            color: #111827 !important;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
            font-size: 0.9rem;
            line-height: 1.5;
        }
        
        #live-log * {
            color: #111827 !important;
        }
        
        /* Report Display - Professional Document Box */
        .report-markdown {
            background: white !important;
            border: 2px solid rgba(249, 115, 22, 0.2) !important;
            border-radius: 16px !important;
            padding: 3rem 2.5rem !important;
            margin: 1.5rem 0 !important;
            box-shadow: 0 8px 24px rgba(249, 115, 22, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08) !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Inter', 'Helvetica Neue', Arial, sans-serif !important;
            line-height: 1.8 !important;
            color: #1e293b !important;
            max-width: 100% !important;
        }
        
        /* Report Typography */
        .report-markdown h1 {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            color: #1e293b !important;
            margin-top: 0 !important;
            margin-bottom: 1.5rem !important;
            padding-bottom: 1rem !important;
            border-bottom: 3px solid #f97316 !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
            letter-spacing: -0.02em !important;
        }
        
        .report-markdown h2 {
            font-size: 1.875rem !important;
            font-weight: 600 !important;
            color: #1e293b !important;
            margin-top: 2.5rem !important;
            margin-bottom: 1.25rem !important;
            padding-bottom: 0.75rem !important;
            border-bottom: 2px solid rgba(249, 115, 22, 0.2) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }
        
        .report-markdown h3 {
            font-size: 1.5rem !important;
            font-weight: 600 !important;
            color: #334155 !important;
            margin-top: 2rem !important;
            margin-bottom: 1rem !important;
        }
        
        .report-markdown p {
            font-size: 1.0625rem !important;
            line-height: 1.85 !important;
            color: #334155 !important;
            margin-bottom: 1.25rem !important;
            text-align: justify !important;
        }
        
        .report-markdown ul, .report-markdown ol {
            margin: 1.25rem 0 !important;
            padding-left: 2rem !important;
            color: #334155 !important;
        }
        
        .report-markdown li {
            margin-bottom: 0.75rem !important;
            line-height: 1.75 !important;
            color: #334155 !important;
        }
        
        .report-markdown strong {
            font-weight: 600 !important;
            color: #1e293b !important;
        }
        
        .report-markdown em {
            font-style: italic !important;
            color: #475569 !important;
        }
        
        /* Table of Contents Styling */
        .report-markdown h2 + ul {
            background: #fff7ed !important;
            border: 1px solid rgba(249, 115, 22, 0.15) !important;
            border-radius: 8px !important;
            padding: 1.5rem !important;
            margin: 1.5rem 0 !important;
        }
        
        .report-markdown ul li a[href^="#"] {
            color: #ea580c !important;
            text-decoration: none !important;
            font-weight: 500 !important;
            transition: color 0.2s ease !important;
        }
        
        .report-markdown ul li a[href^="#"]:hover {
            color: #f97316 !important;
            text-decoration: underline !important;
        }
        
        /* Citation Links - Plain text style, no background, but clickable */
        .report-markdown a[href] {
            display: inline;
            padding: 0;
            margin: 0;
            background-color: transparent !important;
            border: none !important;
            border-radius: 0;
            color: inherit !important;
            text-decoration: none;
            font-size: inherit;
            font-weight: inherit;
            transition: color 0.2s ease;
        }
        
        .report-markdown a[href]:hover {
            background-color: transparent !important;
            border: none !important;
            color: #ea580c !important;
            text-decoration: underline;
            transform: none;
        }
        
        /* Only style non-citation links (like in references) */
        .report-markdown p[id^="ref-"] a[href] {
            color: #ea580c !important;
            text-decoration: underline;
        }
        
        .report-markdown p[id^="ref-"] a[href]:hover {
            color: #f97316 !important;
        }
        
        /* Code blocks */
        .report-markdown code {
            background: #fff7ed !important;
            color: #ea580c !important;
            padding: 0.2rem 0.5rem !important;
            border-radius: 4px !important;
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace !important;
            font-size: 0.9em !important;
            border: 1px solid rgba(249, 115, 22, 0.2) !important;
        }
        
        .report-markdown pre {
            background: #fff7ed !important;
            border: 1px solid rgba(249, 115, 22, 0.2) !important;
            border-radius: 8px !important;
            padding: 1.25rem !important;
            overflow-x: auto !important;
            margin: 1.5rem 0 !important;
        }
        
        .report-markdown pre code {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
        }
        
        /* Tables */
        .report-markdown table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin: 1.5rem 0 !important;
            background: white !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important;
        }
        
        .report-markdown th {
            background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important;
            color: white !important;
            padding: 1rem !important;
            text-align: left !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
        }
        
        .report-markdown td {
            padding: 0.875rem 1rem !important;
            border-bottom: 1px solid rgba(249, 115, 22, 0.1) !important;
            color: #334155 !important;
        }
        
        .report-markdown tr:hover {
            background: #fff7ed !important;
        }
        
        /* Blockquotes */
        .report-markdown blockquote {
            border-left: 4px solid #f97316 !important;
            padding-left: 1.5rem !important;
            margin: 1.5rem 0 !important;
            color: #475569 !important;
            font-style: italic !important;
            background: #fff7ed !important;
            padding: 1rem 1.5rem !important;
            border-radius: 0 8px 8px 0 !important;
        }
        
        /* Horizontal rules */
        .report-markdown hr {
            border: none !important;
            border-top: 2px solid rgba(249, 115, 22, 0.2) !important;
            margin: 2.5rem 0 !important;
        }
        
        /* References dropdown section */
        .report-markdown details {
            margin: 2rem 0 !important;
            padding: 1rem 0 !important;
            border-top: 2px solid rgba(249, 115, 22, 0.2) !important;
        }
        
        .report-markdown details summary {
            cursor: pointer;
            padding: 0.75rem 0 !important;
            font-weight: 600;
            color: #1e293b !important;
            user-select: none;
            list-style: none;
        }
        
        .report-markdown details summary::-webkit-details-marker {
            display: none;
        }
        
        .report-markdown details summary::before {
            content: "▶ ";
            display: inline-block;
            margin-right: 0.5rem;
            transition: transform 0.2s ease;
            color: #f97316;
        }
        
        .report-markdown details[open] summary::before {
            transform: rotate(90deg);
        }
        
        .report-markdown details summary h2 {
            display: inline !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        .report-markdown details p[id^="ref-"] {
            padding: 0.75rem 0 !important;
            border-bottom: 1px solid rgba(249, 115, 22, 0.1) !important;
            margin: 0 !important;
        }
        
        .report-markdown details p[id^="ref-"]:last-of-type {
            border-bottom: none !important;
        }
        
        /* Plan section */
        .plan-section {
            padding: 1.5rem !important;
            background: rgba(255, 255, 255, 0.8) !important;
            border-radius: 12px !important;
            backdrop-filter: blur(5px) !important;
        }
        
        .plan-section .dataframe,
        .plan-section .gr-df {
            margin: 1rem 0 !important;
            padding: 0.5rem !important;
        }
        
        /* Cards and sections */
        .gr-group,
        .gr-accordion,
        .gr-tab {
            background: rgba(255, 255, 255, 0.9) !important;
            backdrop-filter: blur(5px) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            margin: 1rem 0 !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Input fields */
        .gr-textbox,
        .gr-textarea,
        .gr-slider {
            background: rgba(255, 255, 255, 0.95) !important;
            border: 2px solid rgba(249, 115, 22, 0.3) !important;
            border-radius: 8px !important;
            color: #1e293b !important;
        }
        
        .gr-textbox:focus,
        .gr-textarea:focus {
            border-color: #f97316 !important;
            box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.2) !important;
        }
        
        /* Labels and text inside container */
        .gradio-container label,
        .gradio-container .gr-label,
        .gradio-container .gr-markdown,
        .gradio-container p:not(.report-markdown p),
        .gradio-container span:not(.report-markdown span) {
            color: rgba(255, 255, 255, 0.9) !important;
        }
        
        /* Ensure input text is dark */
        .gr-textbox input,
        .gr-textarea textarea {
            color: #1e293b !important;
        }
        
        /* Buttons */
        .gr-button {
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        }
        
        .gr-button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3) !important;
        }
        
        /* Tabs */
        .gr-tabs {
            background: rgba(255, 255, 255, 0.95) !important;
            border-radius: 12px !important;
            padding: 1rem !important;
            margin: 1rem 0 !important;
        }
        
        /* Live log with better visibility */
        #live-log {
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(5px) !important;
            border: 2px solid rgba(249, 115, 22, 0.2) !important;
        }
        
        /* File upload area */
        .gr-file {
            background: rgba(255, 255, 255, 0.9) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
        }
    """


def get_css(bg_image_url: str = "") -> str:
    """
    Returns the CSS with background image URL replaced.
    
    Args:
        bg_image_url: Base64 encoded image URL or empty string
        
    Returns:
        CSS string ready to use in Gradio
    """
    return get_css_template().replace('__BG_IMAGE_URL__', bg_image_url)

