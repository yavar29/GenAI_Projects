from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import re

from agents import Agent, ModelSettings, function_tool
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.schemas.source import SourceDoc
from app.schemas.report import ResearchReport, Section
from app.core.safe import safe_run_async

def _estimate_token_count(text: str) -> int:
    """Estimate token count (rough approximation: ~4 chars per token for English)."""
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback: rough estimate (4 chars per token)
        return len(text) // 4

class WriterOutput(BaseModel):
    """Structured output schema for Writer agent."""
    outline: List[str] = Field(
        default_factory=list,
        description="Bullet list outline items describing what the report covers.",
    )
    sections: List[Section] = Field(
        default_factory=list,
        description="List of sections with markdown summaries and inline [1] style citations. Sections may optionally include subsections for hierarchical organization.",
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Limitations, confidence notes, or next-step suggestions.",
    )

def _save_markdown_impl(path: str, content: str) -> str:
    """Save markdown content to disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Saved {len(content)} chars to {p.resolve()}"

@function_tool
def save_markdown(path: str, content: str) -> str:
    """Save the given Markdown content to local disk."""
    return _save_markdown_impl(path, content)

class WriterAgent:
    """Generates structured research reports from topic, summaries, and sources."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        openai_client: Optional[AsyncOpenAI] = None,
    ) -> None:
        _ = openai_client

        self.agent = Agent(
            name="Writer",
            instructions=(
                "You are a senior research analyst.\n\n"

                "INPUT YOU GET:\n"
                "- A user query.\n"
                "- Optional planning hints (subtopics).\n"
                "- A list of source summaries.\n"
                "- A curated list of sources with numeric IDs [1], [2], etc.\n\n"

                "OVERALL GOAL:\n"
                "- Write a comprehensive, detailed, long-form markdown report that thoroughly answers the query.\n"
                "- Adapt the structure and the angle of the report to the query type (e.g., comparison, how-to, concept explainer, case study).\n"
                "- The report should feel like it was written by a thoughtful human analyst, not generated from a rigid template.\n\n"

                "TITLE & INTRO:\n"
                "- CRITICAL: The first section's summary MUST begin with an H1 title (starting with '# ') that rewrites the query into a proper, well-formatted title.\n"
                "  - Do NOT simply repeat the raw query text verbatim, especially if it is informal, misspelled, or contains phrases like 'suggest how to', 'how to', 'tell me about', etc.\n"
                "  - Transform informal queries into professional, descriptive titles.\n"
                "  - Example: for query 'suggest how to become ai engineer', a good title is '# How to Become an AI Engineer: A Comprehensive Guide'.\n"
                "  - Example: for query 'india vs paksitan', a good title is '# India and Pakistan: A Comparative Analysis'.\n"
                "- The H1 report title MUST appear only at the very start of the first section's summary.\n"
                "- Do NOT reuse the H1 title inside the 'title' field or repeat it as any H2/H3 heading.\n"
                "- The first section's 'title' field should be a short label such as 'Introduction' or 'Overview', not the full report title.\n"
                "- After the H1 title, write an introductory paragraph (3–6 sentences) that frames the topic, explains why it matters, and previews the structure of the report.\n\n"

                "STRUCTURE (ADAPTIVE):\n"
                "- Organize the report into logical sections with H2/H3 headings.\n"
                "- Choose section titles that fit the query type (e.g., 'Historical Background', 'Current Capabilities', 'Economic Comparison', 'Case Studies', 'Risks & Opportunities').\n"
                "- Do NOT hardcode a fixed structure. Instead, design the structure that best serves the specific query.\n"
                "- When it naturally fits the topic, you may include concluding sections such as 'Implications', 'Recommendations', or 'Limitations & Open Questions', but only if they are useful and relevant.\n"
                "- The JSON 'outline' field should list the main sections in order, but the markdown itself should not include headings like 'Table of Contents' or 'Outline'.\n"
                "- Inside the markdown, do NOT create sections literally called 'Table of Contents' or 'Outline'.\n\n"

                "SECTION DEPTH & INTERNAL STRUCTURE:\n"
                "- Each major section should be substantial and feel complete.\n"
                "- Within each section, follow a clear internal structure:\n"
                "  1) Start with few sentences that state the main idea of the section in plain language.\n"
                "  2) Then provide detailed evidence: specific numbers, dates, names, mechanisms, concrete examples, etc.\n"
                "  3) Use bullet lists or numbered lists when enumerating factors, pros/cons, dimensions of comparison, or steps.\n"
                "  4) Where helpful, you may include small markdown tables to summarize side-by-side metrics (e.g., GDP, troop counts, performance indicators etc.).\n"
                "  5) End the section with few sentences that interpret what the evidence means in context and connect it back to the overall question.\n\n"
                
                "NESTED SUBTOPICS (SUBSECTIONS):\n"
                "- When a section naturally breaks down into distinct subtopics, use the 'subsections' field to organize content hierarchically.\n"
                "- Use subsections when:\n"
                "  * A section covers multiple related but distinct aspects (e.g., 'Economic Impact' section with subsections: 'GDP Growth', 'Employment Trends', 'Trade Relations').\n"
                "  * You need to compare multiple items within a section (e.g., 'Key Technologies' with subsections for each technology).\n"
                "  * A section contains case studies, examples, or categories that deserve their own headings.\n"
                "  * The content would benefit from clearer organization with intermediate headings.\n"
                "- Each subsection should have:\n"
                "  * A clear, descriptive title (e.g., 'Machine Learning Applications', 'Regulatory Challenges', 'Case Study: Company X').\n"
                "  * Substantial content (typically 100-300 words) with specific facts, examples, and citations.\n"
                "  * Bullet points or numbered lists when appropriate (e.g., for enumerating features, steps, or factors).\n"
                "- The main section's 'summary' field should provide an introduction/overview, then subsections provide detailed breakdown.\n"
                "- You can mix: some sections with subsections, and some without (flat structure). Choose based on what best serves the content.\n"
                "- Do NOT force subsections if the section flows better as a single narrative. Use them only when they genuinely improve organization.\n\n"

                "USE OF SOURCES & CROSS-SOURCE SYNTHESIS:\n"
                "- You must synthesize across multiple sources instead of summarizing them one by one.\n"
                "- Combine facts from multiple sources wherever possible to create cohesive analysis.\n"
                "- If multiple sources agree on a claim, you may cite them together (e.g., [1][3][5]).\n"
                "- If sources conflict or present different perspectives, explicitly note the disagreement and explain the differing viewpoints.\n\n"

                "CITATIONS:\n"
                "- Use inline numeric citations like [1], [2][5] ONLY for factual claims that need source attribution.\n"
                "- Place citations at the END of sentences, just before the final punctuation (e.g., '... in 2025.[1][4]').\n"
                "- NEVER use citation brackets [ ] for:\n"
                "  * Product names or versions (e.g., write 'WeatherNext 2' not 'WeatherNext-[2]')\n"
                "  * Measurements or quantities (e.g., write '15 days' not '[15] days', '0.25 degrees' not '0.25[°]')\n"
                "  * Numbers that are part of names, dates, or technical specifications\n"
                "- Citations should ONLY appear as [1], [2], [3] etc. at sentence endings to reference sources.\n"
                "- Use citations sparingly: 1–2 citation clusters per paragraph is usually enough.\n"
                "- Only use citation numbers that exist in the numbered source list provided.\n"
                "- CRITICAL: Each source in the numbered list appears only once. Do NOT cite the same source multiple times with different numbers.\n"
                "- If you need to reference the same source multiple times in different sections, use the same citation number consistently.\n"
                "- For each section, populate the 'citations' field with the main source IDs used there (avoid listing the same ID multiple times).\n"
                "- Do not invent citations; if there is no supporting source, omit the citation.\n\n"


                "STYLE:\n"
                "- Write in your own words; do NOT copy the summaries or source text verbatim.\n"
                "- Aim for depth over brevity: detailed, specific, and analytical rather than generic.\n"
                "- Prefer concrete, specific statements over vague generalities.\n"
                "- Connect ideas between sections when helpful (e.g., 'This builds on the trends discussed in the previous section').\n"
                "- Keep the tone clear, professional, and balanced. Avoid hype or sensational language.\n\n"

                "OUTPUT FORMAT (IMPORTANT):\n"
                "- You MUST return exactly one valid JSON object and nothing else (no markdown, no backticks, no commentary).\n"
                "- The JSON must match WriterOutput with keys: \"outline\", \"sections\", and \"notes\".\n"
                "- Example high-level shape (do NOT include comments):\n"
                "  {\n"
                "    \"outline\": [\"<section 1 title>\", \"<section 2 title>\", \"<section 3 title>\", ...],\n"
                "    \"sections\": [\n"
                "      {\n"
                "        \"title\": \"<section title>\",\n"
                "        \"summary\": \"<markdown content for this section with inline [1]-style citations>\",\n"
                "        \"citations\": [1, 3, 5],\n"
                "        \"subsections\": [\n"
                "          {\n"
                "            \"title\": \"<subsection title>\",\n"
                "            \"content\": \"<markdown content for subsection with citations>\",\n"
                "            \"citations\": [2, 4]\n"
                "          }\n"
                "        ]\n"
                "      }\n"
                "    ],\n"
                "    \"notes\": [\"<limitation or confidence note>\", \"<suggestion for follow-up research>\"]\n"
                "  }\n"
                "- 'outline': a bullet-style list (as plain strings) describing the main sections of the report.\n"
                "- 'sections': each item has a 'title', a 'summary' (markdown), optional 'citations', and optional 'subsections'.\n"
                "  - 'summary': the main content/introduction for the section (markdown with inline numeric citations like [1][3]).\n"
                "  - 'citations': a list of the main source IDs that support this section.\n"
                "  - 'subsections' (optional): an array of objects with 'title', 'content' (markdown with citations), and 'citations'.\n"
                "    * Use subsections when a section naturally breaks into distinct subtopics that benefit from their own headings.\n"
                "    * Each subsection's 'content' can include paragraphs, bullet lists, numbered lists, or tables as needed.\n"
                "- 'notes': list any limitations, confidence notes, or suggestions for follow-up research.\n"
                "- Use double quotes for all JSON keys and string values.\n"
                "- Do NOT wrap the JSON in backticks or extra formatting; return raw JSON only.\n"
            ),
            model=model,
            tools=[save_markdown],
            model_settings=ModelSettings(
                temperature=0.3,
                max_output_tokens=16000,
            ),
            output_type=WriterOutput,
        )



    # async entrypoint 

    async def draft_async(
        self,
        topic: str,
        subtopics: List[str],
        summaries: List[str],
        sources: List[SourceDoc],
        query_level_summaries: str = "",
    ) -> ResearchReport:
        """Async wrapper used by ResearchManager.

        - Builds a rich prompt including search/document summaries and sources.
        - Calls the agent via safe_run_async.
        - Normalises citations to integer IDs in the resulting ResearchReport.
        """
        prompt = _build_prompt(topic, subtopics, summaries, sources, query_level_summaries)

        out: WriterOutput = await safe_run_async(self.agent, prompt, WriterOutput)
        
        # Enhanced validation of structured output
        if not out.sections:
            raise ValueError("WriterAgent output missing sections. The model did not generate any report sections.")
        
        # Check for empty or very short sections (warn but don't fail - let LLM decide structure)
        empty_sections = [i for i, sec in enumerate(out.sections) if not sec.summary or len(sec.summary.strip()) < 30]
        if empty_sections:
            print(f"Warning: WriterAgent generated {len(empty_sections)} empty/short sections: {empty_sections}")
        
        # Validate outline matches sections (warn but don't fail)
        if out.outline and len(out.outline) != len(out.sections):
            print(f"Warning: Outline length ({len(out.outline)}) doesn't match sections ({len(out.sections)})")

        return _writer_output_to_report(topic, out, sources)

