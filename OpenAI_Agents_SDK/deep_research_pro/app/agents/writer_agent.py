from __future__ import annotations

from pathlib import Path
from typing import List, Optional

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
        description="List of sections with markdown summaries and inline [1] style citations.",
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
        model: str = "gpt-4o",
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
                "YOUR JOB:\n"
                "- Write a comprehensive, detailed, long-form markdown report that thoroughly answers the query.\n"
                "- Each section should be substantial (typically 200-400 words) with deep analysis, not brief summaries.\n"
                "- Organize it into logical sections with H2/H3 headings.\n"
                "- Use bullet lists or numbered lists whenever you enumerate items.\n"
                "- Synthesize across multiple sources instead of summarizing them one by one.\n"
                "- Combine facts from multiple sources wherever possible to create cohesive analysis.\n"
                "- Provide extensive detail: include specific numbers, dates, names, technical details, and concrete examples.\n"
                "- Expand on implications, context, and connections between ideas.\n"
                "- Use inline numeric citations like [1], [2][5] for specific factual claims.\n"
                "- Provide one or two citations per key point. If multiple sources agree on a claim, cite them all (e.g., [1][3][5]).\n"
                "- If sources conflict or present different perspectives, explicitly note the disagreement and explain the differing viewpoints.\n"
                "- End with a comprehensive 'Practical implications' section and a detailed 'Limitations & open questions' section.\n\n"
                "STYLE:\n"
                "- Write in your own words; do NOT copy the summaries.\n"
                "- Be thorough and detailed - aim for depth over brevity.\n"
                "- Include specific examples, statistics, and technical details from sources.\n"
                "- Link ideas between sections when helpful (e.g., 'This builds on the applications in section 2').\n"
                "- Avoid very generic sentences; prefer concrete, specific statements with supporting evidence.\n"
                "- Each section should feel complete and informative, not rushed or superficial.\n\n"
                "OUTPUT FORMAT:\n"
                "- Return a JSON object matching WriterOutput: {outline: [...], sections: [...], notes: [...]}.\n"
                "- 'outline': bullet list of the main sections in order.\n"
                "- 'sections': each item has a 'title', 'summary' (markdown), and optional 'citations'.\n"
                "- 'notes': limitations, confidence, or follow-up research ideas.\n"
                "Do NOT wrap the JSON in backticks or extra formatting."
            ),
            model=model,
            tools=[save_markdown],
            model_settings=ModelSettings(
                temperature=0.3,
                max_output_tokens=16000,  # Increased for more detailed, comprehensive reports
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
        
        # Validate section quality
        if len(out.sections) < 2:
            raise ValueError(f"WriterAgent generated too few sections ({len(out.sections)}). Expected at least 2 sections.")
        
        # Check for empty or very short sections
        empty_sections = [i for i, sec in enumerate(out.sections) if not sec.summary or len(sec.summary.strip()) < 30]
        if empty_sections:
            print(f"Warning: WriterAgent generated {len(empty_sections)} empty/short sections: {empty_sections}")
        
        # Validate outline matches sections
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
        "You must generate a comprehensive, detailed, high-quality research report with an adaptive structure that fits this query type.\n"
        "IMPORTANT: This report should be extensive and thorough. Each section must be substantial (200-400 words minimum) with:\n"
        "- Deep analysis and detailed explanations\n"
        "- Specific facts, numbers, dates, and technical details\n"
        "- Multiple examples and concrete evidence\n"
        "- Comprehensive coverage of all aspects mentioned in the query\n"
        "- Rich context and background information\n"
        "Do NOT write brief summaries. Write detailed, informative content that thoroughly explores each topic.\n"
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
        "\nUse ONLY the above sources for factual claims. "
        "Cite as [1], [2][5] when multiple sources support a claim. "
        "Do not invent citations.\n"
    )
    
    # Token guard: estimate and warn if prompt is too long
    estimated_tokens = _estimate_token_count(prompt)
    if estimated_tokens > 12000:
        # Truncate summaries if prompt is too long
        prompt_parts = prompt.split("Source Summaries:\n")
        if len(prompt_parts) > 1:
            base_prompt = prompt_parts[0]
            summaries_section = prompt_parts[1].split("\nSources (cite")[0]
            sources_section = "\nSources (cite" + prompt_parts[1].split("\nSources (cite")[1]
            
            # Keep only first 8 summaries if too long
            summary_lines = summaries_section.split("\n")
            if len(summary_lines) > 8:
                summaries_section = "\n".join(summary_lines[:8]) + "\n... [additional sources truncated]"
            
            prompt = base_prompt + "Source Summaries:\n" + summaries_section + sources_section
            estimated_tokens = _estimate_token_count(prompt)
    
    # Debug: log token count (can be removed in production)
    if estimated_tokens > 10000:
        print(f"⚠️ Writer prompt length: ~{estimated_tokens} tokens (target: <10k)")

    return prompt

def _writer_output_to_report(
    topic: str,
    out: WriterOutput,
    sources: List[SourceDoc],
) -> ResearchReport:
    """Convert WriterOutput from the agent into a ResearchReport.

    - Ensures citations are a clean list[int] per section.
    - Leaves extraction of [1] tokens from the text to ResearchManager post-processing.
    """
    fixed_sections: List[Section] = []

    for sec in out.sections:
        citation_ids: List[int] = []

        if sec.citations:
            for c in sec.citations:
                try:
                    citation_ids.append(int(c))
                except (ValueError, TypeError):
                    # If it's a string/URL, ignore it; ResearchManager will
                    # extract [1] style citations from the text later.
                    continue

        fixed_sections.append(
            Section(
                title=sec.title,
                summary=sec.summary,
                citations=citation_ids,
            )
        )

    return ResearchReport(
        topic=topic,
        outline=out.outline or [],
        sections=fixed_sections,
        sources=sources,
        notes=out.notes or [],
    )
