from __future__ import annotations
from typing import Optional
from agents import Agent, Runner, ModelSettings
from openai import AsyncOpenAI

from app.schemas.source import SourceItem
from app.core.safe import safe_run_async


class SearchAgent:
    """Summarizes individual search results into detailed analytical summaries."""
    def __init__(self, model: str = "gpt-4o", openai_client: Optional[AsyncOpenAI] = None):
        if openai_client:
            # SDK reads from environment
            pass
        self.agent = Agent(
            name="SearchResultSummarizer",
            instructions=(
                "You are a research assistant that summarizes individual search results in great detail.\n"
                "You will receive the title, URL, and snippet of a single result from a web search.\n\n"
                "Your job is to expand the snippet into a richer, analytical summary that will be fed into a later synthesis step.\n"
                "For each result:\n"
                "- Pull out concrete facts, names, dates, figures, specific claims, and any other relevant information.\n"
                "- Explain what this source adds that might be different from other sources (if visible from the snippet).\n"
                "- Discuss any obvious angle: background, current data, trend, case study, risk, recommendations, etc.\n"
                "- Do NOT hallucinate content that is not clearly implied by the snippet.\n"
                "- Always output:\n"
                "  1) One detailed paragraph (8-12 sentences) covering all the information in the snippet.\n"
                "  2) Then a markdown bullet list of 5–10 'Key points', each focusing on a single concrete fact or claim.\n"
                "- Do NOT hallucinate content that is not clearly implied by the snippet.\n"
                "Return plain text using markdown bullets for the key points, no headings.\n"
                    ),
            model=model,
            model_settings=ModelSettings(temperature=0.3, max_output_tokens=5000),
        )

    async def summarize_result_async(self, source_item: SourceItem) -> str:
        """Summarize a single search result into detailed analytical summary."""
        prompt = (
            f"Title: {source_item.title}\n"
            f"URL: {source_item.url}\n"
            f"Snippet: {source_item.snippet}\n\n"
            "Write:\n"
            "  1) One detailed paragraph (8-12 sentences) covering all the information in the snippet.\n"
            "  2) Then a markdown bullet list of 5–10 'Key points' depending on the information in the snippet, each focusing on a single concrete fact or claim.\n"
            "- Do NOT hallucinate content that is not clearly implied by the snippet.\n"
            "Return plain text using markdown bullets for the key points, no headings.\n"
        )
        result = await safe_run_async(self.agent, prompt, str)
        return result.strip() if result else ""