# Shared utilities

def _build_prompt(
    topic: str,
    subtopics: List[str],
    summaries: List[str],
    sources: List[SourceDoc],
    query_level_summaries: str = "",
) -> str:
    """Construct the final text prompt given to the Writer agent.

    We provide:

    - The query/topic.
    - (Optional) planning hints / subtopics.
    - A block of search/document summaries.
    - A numbered 'Curated sources' section that the model cites as [1], [2], ...
    """
    prompt = f"Query: {topic}\n\n"
    prompt += (
        "You must generate a comprehensive, detailed, high-quality research report with an adaptive structure "
        "that fits this specific query.\n\n"
        "GENERAL REQUIREMENTS:\n"
        "- The report must be long-form and thorough, not a brief summary.\n"
        "- Each major section should be substantial (typically 300–600 words or more) with deep analysis and detailed explanations.\n"
        "- Include specific facts, numbers, dates, names, and technical details wherever available from the sources.\n"
        "- Provide multiple examples and concrete evidence, not just abstract statements.\n"
        "- Cover all major aspects implied by the query.\n"
        "- CRITICAL: The first section's summary MUST start with an H1 title (format: '# Title Here') that transforms the raw query into a professional, well-formatted title.\n"
        "  - Remove informal query prefixes like 'suggest how to', 'how to', 'tell me about', 'explain', 'what is', 'can you', 'please', etc.\n"
        "  - Convert the query into a proper title case format suitable for a research report.\n"
        "  - Do NOT simply echo the raw query wording - transform it into a polished title.\n\n"
    )

    # Heuristic: tailor structure for comparison-style queries like "X vs Y"
    lower_topic = topic.lower()
    if " vs " in lower_topic or " vs. " in lower_topic or " versus " in lower_topic:
        prompt += (
            "STRUCTURE HINT (COMPARISON QUERY):\n"
            "- This query appears to be a comparative 'X vs Y' question.\n"
            "- Design a structure that makes the comparison explicit and easy to follow. For example:\n"
            "  - Start with an overview that explains what is being compared and why it matters now.\n"
            "  - Provide separate background sections for each side (e.g., history, baseline context).\n"
            "  - Include at least one section that directly compares key dimensions side-by-side (e.g., military, economy, technology, diplomacy, or performance metrics).\n"
            "  - Use bullet lists or tables to contrast metrics or attributes.\n"
            "  - Conclude with a balanced comparative assessment that summarizes the main differences, areas of parity, and likely future trajectories.\n"
            "- These are advisory hints; you should still adapt the final structure to best answer the actual query.\n\n"
        )

    if subtopics:
        prompt += (
            "\nPlanning hints (advisory only, optional): "
            + ", ".join(subtopics)
            + "\n"
        )

    prompt += "\n---\n\n"
    
    # Insert query-level summaries at the top (executive briefing)
    if query_level_summaries:
        prompt += "Query-Level Search Summaries:\n"
        prompt += query_level_summaries
        prompt += (
            "\n\n(Note: The above are high-level query summaries providing context across research waves. "
            "Use them for synthesis but cite specific sources below, not these summaries.)\n\n"
        )
        prompt += "---\n\n"
    
    # Cross-source synthesis instruction
    prompt += (
        "CRITICAL: Cross-Source Synthesis Required\n"
        "You must combine facts from multiple sources wherever possible. "
        "If multiple sources agree on a claim, cite them all together (e.g., [2][5][7]). "
        "If sources conflict or present different perspectives, explicitly note the disagreement. "
        "Synthesize information across sources to create cohesive analysis, not isolated summaries.\n\n"
    )

    # Include search / document summaries (per-result only, query-level already added above)
    if summaries:
        prompt += "Source Summaries:\n"
        for summary in summaries:
            # Skip query-level summaries here (already added above)
            if summary.startswith("Query-level search summaries:"):
                continue
            # Truncate very long summaries in the prompt
            if len(summary) > 3000:
                summary = summary[:3000] + "... [truncated]"
            prompt += f"{summary}\n"
        prompt += "\n"

    # Curated numbered sources for citations (simplified format with enhanced titles)
    prompt += "Sources (cite as [1], [2], etc.):\n"
    for i, s in enumerate(sources, 1):
        # Use shorter snippet for prompt efficiency
        snippet_text = (s.snippet or "")[:150]
        kind = (
            "File"
            if (s.source_type or "").lower() == "file"
            else "Web"
        )
        # Enhance title with context from snippet if title is generic
        enhanced_title = s.title or "Untitled Source"
        if len(enhanced_title) < 30 and snippet_text:
            # Extract key topic from snippet for better context
            snippet_words = snippet_text.split()[:5]
            if snippet_words:
                topic_hint = " ".join(snippet_words)
                enhanced_title = f"{enhanced_title} – {topic_hint}"
        prompt += f"[{i}] {enhanced_title} ({kind}) | {snippet_text}\n"

    prompt += (
        "\nUse ONLY the above numbered sources for factual claims.\n"
        "- When you make concrete factual statements, support them with citations at the END of sentences only.\n"
        "- NEVER use citation brackets [ ] for product names, versions, measurements, or quantities.\n"
        "- Examples of what NOT to cite: 'WeatherNext 2' (product name), '15 days' (measurement), '0.25 degrees' (quantity).\n"
        "- Citations [1], [2], [3] should ONLY appear at sentence endings to reference sources.\n"
        "- Use 1–2 citation clusters per paragraph; do not over-cite.\n"
        "- Do not invent citation numbers that are not listed here.\n"
        "- CRITICAL: Each source in the numbered list above appears only once. Each number [1], [2], [3], etc. refers to a unique, distinct source.\n"
        "- Do NOT cite the same source multiple times with different numbers. If you reference the same source in different sections, use the same citation number consistently.\n"
        "- The sources list has already been deduplicated, so there are no duplicate sources with different numbers.\n"
        "- Interpretive or high-level analytical statements can be left uncited or backed by one or two key sources.\n"
    )

    
    # Token guard: estimate and warn if prompt is too long
    estimated_tokens = _estimate_token_count(prompt)
    if estimated_tokens > 20000:
        # Truncate summaries if prompt is too long
        prompt_parts = prompt.split("Source Summaries:\n")
        if len(prompt_parts) > 1:
            base_prompt = prompt_parts[0]
            summaries_section = prompt_parts[1].split("\nSources (cite")[0]
            sources_section = "\nSources (cite" + prompt_parts[1].split("\nSources (cite")[1]
            
            # Keep only first 8 summaries if too long
            summary_lines = summaries_section.split("\n")
            if len(summary_lines) > 20:
                summaries_section = "\n".join(summary_lines[:20]) + "\n... [additional sources truncated]"
            
            prompt = base_prompt + "Source Summaries:\n" + summaries_section + sources_section
            estimated_tokens = _estimate_token_count(prompt)
    
    # Debug: log token count (can be removed in production)
    if estimated_tokens > 20000:
        print(f"⚠️ Writer prompt length: ~{estimated_tokens} tokens (target: <20k)")

    return prompt

