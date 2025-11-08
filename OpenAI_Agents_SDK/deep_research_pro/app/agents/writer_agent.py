from __future__ import annotations
from typing import List, Optional
from pathlib import Path
from agents import Agent, Runner, ModelSettings, function_tool
from pydantic import BaseModel, Field
from openai import AsyncOpenAI

from app.schemas.source import SourceDoc
from app.schemas.report import ResearchReport, Section
from app.core.safe import safe_run_async

def _clean_url(u: str) -> str:
    return (u or "").replace("\n", "").replace(" ", "").strip()

class WriterOutput(BaseModel):
    sections: List[Section] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

def _pick_citations(sources: List[SourceDoc], k: int = 3) -> List[str]:
    urls = []
    for s in sources:
        u = str(s.url)
        if u and u not in urls:
            urls.append(u)
        if len(urls) >= k:
            break
    return urls

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
    def __init__(self, model: str = "gpt-4o-mini", openai_client: Optional[AsyncOpenAI] = None):
        # If client provided, ensure it's available to the SDK via environment
        if openai_client:
            # The SDK reads from environment, so we ensure the API key is set
            # The client itself will be used by the SDK internally
            pass
        self.agent = Agent(
            name="Writer",
            instructions=(
                "You are a precise research writer. Given a topic, subtopics and curated sources, "
                "compose a concise multi-section brief (3–5 sections). "
                "Each section must be 3–5 sentences, factual, and neutral. "
                "DO NOT invent citations—use only the provided sources' URLs. "
                "Return strictly the JSON payload matching WriterOutput."
            ),
            model=model,
            tools=[save_markdown],  # tool available (optional for later steps)
            model_settings=ModelSettings(temperature=0.2),
            output_type=WriterOutput,
        )

    # ---- sync (kept for compatibility) ----
    def draft(self, topic: str, subtopics: List[str], sources: List[SourceDoc]) -> ResearchReport:
        return _draft_core(self.agent, topic, subtopics, sources)

    # ---- async ----
    async def draft_async(self, topic: str, subtopics: List[str], sources: List[SourceDoc]) -> ResearchReport:
        prompt = _build_prompt(topic, subtopics, sources)
        out: WriterOutput = await safe_run_async(self.agent, prompt, WriterOutput)
        fixed_sections: List[Section] = []
        for sec in out.sections:
            if not sec.citations:
                sec.citations = _pick_citations(sources, k=3)
            sec.citations = [_clean_url(c) for c in sec.citations if _clean_url(c)]
            fixed_sections.append(sec)
        return ResearchReport(topic=topic, sections=fixed_sections, sources=sources, notes=out.notes or [])

# --- shared utilities ---
def _build_prompt(topic: str, subtopics: List[str], sources: List[SourceDoc]) -> str:
    prompt = (
        f"Topic: {topic}\n\n"
        f"Subtopics: {subtopics}\n\n"
        "You have these normalized sources (title, url, snippet, published):\n"
    )
    for s in sources:
        prompt += f"- {s.title} | {s.url} | {s.published or ''} | {s.snippet[:160]}\n"
    prompt += (
        "\nCreate 3–5 sections named from this pool when appropriate: "
        "[Background, Timeline, Key Players, Risks & Compliance, Outlook]. "
        "Citations must be a subset of the provided URLs. "
        "Add 2–4 citations per section. "
        "Also include a short 'notes' list with 1–3 limitations."
    )
    return prompt

def _draft_core(agent: Agent, topic: str, subtopics: List[str], sources: List[SourceDoc]) -> ResearchReport:
    from agents import Runner  # local import to avoid circulars in some test setups
    res = Runner.run_sync(agent, _build_prompt(topic, subtopics, sources))
    out: WriterOutput = res.final_output_as(WriterOutput)
    fixed_sections: List[Section] = []
    for sec in out.sections:
        if not sec.citations:
            sec.citations = _pick_citations(sources, k=3)
        sec.citations = [_clean_url(c) for c in sec.citations if _clean_url(c)]
        fixed_sections.append(sec)
    return ResearchReport(topic=topic, sections=fixed_sections, sources=sources, notes=out.notes or [])
