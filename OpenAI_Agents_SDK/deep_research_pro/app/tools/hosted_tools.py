from __future__ import annotations
from typing import List, Dict, Callable, Optional, Coroutine, Any

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
            model="gpt-4o-mini",
            # Ensure the tool is actually invoked
            model_settings=ModelSettings(tool_choice="required"),
            output_type=SearchOutput,
        )
    return _HOSTED_AGENT

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
    
    return (summary, out)

def get_search_provider_async(name: str = "hosted", debug: bool = False) -> Callable[[str], Coroutine[Any, Any, tuple[str, List[Dict]]]]:
    """Factory: returns async hosted search provider."""
    if name.lower() == "hosted":
        return _hosted_web_search_async
    raise ValueError(f"Unknown provider: {name}. Only 'hosted' is supported.")
