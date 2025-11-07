from __future__ import annotations
import argparse
from pathlib import Path
from rich import print

from app.core.settings import PROJECT_NAME, OPENAI_API_KEY, DB_PATH
from app.core.sessions import get_session
from app.core.tracing import enable_tracing
from app.tools.hosted_tools import get_search_provider

from app.agents.planner_agent import PlannerAgent
from app.agents.search_agent import SearchAgent
from app.agents.writer_agent import WriterAgent
from app.agents.verifier_agent import VerifierAgent
from app.schemas.verify import VerificationOutput

# --- Score explainer (mirrors verifier's domain weights) ---
_DOMAIN_WEIGHTS = {
    "gov": 1.0, "europa.eu": 1.0, "who.int": 1.0, "oecd.org": 1.0,
    "jamanetwork.com": 1.0, "nejm.org": 1.0, "nature.com": 1.0, "reuters.com": 1.0,
    "ft.com": 0.8, "apnews.com": 0.8, "bbc.com": 0.8, "nytimes.com": 0.8, "economist.com": 0.8,
}

def _domain_weight(url: str) -> float:
    u = (url or "").lower()
    for dom, w in _DOMAIN_WEIGHTS.items():
        if dom in u:
            return w
    if u.endswith(".gov") or ".gov/" in u:
        return 1.0
    if u.endswith(".edu") or ".edu/" in u:
        return 0.85
    return 0.4

def _domain_from_url(url: str) -> str:
    # tiny domain extractor good enough for display (no extra deps)
    try:
        without_scheme = url.split("://", 1)[-1]
        host = without_scheme.split("/", 1)[0]
        return host.lower()
    except Exception:
        return url

def _score_explainer(urls: list[str]) -> tuple[list[str], list[str]]:
    """Return two lists: boosts (>=0.8) and drags (<=0.5) by domain, deduped."""
    boosts, drags = [], []
    seen = set()
    for u in urls or []:
        dom = _domain_from_url(u)
        if dom in seen:
            continue
        seen.add(dom)
        w = _domain_weight(u)
        if w >= 0.8:
            boosts.append(dom)
        elif w <= 0.5:
            drags.append(dom)
    return boosts, drags


def _render_markdown(report, verification: VerificationOutput | None) -> str:
    lines = [f"# {report.topic}", ""]

    # Collect unique references across all sections
    ref_map: dict[str, int] = {}
    for sec in report.sections:
        for u in sec.citations:
            if u and u not in ref_map:
                ref_map[u] = len(ref_map) + 1

    # Sections with numbered inline citations
    for i, sec in enumerate(report.sections, 1):
        lines.append(f"## {i}. {sec.title}")
        lines.append(sec.summary.strip())
        if sec.citations:
            nums = [str(ref_map[u]) for u in sec.citations if u in ref_map]
            if nums:
                lines.append("**Citations:** " + ", ".join(f"[{n}]" for n in nums))
        lines.append("")

    # Notes
    if report.notes:
        lines.append("## Notes")
        for n in report.notes:
            lines.append(f"- {n}")
        lines.append("")

    # Verification
    if verification:
        lines.append("## Verification")
        lines.append(f"**Overall confidence:** {verification.overall_confidence:.2f}")
        lines.append("")
        for j, r in enumerate(verification.reviews, 1):
            lines.append(f"### {j}. {r.section_title}")
            lines.append(f"- **Confidence:** {r.confidence:.2f}")
            lines.append(f"- **Reasoning:** {r.reasoning}")
            if r.issues:
                lines.append("- **Issues:**")
                for issue in r.issues:
                    lines.append(f"  - {issue}")
            # map cited_urls to reference numbers if present
            if r.cited_urls:
                ref_nums = [str(ref_map[u]) for u in r.cited_urls if u in ref_map]
                if ref_nums:
                    lines.append(f"- **Checked citations:** " + ", ".join(f"[{n}]" for n in ref_nums))

            # print strict-verify metrics when available
            if getattr(r, "metrics", None):
                lines.append(
                    f"- **Metrics:** "
                    f"llm={r.metrics.llm_conf:.2f}, "
                    f"coverage={r.metrics.coverage:.2f}, "
                    f"quality={r.metrics.quality:.2f}, "
                    f"recency={r.metrics.recency:.2f}, "
                    f"**final={r.metrics.final:.2f}**"
                )
                # Why this score?' explainer using source domains
                boosts, drags = _score_explainer(r.cited_urls or [])
                parts = []
                if boosts:
                    parts.append("+" + ", +".join(boosts[:4]) + ("…" if len(boosts) > 4 else ""))
                if drags:
                    parts.append("−" + ", −".join(drags[:4]) + ("…" if len(drags) > 4 else ""))
                if parts:
                    lines.append(f"- **Why this score?** " + " · ".join(parts))

            
            lines.append("")

    # References (angle brackets prevent weird wrapping)
    if ref_map:
        lines.append("## References")
        for url, idx in sorted(ref_map.items(), key=lambda kv: kv[1]):
            lines.append(f"[{idx}] <{url}>")
        lines.append("")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Deep Research Pro — Iteration 3 (Verifier)")
    parser.add_argument("--topic", type=str, default="AI in healthcare", help="Research topic")
    parser.add_argument("--n", type=int, default=8, help="Max sources to return")
    parser.add_argument("--provider", type=str, choices=["stub", "hosted"], default="stub", help="Search provider to use")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification step")
    parser.add_argument("--strict-verify", action="store_true", help="Blend LLM confidence with coverage/quality/recency metrics")
    parser.add_argument("--save", type=str, default="", help="Optional path to save Markdown report")
    args = parser.parse_args()

    print(f"[bold cyan]{PROJECT_NAME}[/bold cyan] • Iteration 3 (Planner + Search + Writer + Verifier: {args.provider})")
    print(":key: OPENAI_API_KEY detected" if OPENAI_API_KEY else ":warning: OPENAI_API_KEY not set (ok for stub)")

    enable_tracing()
    session = get_session(DB_PATH)
    web_search = get_search_provider(args.provider)

    # 1) Plan
    plan = PlannerAgent().plan(args.topic)

    # 2) Search
    searcher = SearchAgent(search_func=web_search)
    sources = searcher.search_many(plan.queries, limit_total=args.n)

    # 3) Write
    writer = WriterAgent()
    report = writer.draft(plan.topic, plan.subtopics, sources)

    # 4) Verify (optional)
    verification = None
    if not args.no_verify:
        # Use tools only when provider is hosted (so verifier can re-check selectively)
        use_tools = (args.provider == "hosted")
        #verifier = VerifierAgent(use_tools=use_tools)
        verifier = VerifierAgent(use_tools=use_tools, strict=args.strict_verify)
        verification = verifier.verify(report)

    # 5) Render Markdown
    md = _render_markdown(report, verification)
    print(md)

    # 6) Optional save
    if args.save:
        out_path = Path(args.save)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"\n[green]Saved report → {out_path}[/green]")

if __name__ == "__main__":
    main()
