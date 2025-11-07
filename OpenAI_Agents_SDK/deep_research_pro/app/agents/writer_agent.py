from __future__ import annotations
from typing import List
from agents import Agent, Runner, ModelSettings
from pydantic import BaseModel, Field
from app.schemas.source import SourceDoc
from app.schemas.report import ResearchReport, Section

def _clean_url(u: str) -> str:
    # remove any accidental whitespace/newlines that break links
    return (u or "").replace("\n", "").replace(" ", "").strip()

# Typed output the Writer agent should produce
class WriterOutput(BaseModel):
    sections: List[Section] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

# A small helper to pick a few URLs per section
def _pick_citations(sources: List[SourceDoc], k: int = 3) -> List[str]:
    urls = []
    for s in sources:
        u = str(s.url)
        if u and u not in urls:
            urls.append(u)
        if len(urls) >= k:
            break
    return urls

class WriterAgent:
    """
    Turns topic + subtopics + sources into a structured ResearchReport with sections and citations.
    Uses an Agent with typed output to keep JSON consistent.
    """
    def __init__(self, model: str = "gpt-4o-mini"):
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
            model_settings=ModelSettings(temperature=0.2),
            output_type=WriterOutput,
        )

    def draft(self, topic: str, subtopics: List[str], sources: List[SourceDoc]) -> ResearchReport:
        prompt = (
            f"Topic: {topic}\n\n"
            f"Subtopics: {subtopics}\n\n"
            "You have these normalized sources (title, url, snippet, published):\n"
        )
        for s in sources:
            prompt += f"- {s.title} | {s.url} | {s.published or ''} | {s.snippet[:160]}\n"

        # Ask model to propose sensible section titles using the subtopics as hints
        prompt += (
            "\nCreate 3–5 sections named from this pool when appropriate: "
            "[Background, Timeline, Key Players, Risks & Compliance, Outlook]. "
            "Citations must be a subset of the provided URLs. "
            "Add 2–4 citations per section. "
            "Also include a short 'notes' list with 1–3 limitations."
        )

        res = Runner.run_sync(self.agent, prompt)
        out: WriterOutput = res.final_output_as(WriterOutput)

        # Backstop: if any section lacks citations, attach a few top URLs
        fixed_sections: List[Section] = []
        for sec in out.sections:
            if not sec.citations:
                sec.citations = _pick_citations(sources, k=3)
            sec.citations = [_clean_url(c) for c in sec.citations if _clean_url(c)]
            fixed_sections.append(sec)

        return ResearchReport(
            topic=topic,
            sections=fixed_sections,
            sources=sources,
            notes=out.notes or []
        )
