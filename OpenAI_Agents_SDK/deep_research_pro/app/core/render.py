from __future__ import annotations
from typing import Dict, Optional
import re
import markdown as md

def _slugify(text: str) -> str:
    """Convert section title to anchor-friendly slug."""
    # Lowercase, replace spaces with hyphens, remove special chars
    slug = text.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

def render_markdown(report, source_index: Optional[Dict[int, any]] = None) -> str:  # type: ignore
    """
    Render ResearchReport to markdown.
    
    Args:
        report: ResearchReport object
        source_index: Optional dict mapping numeric ID -> SourceItem (for deterministic citations)
    """
    lines = [f"# {report.topic}", ""]

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
            # Generate slug from heading text (no numbering) to match actual heading
            heading_text = sec.title
            slug = _slugify(heading_text)
            lines.append(f"- [{heading_text}](#{slug})")
        lines.append("")

    # Show outline first if available
    if report.outline:
        lines.append("## Outline")
        for item in report.outline:
            lines.append(f"- {item}")
        lines.append("")

    # Sections with inline citations already in text (no separate Citations line)
    for i, sec in enumerate(report.sections, 1):
        # Create heading - markdown renderers will auto-create anchors from heading text
        # Use section title directly without numbering
        heading_text = sec.title
        lines.append(f"## {heading_text}")
        
        # Replace inline citations [1], [2] with styled clickable boxes
        # Handle both [1] and [1][2] formats, ensuring proper spacing
        summary_text = sec.summary.strip()
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
                        return f"[{num_str}]"
                except (ValueError, TypeError):
                    pass
                return num_str
            
            # Pattern to match standalone numbers (1-3 digits) that could be citations
            # Match numbers that are: at word boundaries, followed by space, punctuation, or end of string
            # But not followed by another digit (to avoid matching parts of larger numbers)
            summary_text = re.sub(r'\b(\d{1,3})\b(?=\s|[,.;:!?]|$)', wrap_bare_citation, summary_text)
            
            # Find all citation patterns like [1], [2], [10] and convert to styled HTML boxes
            def replace_citation(match):
                citation_id_str = match.group(1)
                try:
                    citation_id = int(citation_id_str)
                    if citation_id in id_to_source:
                        source_item = id_to_source[citation_id]
                        url = source_item.url if hasattr(source_item, 'url') else str(source_item)
                        
                        # Clean up URL first (remove angle brackets if present)
                        url = url.strip('<>').strip()
                        
                        # Fix malformed URLs (missing protocol or domain)
                        if url and not url.startswith(('http://', 'https://', '#')):
                            if url.startswith('/'):
                                # Relative URL - link to reference section
                                url = f"#ref-{citation_id}"
                            elif '.' not in url or url.strip() == '' or len(url) < 4:
                                # Malformed URL - link to reference section
                                url = f"#ref-{citation_id}"
                            else:
                                # Missing protocol, add https
                                url = f"https://{url}"
                        
                        # Use HTML span with inline styles for box appearance
                        return f'<a href="{url}" style="display: inline-block; padding: 2px 6px; margin: 0 2px; background-color: #e3f2fd; border: 1px solid #2196f3; border-radius: 3px; color: #1976d2; text-decoration: none; font-size: 0.9em; font-weight: 500;">[{citation_id_str}]</a>'
                except (ValueError, AttributeError):
                    pass
                return match.group(0)  # Return original if can't parse
            
            summary_text = re.sub(r'\[(\d+)\]', replace_citation, summary_text)
        
        lines.append(summary_text)
        lines.append("")

    # Notes (may include next steps)
    if report.notes:
        lines.append("## Notes")
        for n in report.notes:
            lines.append(f"- {n}")
        lines.append("")

    # References: Build programmatically from Source Index
    if ref_map:
        lines.append("## References")
        lines.append("")  # Blank line after heading
        # Use Source Index: render as [id] title — url (with anchor for internal links)
        # Each reference on its own line (one per line)
        for citation_id, source_item in ref_map.items():
            url = source_item.url if hasattr(source_item, 'url') else str(source_item)
            title = source_item.title if hasattr(source_item, 'title') else ""
            
            # Clean up URL first (remove angle brackets if present)
            original_url = url = url.strip('<>').strip() if url else ""
            
            # Fix malformed URLs (missing protocol or domain)
            display_url = original_url
            if url and not url.startswith(('http://', 'https://', '#')):
                if url.startswith('/'):
                    # Relative URL - mark as unavailable but show original
                    url = "#"  # Non-functional link
                    display_url = f"(Relative URL: {original_url})"
                elif '.' not in url or url.strip() == '' or len(url) < 4:
                    # Malformed URL - mark as unavailable
                    url = "#"
                    display_url = f"(Invalid URL: {original_url})"
                else:
                    # Missing protocol, add https
                    url = f"https://{url}"
                    display_url = url
            
            # Add anchor ID for reference section
            anchor_id = f"ref-{citation_id}"
            
            # Each reference on a new line (one per line, no inline formatting)
            # Title is clickable, URL is also clickable
            if title:
                if url.startswith('http'):
                    # Both title and URL are clickable links
                    lines.append(f'<p id="{anchor_id}">[{citation_id}] <a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a> — <a href="{url}" target="_blank" rel="noopener noreferrer">{display_url}</a></p>')
                else:
                    # Title links to reference anchor, URL shown as text
                    lines.append(f'<p id="{anchor_id}">[{citation_id}] <a href="#{anchor_id}">{title}</a> — {display_url}</p>')
            else:
                if url.startswith('http'):
                    lines.append(f'<p id="{anchor_id}">[{citation_id}] <a href="{url}" target="_blank" rel="noopener noreferrer">{display_url}</a></p>')
                else:
                    lines.append(f'<p id="{anchor_id}">[{citation_id}] {display_url}</p>')
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
        extensions=["extra", "toc", "tables", "fenced_code"]
    )

