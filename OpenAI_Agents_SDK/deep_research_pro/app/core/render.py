from __future__ import annotations
from typing import Dict, Optional, Tuple
import re
import markdown as md
from urllib.parse import urlparse, urlunparse

def _slugify(text: str) -> str:
    """Convert section title to anchor-friendly slug."""
    # Lowercase, replace spaces with hyphens, remove special chars
    slug = text.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

def _extract_url_from_markdown(text: str) -> Optional[str]:
    """Extract the first valid URL from markdown link syntax [text](url)."""
    if not text:
        return None
    # Pattern to match markdown links: [text](url)
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, text)
    for _, url in matches:
        url = url.strip()
        # Remove query params that might be added by OpenAI (like ?utm_source=openai)
        if '?' in url:
            url = url.split('?')[0]
        # Check if it's a valid URL
        if url.startswith(('http://', 'https://')):
            return url
    return None

def _extract_domain_from_title_or_provider(title: str = "", provider: str = "") -> Optional[str]:
    """Try to extract domain from title or provider field."""
    # Common domain patterns in titles
    domain_pattern = r'\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.(?:com|org|net|edu|gov|io|co|pk|in|uk|au))\b'
    
    # Try title first
    if title:
        match = re.search(domain_pattern, title.lower())
        if match:
            return match.group(1)
    
    # Try provider
    if provider:
        match = re.search(domain_pattern, provider.lower())
        if match:
            return match.group(1)
    
    return None

def _normalize_url(url: str, title: str = "", provider: str = "") -> tuple[str, str]:
    """
    Normalize and fix malformed URLs.
    
    Returns:
        tuple of (normalized_url, display_url)
    """
    if not url:
        return "#", "(No URL provided)"
    
    # Remove angle brackets
    original_url = url = url.strip('<>').strip()
    
    # Check if it's already a valid URL
    if url.startswith(('http://', 'https://')):
        # Clean up query params that might be added by OpenAI
        if '?' in url and 'utm_source=openai' in url:
            url = url.split('?')[0]
        return url, url
    
    # Check if it's a placeholder like "source1", "source2", etc.
    if re.match(r'^source\d+$', url, re.IGNORECASE):
        return "#", f"(Invalid URL: {original_url})"
    
    # Check if it's just a slug (like "pakistan-launches-diplomatic-campaign-to-counter-indias-aggression")
    # If it looks like a URL slug (has hyphens, no spaces, reasonable length), try to construct URL
    if not url.startswith('/') and '.' not in url and '-' in url and len(url) > 10:
        # Try to extract domain from title or provider
        domain = _extract_domain_from_title_or_provider(title, provider)
        if domain:
            # Reconstruct URL from slug and domain
            normalized = f"https://{domain}/{url}"
            return normalized, normalized
        # Mark as invalid but preserve the slug
        return "#", f"(Invalid URL: {original_url})"
    
    # If relative URL
    if url.startswith('/'):
        return "#", f"(Relative URL: {original_url})"
    
    # If it looks like a domain (has dot and reasonable length), add https
    if '.' in url and len(url) > 4 and not url.startswith('<'):
        normalized = f"https://{url}"
        return normalized, normalized
    
    # Otherwise mark as invalid
    return "#", f"(Invalid URL: {original_url})"

def _extract_main_heading_and_clean_summary(summary: str) -> Tuple[Optional[str], str]:
    """Extract leading markdown heading from summary and return cleaned summary."""
    if not summary:
        return None, ""
    lines = summary.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            # remove heading line
            lines.pop(idx)
            while idx < len(lines) and not lines[idx].strip():
                lines.pop(idx)
            cleaned = "\n".join(lines).strip()
            return heading, cleaned
    return None, summary.strip()

def _clean_heading_text(text: str) -> str:
    """Remove stray markdown markers (#) or numbering prefixes from headings."""
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = cleaned.lstrip("#").strip()
    cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
    return cleaned