def _writer_output_to_report(
    topic: str,
    out: WriterOutput,
    sources: List[SourceDoc],
) -> ResearchReport:
    """Convert WriterOutput from the agent into a ResearchReport.

    - Derives a clean global title from the first section's H1 (if present).
    - Strips that H1 from the section summary so it doesn't duplicate.
    - Normalizes section titles (no leading '#' etc.).
    - Ensures citations are a clean list[int] per section and subsection.
    """
    from app.schemas.report import Subsection

    derived_topic = topic

    if out.sections:
        first_sec = out.sections[0]

        # Extract H1 from first summary for main title
        if first_sec.summary:
            raw_summary = first_sec.summary.lstrip()
            lines = raw_summary.splitlines()
            if lines:
                m = re.match(r'^#\s+(.+)$', lines[0].strip())
                if m:
                    derived_topic = m.group(1).strip()
                    remaining = "\n".join(lines[1:]).lstrip()
                    first_sec.summary = remaining or ""

        # Normalize section titles
        for sec in out.sections:
            if getattr(sec, "title", None):
                clean_title = re.sub(r'^#+\s*', '', sec.title).strip()
                sec.title = clean_title

        # Rename first section if duplicate of title
        if getattr(first_sec, "title", None) and derived_topic:
            if first_sec.title.strip().lower() == derived_topic.strip().lower():
                first_sec.title = "Introduction"

    fixed_sections: List[Section] = []

    for sec in out.sections:
        citation_ids: List[int] = []
        if sec.citations:
            for c in sec.citations:
                try:
                    citation_ids.append(int(c))
                except (ValueError, TypeError):
                    continue

        fixed_subsections = None
        if hasattr(sec, 'subsections') and sec.subsections:
            fixed_subsections = []
            for subsec in sec.subsections:
                sub_citation_ids: List[int] = []
                if hasattr(subsec, 'citations') and subsec.citations:
                    for c in subsec.citations:
                        try:
                            sub_citation_ids.append(int(c))
                        except (ValueError, TypeError):
                            continue

                fixed_subsections.append(
                    Subsection(
                        title=subsec.title,
                        content=subsec.content,
                        citations=sub_citation_ids,
                    )
                )

        fixed_sections.append(
            Section(
                title=sec.title,
                summary=sec.summary,
                citations=citation_ids,
                subsections=fixed_subsections,
            )
        )

    return ResearchReport(
        topic=derived_topic,
        outline=out.outline or [],
        sections=fixed_sections,
        sources=sources,
        notes=out.notes or [],
    )
