from __future__ import annotations
from typing import Optional
from agents import Agent, Runner, ModelSettings
from openai import AsyncOpenAI

from app.schemas.source import SourceItem
from app.core.safe import safe_run_async


class SearchAgent:
    """
    Per-result summarizer agent.
    Takes Title + URL + Snippet and produces a rich, detailed 8-12 sentence analytical summary.
    Uses snippet-based summarization with deep analytical expansion.
    """
    def __init__(self, model: str = "gpt-4o", openai_client: Optional[AsyncOpenAI] = None):
        if openai_client:
            # SDK reads from environment
            pass
        self.agent = Agent(
            name="SearchResultSummarizer",
            instructions=(
                "You are a research assistant that summarizes individual search results.\n"
                "You will receive the title, URL, and snippet of a single result from a web search.\n\n"
                "Your job is to expand the snippet into a richer, analytical summary that will be fed into a later synthesis step.\n"
                "For each result:\n"
                "- Pull out concrete facts, names, dates, figures, and specific claims.\n"
                "- Explain what this source adds that might be different from other sources (if visible from the snippet).\n"
                "- Discuss any obvious angle: background, current data, trend, case study, risk, or recommendation.\n"
                "- If appropriate, you may use a short inline list (e.g., 'Key points: ...') but you do not need to follow a fixed template.\n"
                "- Do NOT hallucinate content that is not clearly implied by the snippet.\n"
                "- Aim for about 8–12 sentences of dense, informative text.\n"
                "Return only the summary text, no headings or formatting.\n"
            ),
            model=model,
            model_settings=ModelSettings(temperature=0.2),
        )

    async def summarize_result_async(self, source_item: SourceItem) -> str:
        """
        Summarize a single search result using snippet-based summarization.
        Returns a rich, detailed 8-12 sentence analytical summary.
        """
        prompt = (
            f"Title: {source_item.title}\n"
            f"URL: {source_item.url}\n"
            f"Snippet: {source_item.snippet}\n\n"
            "Write a detailed, 8–12 sentence analytical summary based ONLY on the snippet and title. "
            "Focus on concrete facts, specific claims, and what this source contributes to understanding the main query."
        )
        
        result = await safe_run_async(self.agent, prompt, str)
        return result.strip() if result else ""