def render_markdown(report, source_index: Optional[Dict[int, any]] = None) -> str:  # type: ignore
    """
    Render ResearchReport to markdown.
    
    Args:
        report: ResearchReport object
        source_index: Optional dict mapping numeric ID -> SourceItem (for deterministic citations)
    """
    main_heading = (report.topic or "").strip()
    first_section_clean_summary: Optional[str] = None
    if report.sections:
        heading_from_summary, cleaned = _extract_main_heading_and_clean_summary(report.sections[0].summary)
        if heading_from_summary:
            main_heading = heading_from_summary
            first_section_clean_summary = cleaned
    lines = [f"# {main_heading}", ""]

    # Build references programmatically from Source Index using section.citations (IDs)
    if source_index:
        # Use Source Index for deterministic citations
        id_to_source = source_index
        
        # Collect all citation IDs from section.citations
        all_citation_ids = set()
        for sec in report.sections:
            for citation_id in sec.citations:
                if citation_id in id_to_source:
                    all_citation_ids.add(citation_id)
        
        # Build reference map from Source Index (ID -> SourceItem)
        ref_map: Dict[int, any] = {cid: id_to_source[cid] for cid in sorted(all_citation_ids)}
    else:
        # Fallback: If no source_index, can't render references properly
        ref_map: Dict[int, any] = {}

    # Table of Contents
    if report.sections:
        lines.append("## Table of Contents")
        for i, sec in enumerate(report.sections, 1):
            heading_text = _clean_heading_text(sec.title)
            canonical_topic = (report.topic or "").strip().lower()
            if heading_text.lower() == main_heading.lower() or (
                canonical_topic and heading_text.lower() == canonical_topic
            ):
                continue
            slug = _slugify(heading_text)
            lines.append(f"- [{heading_text}](#{slug})")
            
            # Add subsections to TOC if they exist
            if hasattr(sec, 'subsections') and sec.subsections:
                for subsection in sec.subsections:
                    subsection_title = subsection.title
                    subsection_slug = _slugify(subsection_title)
                    lines.append(f"  - [{subsection_title}](#{subsection_slug})")
        lines.append("")

    # Sections with inline citations already in text (no separate Citations line)
    for i, sec in enumerate(report.sections, 1):
        # Create heading - markdown renderers will auto-create anchors from heading text
        # Use section title directly without numbering
        heading_text = _clean_heading_text(sec.title)
        if not heading_text:
            heading_text = f"Section {i}"
        lines.append(f"## {heading_text}")
        
        # Replace inline citations [1], [2] with clickable links
        # Handle both [1] and [1][2] formats, ensuring proper spacing
        summary_text = sec.summary.strip()
        if i == 1 and first_section_clean_summary is not None:
            summary_text = first_section_clean_summary
        if source_index:
            # First, normalize adjacent citations [4][5] to [4] [5] for proper spacing
            summary_text = re.sub(r'\]\[', '] [', summary_text)
            
            # Also handle cases where citations might appear as bare numbers (6 7) and convert to [6] [7]
            # Only wrap numbers that are valid citation IDs and appear in citation-like contexts
            citation_ids = set(id_to_source.keys())
            max_citation_id = max(citation_ids) if citation_ids else 0
            
            def wrap_bare_citation(match):
                num_str = match.group(0)
                try:
                    num = int(num_str)
                    # Only process if it's a valid citation ID and reasonably small (citations are usually < 50)
                    if num in citation_ids and num <= max(50, max_citation_id):
                        # Check if it's already in brackets (avoid double-wrapping)
                        start = match.start()
                        end = match.end()
                        if start > 0 and end < len(summary_text):
                            # Check if already wrapped in brackets
                            if summary_text[start-1] == '[' and summary_text[end] == ']':
                                return num_str  # Already wrapped
                            # Check if it's part of a larger number or word
                            if start > 0 and summary_text[start-1].isdigit():
                                return num_str  # Part of larger number
                            if end < len(summary_text) and summary_text[end].isdigit():
                                return num_str  # Part of larger number
                            
                            # CRITICAL: Don't wrap numbers that are part of product names, versions, or measurements
                            # Check preceding characters (look back up to 20 chars for context)
                            lookback_start = max(0, start - 20)
                            preceding_text = summary_text[lookback_start:start].lower()
                            
                            # Don't wrap if preceded by product name patterns:
                            # - Letters followed by hyphen: "WeatherNext-", "Model-"
                            # - Letters followed by space: "WeatherNext ", "Model "
                            # - Common version/product words: "version", "v", "model", "release"
                            if re.search(r'[a-z]+[-_]\s*$|[a-z]+\s+$|version\s+|v\d+\s*$|model\s+|release\s+', preceding_text):
                                return num_str  # Part of product name or version
                            
                            # Check if followed by measurement units (don't wrap)
                            following_text = summary_text[end:min(len(summary_text), end + 10)].lower()
                            measurement_units = ['days', 'hours', 'minutes', 'seconds', 'years', 'months', 
                                                'degrees', 'percent', '%', 'km', 'miles', 'meters', 'feet',
                                                'kg', 'pounds', 'tons', 'liters', 'gallons']
                            if any(following_text.strip().startswith(unit + ' ') or 
                                   following_text.strip().startswith(unit + ',') or
                                   following_text.strip().startswith(unit + '.') or
                                   following_text.strip().startswith(unit + ';')
                                   for unit in measurement_units):
                                return num_str  # Part of measurement, not citation
                            
                            # Check immediate preceding character
                            if start > 0:
                                prev_char = summary_text[start-1]
                                # Don't wrap if preceded by letter, hyphen, or underscore (product names)
                                if prev_char.isalpha() or prev_char in ['-', '_']:
                                    return num_str  # Part of name/version
                        return f"[{num_str}]"
                except (ValueError, TypeError):
                    pass
                return num_str
            
            # Pattern to match standalone numbers (1-3 digits) that could be citations
            # Match numbers that are: at word boundaries, followed by space, punctuation, or end of string
            # But not followed by another digit (to avoid matching parts of larger numbers)
            # IMPORTANT: Only match numbers that are clearly citations, not part of product names, versions, or measurements
            # Don't match if preceded by: letters, hyphens, underscores (product names like "WeatherNext-2", "Model 3")
            # Don't match if followed by: units like "days", "hours", "degrees", etc.
            summary_text = re.sub(r'(?<![a-zA-Z\-_])\b(\d{1,3})\b(?=\s|[,.;:!?]|$)', wrap_bare_citation, summary_text)
            
            # Find all citation patterns like [1], [2], [10] and convert to clickable links
            def replace_citation(match):
                citation_id_str = match.group(1)
                try:
                    citation_id = int(citation_id_str)
                    if citation_id in id_to_source:
                        source_item = id_to_source[citation_id]
                        url = source_item.url if hasattr(source_item, 'url') else str(source_item)
                        title = source_item.title if hasattr(source_item, 'title') else ""
                        provider = source_item.provider if hasattr(source_item, 'provider') else ""
                        
                        # Normalize URL
                        normalized_url, _ = _normalize_url(url, title, provider)
                        
                        # If URL is invalid, try to extract from summary text (if available)
                        if normalized_url == "#":
                            # Try snippet first
                            if hasattr(source_item, 'snippet'):
                                extracted_url = _extract_url_from_markdown(source_item.snippet or "")
                                if extracted_url:
                                    normalized_url = extracted_url
                            # Try content if snippet didn't work
                            if normalized_url == "#" and hasattr(source_item, 'content'):
                                extracted_url = _extract_url_from_markdown(source_item.content or "")
                                if extracted_url:
                                    normalized_url = extracted_url
                        
                        # If still invalid, link to reference section
                        if normalized_url == "#":
                            normalized_url = f"#ref-{citation_id}"
                        
                        # Simple link without color highlighting
                        return f'<a href="{normalized_url}">[{citation_id_str}]</a>'
                except (ValueError, AttributeError):
                    pass
                return match.group(0)  # Return original if can't parse
            
            summary_text = re.sub(r'\[(\d+)\]', replace_citation, summary_text)
        
        lines.append(summary_text)
        lines.append("")
        
        # Render subsections if they exist
        if hasattr(sec, 'subsections') and sec.subsections:
            for subsection in sec.subsections:
                # Add H3 heading for subsection
                subsection_title = subsection.title
                lines.append(f"### {subsection_title}")
                lines.append("")
                
                # Process subsection content with citations
                subsection_content = subsection.content.strip()
                if source_index:
                    # Normalize adjacent citations
                    subsection_content = re.sub(r'\]\[', '] [', subsection_content)
                    
                    # Wrap bare citations (same logic as for summary)
                    citation_ids = set(id_to_source.keys())
                    max_citation_id = max(citation_ids) if citation_ids else 0
                    
                    def wrap_bare_citation_sub(match):
                        num_str = match.group(0)
                        try:
                            num = int(num_str)
                            if num in citation_ids and num <= max(50, max_citation_id):
                                start = match.start()
                                end = match.end()
                                if start > 0 and end < len(subsection_content):
                                    # Check if already wrapped
                                    if subsection_content[start-1] == '[' and subsection_content[end] == ']':
                                        return num_str
                                    # Check if part of larger number
                                    if start > 0 and subsection_content[start-1].isdigit():
                                        return num_str
                                    if end < len(subsection_content) and subsection_content[end].isdigit():
                                        return num_str
                                    
                                    # CRITICAL: Don't wrap numbers that are part of product names, versions, or measurements
                                    lookback_start = max(0, start - 20)
                                    preceding_text = subsection_content[lookback_start:start].lower()
                                    
                                    if re.search(r'[a-z]+[-_]\s*$|[a-z]+\s+$|version\s+|v\d+\s*$|model\s+|release\s+', preceding_text):
                                        return num_str
                                    
                                    following_text = subsection_content[end:min(len(subsection_content), end + 10)].lower()
                                    measurement_units = ['days', 'hours', 'minutes', 'seconds', 'years', 'months', 
                                                        'degrees', 'percent', '%', 'km', 'miles', 'meters', 'feet',
                                                        'kg', 'pounds', 'tons', 'liters', 'gallons']
                                    if any(following_text.strip().startswith(unit + ' ') or 
                                           following_text.strip().startswith(unit + ',') or
                                           following_text.strip().startswith(unit + '.') or
                                           following_text.strip().startswith(unit + ';')
                                           for unit in measurement_units):
                                        return num_str
                                    
                                    if start > 0:
                                        prev_char = subsection_content[start-1]
                                        if prev_char.isalpha() or prev_char in ['-', '_']:
                                            return num_str
                                return f"[{num_str}]"
                        except (ValueError, TypeError):
                            pass
                        return num_str
                    
                    subsection_content = re.sub(r'(?<![a-zA-Z\-_])\b(\d{1,3})\b(?=\s|[,.;:!?]|$)', wrap_bare_citation_sub, subsection_content)
                    
                    # Replace citations with clickable links (reuse the same function logic)
                    def replace_citation_sub(match):
                        citation_id_str = match.group(1)
                        try:
                            citation_id = int(citation_id_str)
                            if citation_id in id_to_source:
                                source_item = id_to_source[citation_id]
                                url = source_item.url if hasattr(source_item, 'url') else str(source_item)
                                title = source_item.title if hasattr(source_item, 'title') else ""
                                provider = source_item.provider if hasattr(source_item, 'provider') else ""
                                
                                normalized_url, _ = _normalize_url(url, title, provider)
                                
                                if normalized_url == "#":
                                    if hasattr(source_item, 'snippet'):
                                        extracted_url = _extract_url_from_markdown(source_item.snippet or "")
                                        if extracted_url:
                                            normalized_url = extracted_url
                                    if normalized_url == "#" and hasattr(source_item, 'content'):
                                        extracted_url = _extract_url_from_markdown(source_item.content or "")
                                        if extracted_url:
                                            normalized_url = extracted_url
                                
                                if normalized_url == "#":
                                    normalized_url = f"#ref-{citation_id}"
                                
                                return f'<a href="{normalized_url}">[{citation_id_str}]</a>'
                        except (ValueError, AttributeError):
                            pass
                        return match.group(0)
                    
                    subsection_content = re.sub(r'\[(\d+)\]', replace_citation_sub, subsection_content)
                
                lines.append(subsection_content)
                lines.append("")

    # Notes (may include next steps)
    if report.notes:
        lines.append("## Notes")
        for n in report.notes:
            lines.append(f"- {n}")
        lines.append("")

    # References: Build programmatically from Source Index (in dropdown)
    if ref_map:
        lines.append("<details>")
        lines.append("<summary><h2 style='display: inline; margin: 0;'>References</h2></summary>")
        lines.append("")  # Blank line after heading
        # Use Source Index: render as [id] title (title is hyperlink to URL)
        # Each reference on its own line (one per line)
        for citation_id, source_item in ref_map.items():
            url = source_item.url if hasattr(source_item, 'url') else str(source_item)
            title = source_item.title if hasattr(source_item, 'title') else ""
            snippet = source_item.snippet if hasattr(source_item, 'snippet') else ""
            provider = source_item.provider if hasattr(source_item, 'provider') else ""
            
            # Normalize URL
            normalized_url, display_url = _normalize_url(url, title, provider)
            
            # If URL is invalid, try to extract from snippet or content
            if normalized_url == "#":
                # Try extracting from snippet
                extracted_url = _extract_url_from_markdown(snippet or "")
                if extracted_url:
                    normalized_url = extracted_url
                    display_url = extracted_url
                else:
                    # Try extracting from content if available
                    if hasattr(source_item, 'content') and source_item.content:
                        extracted_url = _extract_url_from_markdown(source_item.content)
                        if extracted_url:
                            normalized_url = extracted_url
                            display_url = extracted_url
            
            # Add anchor ID for reference section
            anchor_id = f"ref-{citation_id}"
            
            # Each reference on a new line (one per line, no inline formatting)
            # Only title is clickable (as hyperlink)
            if title:
                if normalized_url.startswith('http'):
                    # Title is clickable link to the URL
                    lines.append(f'<p id="{anchor_id}">[{citation_id}] <a href="{normalized_url}" target="_blank" rel="noopener noreferrer">{title}</a></p>')
                else:
                    # Title links to reference anchor (no valid URL)
                    lines.append(f'<p id="{anchor_id}">[{citation_id}] <a href="#{anchor_id}">{title}</a></p>')
            else:
                # No title available, show URL or placeholder
                if normalized_url.startswith('http'):
                    lines.append(f'<p id="{anchor_id}">[{citation_id}] <a href="{normalized_url}" target="_blank" rel="noopener noreferrer">{display_url}</a></p>')
                else:
                    lines.append(f'<p id="{anchor_id}">[{citation_id}] {display_url}</p>')
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)


