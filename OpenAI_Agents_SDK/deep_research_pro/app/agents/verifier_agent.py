from __future__ import annotations
from typing import List, Optional, Dict
from datetime import datetime, timezone
from agents import Runner
from agents import Agent, ModelSettings, WebSearchTool
from pydantic import BaseModel, Field, conlist
from openai import AsyncOpenAI
from app.schemas.report import ResearchReport, Section
from app.schemas.verify import VerificationOutput, SectionReview, SectionMetrics
from app.core.safe import safe_run, safe_run_async
from app.core.text import keyword_set, overlap_count
from urllib.parse import urlparse


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
    """
    Robustly parse many date formats:
    - Plain ISO like '2025-02-17'
    - Reuters-style or other URLs containing a date fragment

    Returns UTC-aware datetime or None.
    """
    if not s:
        return None

    s = str(s).strip()

    # 1) Quick-path: direct ISO(ish) strings
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m", "%Y"):
        try:
            dt = datetime.strptime(s[:len(fmt)], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    # 2) Try to extract yyyy-mm-dd from inside a URL or free text
    # e.g., https://www.reuters.com/.../2025-02-17/
    import re
    m = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", s)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    return None


def _hostname(u: str) -> str:
    try:
        return urlparse(u).hostname or ""
    except Exception:
        return ""

def _diversity_bonus(urls: List[str]) -> float:
    """
    Reward corroboration: small boost for multiple distinct reputable domains in a section's citations.
    - 2 distinct domains: +0.02
    - 3+ distinct domains: +0.03
    (Always clamped at the end.)
    """
    hosts = {_hostname(u).lower() for u in urls if u}
    # Only consider "real" hosts (filter out blanks)
    hosts = {h for h in hosts if h}
    if len(hosts) >= 3:
        return 0.03
    if len(hosts) >= 2:
        return 0.02
    return 0.0


def _recency_score(published_strs: List[Optional[str]]) -> float:
    """
    Score recency using the most recent parsed date:
      - <= 180 days: 1.00
      - <= 365 days: 0.80
      - <= 720 days: 0.60
      - older/unknown: 0.40
    If NO dates at all appear, return a neutral 0.60 (we don't want to punish undated but valid sources).
    """
    now = datetime.now(timezone.utc)
    best = 0.0
    any_seen = False

    for s in published_strs:
        dt = _parse_date(s)
        if not dt:
            continue
        any_seen = True
        days = (now - dt).days
        if days <= 180:
            best = max(best, 1.0)
        elif days <= 365:
            best = max(best, 0.8)
        elif days <= 720:
            best = max(best, 0.6)
        else:
            best = max(best, 0.4)

    if not any_seen:
        return 0.6  # neutral default if no dates supplied
    return best

def _claim_coverage_ratio(
    claims: list[str],
    cited_urls: list[str],
    url_to_title_snippet: dict[str, tuple[str, str]],
    min_overlap: int = 2,
) -> float:
    """
    A claim is 'covered' if ANY cited URL's title/snippet overlaps the claim by >= min_overlap keywords.
    """
    if not claims:
        return 0.6  # neutral if extraction failed
    covered = 0
    for c in claims:
        ck = keyword_set(c)
        if not ck:
            continue
        supported = False
        for u in cited_urls:
            title, snip = url_to_title_snippet.get(u, ("", ""))
            tk = keyword_set(title) | keyword_set(snip)
            if overlap_count(ck, tk) >= min_overlap:
                supported = True
                break
        if supported:
            covered += 1
    return covered / float(len(claims))

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
    def __init__(self, model: str = "gpt-4o-mini", use_tools: bool = False, strict: bool = False, openai_client: Optional[AsyncOpenAI] = None):
        # If client provided, ensure it's available to the SDK via environment
        if openai_client:
            # The SDK reads from environment, so we ensure the API key is set
            # The client itself will be used by the SDK internally
            pass
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

    def _apply_strict_metrics(self, report: ResearchReport, out: VerificationOutput) -> None:
        """Apply strict metrics blending to verification output."""
        if not self.strict:
            return
        
        # Build maps from report.sources for both recency and title/snippet
        url_to_pub: Dict[str, Optional[str]] = {}
        url_to_title_snip: Dict[str, tuple[str, str]] = {}
        
        for s in report.sources:
            url = str(s.url)
            url_to_pub[url] = s.published if getattr(s, "published", None) else None
            # make sure title/snippet are strings
            title = getattr(s, "title", "") or ""
            snip = getattr(s, "snippet", "") or ""
            url_to_title_snip[url] = (title, snip)

        new_confs = []
        for idx, (sec, r) in enumerate(zip(report.sections, out.reviews), start=1):
            # Claims extraction (LLM, low-temp)
            text = f"Section: {sec.title}\n{sec.summary.strip()}"
            claims = safe_run(self.claims_agent, text, ClaimsOutput).claims if self.claims_agent else []

            coverage = _claim_coverage_ratio(
                claims=claims,
                cited_urls=sec.citations,
                url_to_title_snippet=url_to_title_snip,
                min_overlap=2,
            )
            quality = _quality_score(sec.citations)
            recency = _recency_score([url_to_pub.get(u) for u in sec.citations])

            llm_conf = float(r.confidence)
            final = _clamp(0.5 * llm_conf + 0.25 * coverage + 0.15 * quality + 0.10 * recency)
            # Diversity bonus (tiny nudge for corroboration across sources)
            final = _clamp(final + _diversity_bonus(sec.citations))
            
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

    async def _apply_strict_metrics_async(self, report: ResearchReport, out: VerificationOutput) -> None:
        """Apply strict metrics blending to verification output (async version)."""
        if not self.strict:
            return
        
        # Build maps from report.sources for both recency and title/snippet
        url_to_pub: Dict[str, Optional[str]] = {}
        url_to_title_snip: Dict[str, tuple[str, str]] = {}
        
        for s in report.sources:
            url = str(s.url)
            url_to_pub[url] = s.published if getattr(s, "published", None) else None
            # make sure title/snippet are strings
            title = getattr(s, "title", "") or ""
            snip = getattr(s, "snippet", "") or ""
            url_to_title_snip[url] = (title, snip)

        new_confs = []
        for idx, (sec, r) in enumerate(zip(report.sections, out.reviews), start=1):
            # Claims extraction (LLM, low-temp) - async version
            text = f"Section: {sec.title}\n{sec.summary.strip()}"
            claims = []
            if self.claims_agent:
                try:
                    claims_output = await safe_run_async(self.claims_agent, text, ClaimsOutput)
                    claims = claims_output.claims
                except Exception:
                    claims = []

            coverage = _claim_coverage_ratio(
                claims=claims,
                cited_urls=sec.citations,
                url_to_title_snippet=url_to_title_snip,
                min_overlap=2,
            )
            quality = _quality_score(sec.citations)
            recency = _recency_score([url_to_pub.get(u) for u in sec.citations])

            llm_conf = float(r.confidence)
            final = _clamp(0.5 * llm_conf + 0.25 * coverage + 0.15 * quality + 0.10 * recency)
            # Diversity bonus (tiny nudge for corroboration across sources)
            final = _clamp(final + _diversity_bonus(sec.citations))
            
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

        #result = Runner.run_sync(self.agent, "\n".join(prompt))
        #out = result.final_output_as(VerificationOutput)
        out: VerificationOutput = safe_run(self.agent, "\n".join(prompt), VerificationOutput)

        

        # 2) Clamp LLM scores
        out.overall_confidence = _clamp(float(out.overall_confidence))
        for r in out.reviews:
            r.confidence = _clamp(float(r.confidence))

        # 3) Strict metrics blending (optional)
        self._apply_strict_metrics(report, out)

        return out

    async def verify_async(self, report: ResearchReport) -> VerificationOutput:
        """Async version of verify method."""
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

        out = await safe_run_async(self.agent, "\n".join(prompt), VerificationOutput)

        # 2) Clamp LLM scores
        out.overall_confidence = _clamp(float(out.overall_confidence))
        for r in out.reviews:
            r.confidence = _clamp(float(r.confidence))

        # 3) Strict metrics blending (optional)
        await self._apply_strict_metrics_async(report, out)

        return out
