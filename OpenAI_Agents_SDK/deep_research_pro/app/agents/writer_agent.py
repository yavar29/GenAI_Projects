from __future__ import annotations
from typing import List, Optional
from pathlib import Path
from agents import Agent, Runner, ModelSettings, function_tool
from pydantic import BaseModel, Field
from openai import AsyncOpenAI

from app.schemas.source import SourceDoc
from app.schemas.report import ResearchReport, Section
from app.core.safe import safe_run_async

class WriterOutput(BaseModel):
    outline: List[str] = Field(default_factory=list, description="Bullet list outline items describing what the report covers")
    sections: List[Section] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list, description="Limitations, confidence notes, or next-step suggestions")

# --- example custom tool (demonstrates @function_tool pattern) ---
def _save_markdown_impl(path: str, content: str) -> str:
    """Save the given Markdown content to local disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Saved {len(content)} chars to {p.resolve()}"

@function_tool
def save_markdown(path: str, content: str) -> str:
    """Save the given Markdown content to local disk."""
    return _save_markdown_impl(path, content)

class WriterAgent:
    """
    Turns topic + subtopics + sources into a structured ResearchReport with sections and citations.
    Provides sync and async entrypoints. Exposes a simple custom tool (save_markdown).
    """
    def __init__(self, model: str = "gpt-4o", openai_client: Optional[AsyncOpenAI] = None):
        # If client provided, ensure it's available to the SDK via environment
        if openai_client:
            # The SDK reads from environment, so we ensure the API key is set
            # The client itself will be used by the SDK internally
            pass
        self.agent = Agent(
            name="Writer",
            instructions=(
                "You are a senior research analyst tasked with writing a cohesive, long-form research report.\n\n"
                "You will always receive:\n"
                "- The user query.\n"
                "- Search result summaries and a curated list of sources with numeric IDs.\n\n"
                "Your job is to generate a long-form, markdown-formatted research output that:\n"
                "- Uses clear H2/H3 headings when appropriate.\n"
                "- Uses lists, tables, or step-by-step structures when they improve clarity.\n"
                "- Stays grounded in the provided evidence and never fabricates specific facts.\n"
                "- Uses inline numeric citations [1], [2], [3] only for claims supported by evidence.\n"
                "- Returns a JSON payload matching the WriterOutput schema (outline, sections, notes).\n\n"
                "=== CORE RULES ===\n"
                "- Infer the question type (definition, comparison, how-to, forecast, etc.) from the query.\n"
                "- Choose 5–10 sections with headings that best fit THIS query (do not use the same template for every query).\n"
                "- For complex topics, begin with a short 'Key Insights' section containing 5–8 bullet points summarizing the most important takeaways.\n"
                "- Use a mix of narrative, lists, checklists, and tables when appropriate.\n"
                "- Include a short 'Why this matters' or 'Practical implications' section near the end for real-world relevance.\n"
                "- End with a brief 'Limitations & Open Questions' section listing gaps, uncertainties, or follow-up angles.\n"
                "- Base non-obvious claims on the given summaries and sources.\n"
                "- When multiple sources support the same claim, prefer citing more than one, e.g., [1][3].\n"
                "- When sources disagree or are uncertain, explicitly highlight the disagreement.\n"
                "- Paraphrase and synthesize; do not just restate one source at a time.\n"
                "- Use concise paragraphs (3–6 sentences) and avoid giant walls of text.\n"
                "- Citations MUST always appear in square brackets: [1], [2][5]. Never use bare numbers like 12 or 34 as citations.\n"
                "- Do not invent new numeric IDs. Use only those provided in the input.\n\n"
                "=== OUTPUT REQUIREMENTS ===\n"
                "- You must return a JSON object matching WriterOutput: { outline: [...], sections: [...], notes: [...] }.\n"
                "- 'outline' should list the main sections in order.\n"
                "- 'sections' is a list where each section has a title and a markdown summary (which may include headings, lists, and citations).\n"
                "- 'notes' should include limitations, confidence notes, or suggestions for follow-up research.\n"
                "Do not wrap the JSON in backticks or any extra formatting; return the raw JSON object."
            ),
            model=model,
            tools=[save_markdown],
            model_settings=ModelSettings(temperature=0.2),
            output_type=WriterOutput,
        )

    # ---- async ----
    async def draft_async(
        self,
        topic: str,
        subtopics: List[str],
        summaries: List[str],
        sources: List[SourceDoc],
    ) -> ResearchReport:
        prompt = _build_prompt(topic, subtopics, summaries, sources)
        out: WriterOutput = await safe_run_async(self.agent, prompt, WriterOutput)
        # Citations are extracted and validated in ResearchManager._write_report post-processing
        # WriterOutput may have citations as strings or empty; they'll be replaced with numeric IDs
        fixed_sections: List[Section] = []
        for sec in out.sections:
            # Convert any string citations to empty list (will be populated by post-processing)
            # Or if WriterOutput already has numeric IDs, keep them
            citation_ids: List[int] = []
            if sec.citations:
                for c in sec.citations:
                    try:
                        # Try to parse as int (if already numeric)
                        citation_ids.append(int(c))
                    except (ValueError, TypeError):
                        # If it's a string/URL, ignore it (post-processing will extract from text)
                        pass
            fixed_sections.append(Section(
                title=sec.title,
                summary=sec.summary,
                citations=citation_ids,  # List[int]
            ))
        return ResearchReport(
            topic=topic, 
            outline=out.outline or [],
            sections=fixed_sections, 
            sources=sources, 
            notes=out.notes or []
        )

# --- shared utilities ---
def _build_prompt(
    topic: str,
    subtopics: List[str],
    summaries: List[str],
    sources: List[SourceDoc],
) -> str:
    prompt = f"Query: {topic}\n\n"
    prompt += "You must generate a high-quality research report with an adaptive structure that fits this query type.\n"

    if subtopics:
        prompt += f"\nPlanning hints (advisory only, optional): {', '.join(subtopics)}\n"

    prompt += "\n---\n\n"

    # Include search summaries (similar to reference flow)
    if summaries:
        prompt += "Search Results:\n"
        for summary in summaries:
            if summary.startswith("Query-level search summaries:"):
                prompt += f"\n{summary}\n"
                prompt += "(Note: The above query-level summaries are for context only—do not cite them. Use the numbered results below for citations.)\n\n"
            elif "Title:" in summary and "URL:" in summary:
                prompt += f"\n{summary}\n"
            else:
                prompt += f"{summary}\n"
        prompt += "\n"

    prompt += "Curated sources (with numeric IDs for citations):\n"
    for i, s in enumerate(sources, 1):
        prompt += f"[{i}] {s.title} | {s.url} | {s.published or 'N/A'} | {s.snippet[:200]}\n"

    prompt += (
        "\nUse the above search results and curated sources to produce a comprehensive research report. "
        "Use inline numeric citations [1], [2] when referencing sources. "
        "If the Search Results include numeric IDs (e.g., '1. Title'), use those IDs; otherwise, use the IDs from the Curated sources list. "
        "Do not invent IDs or cite sources that are not listed.\n"
    )
    return prompt

def _draft_core(agent: Agent, topic: str, subtopics: List[str], summaries: List[str], sources: List[SourceDoc]) -> ResearchReport:
    from agents import Runner  # local import to avoid circulars in some test setups
    res = Runner.run_sync(agent, input=_build_prompt(topic, subtopics, summaries, sources))
    out: WriterOutput = res.final_output_as(WriterOutput)
    # Citations are extracted and validated in ResearchManager._write_report post-processing
    # WriterOutput may have citations as strings or empty; they'll be replaced with numeric IDs
    fixed_sections: List[Section] = []
    for sec in out.sections:
        # Convert any string citations to empty list (will be populated by post-processing)
        # Or if WriterOutput already has numeric IDs, keep them
        citation_ids: List[int] = []
        if sec.citations:
            for c in sec.citations:
                try:
                    # Try to parse as int (if already numeric)
                    citation_ids.append(int(c))
                except (ValueError, TypeError):
                    # If it's a string/URL, ignore it (post-processing will extract from text)
                    pass
        fixed_sections.append(Section(
            title=sec.title,
            summary=sec.summary,
            citations=citation_ids,  # List[int]
        ))
    return ResearchReport(
        topic=topic, 
        outline=out.outline or [],
        sections=fixed_sections, 
        sources=sources, 
        notes=out.notes or []
    )
