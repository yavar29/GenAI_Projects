from __future__ import annotations
import re
from typing import Dict, Optional

def render_markdown(report, source_index: Optional[Dict[int, any]] = None) -> str:  # type: ignore
    """
    Render ResearchReport to markdown.
    
    Args:
        report: ResearchReport object
        source_index: Optional dict mapping numeric ID -> SourceItem (for deterministic citations)
    """
    lines = [f"# {report.topic}", ""]

    # Show outline first if available
    if report.outline:
        lines.append("## Outline")
        for item in report.outline:
            lines.append(f"- {item}")
        lines.append("")

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

    # Sections with inline citations already in text (no separate Citations line)
    for i, sec in enumerate(report.sections, 1):
        lines.append(f"## {i}. {sec.title}")
        # The summary already contains inline citations [1], [2] from the Writer
        lines.append(sec.summary.strip())
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
        # Use Source Index: render as [id] title — <url>
        for citation_id, source_item in ref_map.items():
            url = source_item.url if hasattr(source_item, 'url') else str(source_item)
            title = source_item.title if hasattr(source_item, 'title') else ""
            if title:
                lines.append(f"[{citation_id}] {title} — <{url}>")
            else:
                lines.append(f"[{citation_id}] <{url}>")
        lines.append("")

    return "\n".join(lines)