def render_html_from_markdown(markdown_text: str) -> str:
    """
    Convert markdown text to HTML.
    
    Args:
        markdown_text: Markdown formatted text
        
    Returns:
        HTML formatted string
    """
    return md.markdown(
        markdown_text or "",
        extensions=["extra", "tables", "fenced_code"]
    )


def render_html_with_styles(html_content: str) -> str:
    """
    Wrap HTML content with CSS styles for PDF export.
    
    Args:
        html_content: HTML content to style
        
    Returns:
        Complete HTML document with styles
    """
    styles = """
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Inter', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.8;
            color: #1e293b;
            max-width: 100%;
        }
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1e293b;
            margin-top: 0;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 3px solid #f97316;
        }
        h2 {
            font-size: 1.875rem;
            font-weight: 600;
            color: #1e293b;
            margin-top: 2.5rem;
            margin-bottom: 1.25rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid rgba(249, 115, 22, 0.2);
        }
        h3 {
            font-size: 1.5rem;
            font-weight: 600;
            color: #334155;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        p {
            font-size: 1.0625rem;
            line-height: 1.85;
            color: #334155;
            margin-bottom: 1.25rem;
            text-align: justify;
        }
        ul, ol {
            margin: 1.25rem 0;
            padding-left: 2rem;
            color: #334155;
        }
        li {
            margin-bottom: 0.75rem;
            line-height: 1.75;
            color: #334155;
        }
        a {
            color: #ea580c;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        code {
            background: #fff7ed;
            color: #ea580c;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
            font-size: 0.9em;
            border: 1px solid rgba(249, 115, 22, 0.2);
        }
        pre {
            background: #fff7ed;
            border: 1px solid rgba(249, 115, 22, 0.2);
            border-radius: 8px;
            padding: 1.25rem;
            overflow-x: auto;
            margin: 1.5rem 0;
        }
        pre code {
            background: transparent;
            border: none;
            padding: 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
        }
        th {
            background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
            color: white;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            font-size: 0.95rem;
        }
        td {
            padding: 0.875rem 1rem;
            border-bottom: 1px solid rgba(249, 115, 22, 0.1);
            color: #334155;
        }
        blockquote {
            border-left: 4px solid #f97316;
            padding-left: 1.5rem;
            margin: 1.5rem 0;
            color: #475569;
            font-style: italic;
            background: #fff7ed;
            padding: 1rem 1.5rem;
            border-radius: 0 8px 8px 0;
        }
        hr {
            border: none;
            border-top: 2px solid rgba(249, 115, 22, 0.2);
            margin: 2.5rem 0;
        }
        details {
            margin: 2rem 0;
            padding: 1rem 0;
            border-top: 2px solid rgba(249, 115, 22, 0.2);
        }
        details summary {
            cursor: pointer;
            padding: 0.75rem 0;
            font-weight: 600;
            color: #1e293b;
        }
        details[open] summary {
            margin-bottom: 1rem;
        }
        p[id^="ref-"] {
            padding: 0.75rem 0;
            border-bottom: 1px solid rgba(249, 115, 22, 0.1);
            margin: 0;
        }
        p[id^="ref-"]:last-of-type {
            border-bottom: none;
        }
    </style>
    """
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Research Report</title>
    {styles}
