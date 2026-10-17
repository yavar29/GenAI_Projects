from __future__ import annotations
from difflib import SequenceMatcher
from typing import List, Dict, Callable, Optional, Coroutine, Any, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, Field
from agents import Agent, Runner, WebSearchTool, ModelSettings

# -----------------------------
# Hosted provider (OpenAI WebSearchTool) – structured output
# -----------------------------

class RawSource(BaseModel):
    title: str
    # IMPORTANT: use plain str (NOT HttpUrl) to avoid 'uri' format errors in schema
    url: str
    snippet: str = ""
    published: Optional[str] = None

class SearchOutput(BaseModel):
    """Structured output from hosted search agent."""
    summary: str = Field(
        description="2–3 paragraph concise summary of results (<=300 words)."
    )
    results: List[RawSource] = Field(
        default_factory=list,
        description="Structured list of sources found by the search."
    )

_HOSTED_AGENT: Optional[Agent] = None

def _get_hosted_agent() -> Agent:
    """Get singleton Agent instance using WebSearchTool with structured SearchOutput."""
    global _HOSTED_AGENT
    if _HOSTED_AGENT is None:
        _HOSTED_AGENT = Agent(
            name="HostedWebSearcher",
            instructions=(
                "You are a research assistant. Given a search term, you search the web for that term and "
                "produce a concise summary of the results. The summary must be 2-3 paragraphs and less than 300 "
                "words. Capture the main points. Write succinctly, no need to have complete sentences or good "
                "grammar. This will be consumed by someone synthesizing a report, so it's vital you capture the "
                "essence and ignore any fluff. Do not include any additional commentary other than the summary itself.\n\n"
                "Always return a structured JSON matching SearchOutput with:\n"
                " - summary: 2–3 paragraphs, <=300 words, concise, capture main points, no fluff\n"
                " - results: a list of objects {title, url, snippet, published}\n"
                "If a field is missing (e.g., published), leave it null."
            ),
            tools=[WebSearchTool(search_context_size="low")],
            model="gpt-4o",
            # Ensure the tool is actually invoked
            model_settings=ModelSettings(tool_choice="required"),
            output_type=SearchOutput,
        )
    return _HOSTED_AGENT

def _clean_url(url: str) -> str:
    """Strip the utm_source=openai tracking parameter the web search tool appends."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "utm_source"]
    return urlunsplit(parts._replace(query=urlencode(query)))

def _is_abbreviated(text: str) -> bool:
    return "..." in text or "…" in text

def is_valid_source_url(url: str) -> bool:
    """A real, complete http(s) link (not a placeholder or a URL the model shortened with '...')."""
    url = (url or "").strip()
    parts = urlsplit(url)
    return parts.scheme in ("http", "https") and "." in parts.netloc and not _is_abbreviated(url)

def _extract_citations(result) -> List[Tuple[str, str]]:
    """Collect (title, url) pairs from the url_citation annotations of the raw model responses.

    These come from the web search tool itself, so unlike the URLs the model writes into its
    JSON output they are always real links.
    """
    citations: List[Tuple[str, str]] = []
    for response in getattr(result, "raw_responses", []) or []:
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                for ann in getattr(content, "annotations", []) or []:
                    if getattr(ann, "type", "") == "url_citation" and is_valid_source_url(getattr(ann, "url", "")):
                        citations.append((getattr(ann, "title", "") or "", ann.url))
    return citations

def _resolve_result_urls(results: List[Dict], citations: List[Tuple[str, str]]) -> List[Dict]:
    """Give every result a real URL, or drop it.

    The model sometimes fills `url` with placeholders ('', 'source', 'arXiv') or shortens
    it with '...'. Those are replaced by the best title match among the tool's citations;
    results that cannot be matched are dropped, since a source without a verifiable link
    should not be cited. Titles the model abbreviated are replaced by the citation's title.
    """
    by_url = {_clean_url(u): t for t, u in citations}
    unused = list(citations)
    resolved = []
    for r in results:
        url = r.get("url") or ""
        title = r.get("title") or ""
        if not is_valid_source_url(url):
            best, best_score = None, 0.0
            for cand in unused:
                score = SequenceMatcher(None, title.lower(), cand[0].lower()).ratio()
                if score > best_score:
                    best, best_score = cand, score
            if best is None or best_score < 0.6:
                continue
            unused.remove(best)
            url = best[1]
        url = _clean_url(url)
        if _is_abbreviated(title) and by_url.get(url):
            title = by_url[url]
        resolved.append({**r, "url": url, "title": title})
    return resolved

async def _hosted_web_search_async(query: str) -> tuple[str, List[Dict]]:
    """Run hosted web search agent and return (summary, results)."""
    agent = _get_hosted_agent()
    result = await Runner.run(agent, input=query)
    payload = result.final_output_as(SearchOutput)

    # Preserve the summary
    summary = (payload.summary or "").strip()

    # Extract results
    out: List[Dict] = []
    for r in payload.results:
        out.append({
            "title": (r.title or "").strip(),
            "url": r.url,            # already a str
            "snippet": (r.snippet or "").strip(),
            "published": r.published,
            "provider": "openai",
        })

    return (summary, _resolve_result_urls(out, _extract_citations(result)))

def get_search_provider_async(name: str = "hosted", debug: bool = False) -> Callable[[str], Coroutine[Any, Any, tuple[str, List[Dict]]]]:
    """Factory: returns async hosted search provider."""
    if name.lower() == "hosted":
        return _hosted_web_search_async
    raise ValueError(f"Unknown provider: {name}. Only 'hosted' is supported.")
