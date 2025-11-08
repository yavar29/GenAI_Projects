from __future__ import annotations
from typing import Any, List, Dict, Callable, Optional

from pydantic import BaseModel, Field
from agents import Agent, Runner, WebSearchTool, ModelSettings

# -----------------------------
# Stub provider (no network)
# -----------------------------
def _stub_web_search(query: str) -> List[Dict]:
    base = query.replace(" ", "+")
    return [
        {
            "title": f"Overview: {query[:48]}",
            "url": f"https://example.com/search?q={base}",
            "snippet": "Stubbed snippet for demonstration.",
            "published": None,
            "provider": "stub",
        },
        {
            "title": f"Deep dive: {query[:48]}",
            "url": f"https://example.org/article?q={base}",
            "snippet": "Another stubbed result.",
            "published": None,
            "provider": "stub",
        },
    ]

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
    """What the hosted search agent should return."""
    summary: str = Field(
        description="2–3 paragraph concise summary of results (<=300 words)."
    )
    results: List[RawSource] = Field(
        default_factory=list,
        description="Structured list of sources found by the search."
    )

_HOSTED_AGENT: Optional[Agent] = None

def _get_hosted_agent() -> Agent:
    """
    Memoize a single Agent instance that uses WebSearchTool and
    returns a structured SearchOutput (summary + results[]).
    """
    global _HOSTED_AGENT
    if _HOSTED_AGENT is None:
        _HOSTED_AGENT = Agent(
            name="HostedWebSearcher",
            instructions=(
                "Use WebSearchTool to search for the user's query. "
                "Always return a structured JSON matching SearchOutput with:\n"
                " - summary: 2–3 paragraphs, <=300 words, no fluff\n"
                " - results: a list of objects {title, url, snippet, published}\n"
                "If a field is missing (e.g., published), leave it null."
            ),
            tools=[WebSearchTool(search_context_size="low")],
            model="gpt-4o-mini",
            # Ensure the tool is actually invoked
            model_settings=ModelSettings(tool_choice="required"),
            output_type=SearchOutput,
        )
    return _HOSTED_AGENT

async def _hosted_web_search_async(query: str) -> List[Dict]:
    """
    Run the hosted web search agent (async) and normalize to List[dict].
    Falls back to stub if anything fails.
    """
    try:
        agent = _get_hosted_agent()
        result = await Runner.run(agent, query)
        payload = result.final_output_as(SearchOutput)
        out: List[Dict] = []
        for r in payload.results:
            out.append({
                "title": (r.title or "").strip(),
                "url": r.url,            # already a str
                "snippet": (r.snippet or "").strip(),
                "published": r.published,
                "provider": "openai",
            })
        # If the tool returned no results, still provide something predictable:
        if not out and payload.summary:
            out.append({
                "title": f"Search result for: {query}",
                "url": "https://example.com",
                "snippet": payload.summary[:200],
                "published": None,
                "provider": "openai",
            })
        return out or _stub_web_search(query)
    except Exception:
        return _stub_web_search(query)

def _hosted_web_search(query: str) -> List[Dict]:
    """
    Sync wrapper for hosted web search (for backward compatibility).
    Falls back to stub if anything fails.
    """
    import asyncio
    try:
        return asyncio.run(_hosted_web_search_async(query))
    except Exception:
        return _stub_web_search(query)

def get_hosted_web_search() -> Callable[[str], List[Dict]]:
    """Expose the hosted search provider as a callable(query)->list[dict]."""
    return _hosted_web_search

# -----------------------------
# Public provider selection
# -----------------------------
def get_search_provider(name: str, debug: bool = False) -> Callable[[str], List[Dict]]:
    """
    Factory: "stub" or "hosted" -> callable(query)->list[dict]
    """
    name = (name or "stub").lower()
    if name == "stub":
        return _stub_web_search
    if name == "hosted":
        return get_hosted_web_search()
    raise ValueError(f"Unknown provider: {name}. Must be one of {{'stub','hosted'}}")

# Back-compat for older tests and simple consumers
def load_hosted_tools() -> dict[str, Any]:
    """
    Include a 'web_search' key for tests expecting that name.
    Also expose explicit stub/hosted entries for clarity.
    """
    return {
        "web_search": _stub_web_search,               # test expects this
        "web_search_stub": _stub_web_search,
        "web_search_hosted": get_hosted_web_search(),
    }