</head>
<body>
    {html_content}
</body>
</html>"""


def render_pdf_from_markdown(markdown_text: str, output_path: str) -> str:
    """
    Convert markdown text to PDF.
    
    Args:
        markdown_text: Markdown formatted text
        output_path: Path where PDF should be saved
        
    Returns:
        Path to the generated PDF file
        
    Raises:
        ImportError: If weasyprint is not installed
        OSError: If required system libraries are missing
        Exception: If PDF generation fails
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise ImportError(
            "weasyprint is required for PDF export. Install it with: pip install weasyprint"
        )
    except OSError as e:
        # Handle missing system libraries (libpango, libcairo, etc.)
        error_msg = str(e)
        if "libpango" in error_msg or "libcairo" in error_msg or "libgdk" in error_msg:
            raise OSError(
                "PDF export requires system libraries that are not installed.\n\n"
                "On macOS, install them with Homebrew:\n"
                "  brew install pango cairo gdk-pixbuf libffi\n\n"
                "Then reinstall weasyprint:\n"
                "  pip install --upgrade --force-reinstall weasyprint\n\n"
                f"Original error: {error_msg}"
            )
        raise
    
    # Convert markdown to HTML
    html_content = render_html_from_markdown(markdown_text)
    
    # Wrap with styles
    full_html = render_html_with_styles(html_content)
    
    try:
        # Generate PDF
        HTML(string=full_html).write_pdf(output_path)
    except OSError as e:
        # Catch OSError during PDF generation (missing libraries)
        error_msg = str(e)
        if "libpango" in error_msg or "libcairo" in error_msg or "libgdk" in error_msg:
            raise OSError(
                "PDF export requires system libraries that are not installed.\n\n"
                "On macOS, install them with Homebrew:\n"
                "  brew install pango cairo gdk-pixbuf libffi\n\n"
                "Then reinstall weasyprint:\n"
                "  pip install --upgrade --force-reinstall weasyprint\n\n"
                f"Original error: {error_msg}"
            )
        raise
    
    return output_path

