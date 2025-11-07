from __future__ import annotations
from typing import List, Optional, Dict
from datetime import datetime

from agents import Agent, Runner, ModelSettings, WebSearchTool
from pydantic import BaseModel, Field, conlist
from app.schemas.report import ResearchReport, Section
from app.schemas.verify import VerificationOutput, SectionReview, SectionMetrics

def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

# ----------------------------
# Lightweight claim extractor
# ----------------------------
class ClaimsOutput(BaseModel):
    claims: conlist(str, min_length=1, max_length=5) = Field(..., description="Up to 5 short, verifiable claims.")

def _build_claims_agent(model: str = "gpt-4o-mini") -> Agent:
    return Agent(
        name="ClaimExtractor",
        instructions=(
            "Read the given section text and extract up to 5 concise, verifiable claims as short sentences. "
            "No numbering, no commentary—just the claims. Keep each under 20 words."
        ),
        model=model,
        model_settings=ModelSettings(temperature=0.0),
        output_type=ClaimsOutput,
    )

# ----------------------------
# Helpers for strict metrics
# ----------------------------
_DOMAIN_WEIGHTS: Dict[str, float] = {
    # high trust
    "gov": 1.0, "europa.eu": 1.0, "who.int": 1.0, "oecd.org": 1.0,
    "jamanetwork.com": 1.0, "nejm.org": 1.0, "nature.com": 1.0, "reuters.com": 1.0,
    # decent news
    "ft.com": 0.8, "apnews.com": 0.8, "bbc.com": 0.8, "nytimes.com": 0.8, "economist.com": 0.8,
}

def _domain_weight(url: str) -> float:
    u = (url or "").lower()
    for dom, w in _DOMAIN_WEIGHTS.items():
        if dom in u:
            return w
    # quick tld heuristic
    if u.endswith(".gov") or ".gov/" in u:
        return 1.0
    if u.endswith(".edu") or ".edu/" in u:
        return 0.85
    return 0.4  # default/unknown

def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m", "%Y"):
        try:
            return datetime.strptime(s[:len(fmt)], fmt)
        except Exception:
            continue
    return None

def _recency_score(published_strs: List[Optional[str]]) -> float:
    # If any recent source is present, score well.
    now = datetime.utcnow()
    best = 0.4  # default floor
    for s in published_strs:
        dt = _parse_date(s)
        if not dt:
            continue
        days = (now - dt).days
        if days <= 180:
            best = max(best, 1.0)
        elif days <= 365:
            best = max(best, 0.8)
        elif days <= 720:
            best = max(best, 0.6)
        else:
            best = max(best, 0.4)
    # if no dates at all, use neutral-ish 0.6
    if best == 0.4 and all(p is None for p in published_strs):
        return 0.6
    return best

def _coverage_score(claims: List[str], citations_count: int) -> float:
    # Simple proxy: if you have >= as many citations as claims, coverage=1; else proportion.
    if not claims:
        return 0.6  # neutral default if extraction failed
    return _clamp(citations_count / float(len(claims)))

def _quality_score(urls: List[str]) -> float:
    if not urls:
        return 0.3
    weights = [_domain_weight(u) for u in urls]
    return sum(weights) / len(weights)

# ----------------------------
# Verifier Agent (LLM)
# ----------------------------
class VerifierAgent:
    """
    Checks each section and returns typed confidence reviews.
    If use_tools=True, the agent may call WebSearchTool to sanity-check citations.
    If strict=True, blends LLM confidence with rule-based metrics.
    """
    def __init__(self, model: str = "gpt-4o-mini", use_tools: bool = False, strict: bool = False):
        tools = [WebSearchTool(search_context_size="low")] if use_tools else []
        tool_choice = "auto" if use_tools else "none"

        self.agent = Agent(
            name="Verifier",
            instructions=(
                "You are a meticulous research verifier. Given a topic and a multi-section brief "
                "with citations, evaluate each section for factual soundness and evidence quality. "
                "For each section, provide a confidence score in [0,1], a short reasoning, and a "
                "list of concrete issues if any (e.g., weak evidence, outdated link, claim not supported). "
                "Use citations from the section and (if tools available) perform lightweight checks. "
                "Return ONLY the JSON matching the output schema."
            ),
            model=model,
            tools=tools,
            model_settings=ModelSettings(temperature=0.0, tool_choice=tool_choice),
            output_type=VerificationOutput,
        )
        self.strict = strict
        self.claims_agent = _build_claims_agent(model=model) if strict else None

    def verify(self, report: ResearchReport) -> VerificationOutput:
        # 1) LLM verification
        prompt = [f"Topic: {report.topic}\n"]
        for i, sec in enumerate(report.sections, 1):
            prompt.append(f"Section {i}: {sec.title}\nSummary:\n{sec.summary.strip()}\nCitations:")
            if sec.citations:
                for u in sec.citations:
                    prompt.append(f"- {u}")
            else:
                prompt.append("- (none)")
            prompt.append("")  # blank line

        prompt.append(
            "Evaluate each section. Score confidence in [0,1]. If evidence is weak, list issues. "
            "Set 'cited_urls' to the subset of provided URLs you actually relied on. "
            "Finally, provide an overall_confidence and a brief methodology."
        )

        result = Runner.run_sync(self.agent, "\n".join(prompt))
        out = result.final_output_as(VerificationOutput)

        # 2) Clamp LLM scores
        out.overall_confidence = _clamp(float(out.overall_confidence))
        for r in out.reviews:
            r.confidence = _clamp(float(r.confidence))

        # 3) Strict metrics blending (optional)
        if self.strict:
            # Build URL -> published map from report sources for recency
            url_to_pub: Dict[str, Optional[str]] = {}
            for s in report.sources:
                url_to_pub[str(s.url)] = s.published if getattr(s, "published", None) else None

            new_confs = []
            for idx, (sec, r) in enumerate(zip(report.sections, out.reviews), start=1):
                # Claims extraction (LLM, low-temp)
                text = f"Section: {sec.title}\n{sec.summary.strip()}"
                try:
                    claims_res = Runner.run_sync(self.claims_agent, text)
                    claims = claims_res.final_output_as(ClaimsOutput).claims
                except Exception:
                    claims = []

                coverage = _coverage_score(claims, len(sec.citations))
                quality = _quality_score(sec.citations)
                recency = _recency_score([url_to_pub.get(u) for u in sec.citations])

                llm_conf = float(r.confidence)
                final = _clamp(0.5 * llm_conf + 0.25 * coverage + 0.15 * quality + 0.10 * recency)

                r.metrics = SectionMetrics(
                    llm_conf=_clamp(llm_conf),
                    coverage=_clamp(coverage),
                    quality=_clamp(quality),
                    recency=_clamp(recency),
                    final=_clamp(final),
                )
                # overwrite displayed confidence with blended final
                r.confidence = r.metrics.final
                new_confs.append(r.confidence)

            # Recompute overall as mean of finals
            if new_confs:
                out.overall_confidence = _clamp(sum(new_confs) / len(new_confs))

        return out
