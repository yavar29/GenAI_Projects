from __future__ import annotations
from typing import List, Optional
import os
from agents import Agent, Runner, ModelSettings
from app.schemas.plan import ResearchPlan
from openai import AsyncOpenAI

HOW_MANY_SEARCHES = 5

class PlannerAgent:
    """
    Research planner with two modes:
    - Heuristic (default): Fast, free, predictable planning
    - SDK (optional): LLM-powered, adaptive planning
    """
    def __init__(self, use_sdk: bool = False, model: str = "gpt-4o-mini", openai_client: Optional[AsyncOpenAI] = None):
        self.use_sdk = use_sdk
        # If client provided, ensure it's available to the SDK via environment
        if openai_client:
            # The SDK reads from environment, so we ensure the API key is set
            # The client itself will be used by the SDK internally
            pass
        if use_sdk:
            self.agent = Agent(
                name="Planner",
                instructions=(
                    "Create a strategic research plan for the given topic:\n"
                    "- 3–5 subtopics covering key aspects\n"
                    "- 6–10 high-coverage search queries (diverse domains: gov, edu, news, academic)\n"
                    "- Include constraints for source quality and recency\n"
                    "- Return strictly the JSON payload matching ResearchPlan."
                ),
                model=model,
                model_settings=ModelSettings(temperature=0.2),
                output_type=ResearchPlan,
            )
        else:
            self.agent = None

    def plan(self, topic: str) -> ResearchPlan:
        """Sync planning - uses heuristic by default, SDK if use_sdk=True."""
        if self.use_sdk:
            result = Runner.run_sync(self.agent, f"Topic: {topic}")
            return result.final_output_as(ResearchPlan)
        return self._plan_heuristic(topic)

    async def plan_async(self, topic: str) -> ResearchPlan:
        """Async planning - uses SDK if use_sdk=True, otherwise heuristic."""
        if self.use_sdk:
            result = await Runner.run(self.agent, f"Topic: {topic}")
            return result.final_output_as(ResearchPlan)
        return self._plan_heuristic(topic)

    def _plan_heuristic(self, topic: str) -> ResearchPlan:
        """Heuristic-based planning (fast, free, predictable)."""
        topic = topic.strip()
        # Simple subtopic expansion (can be LLM-powered later)
        subtopics: List[str] = [
            f"{topic} — background",
            f"{topic} — recent developments",
            f"{topic} — key players",
            f"{topic} — risks & challenges",
        ][:4]

        # Derive concrete queries from subtopics
        queries: List[str] = []
        for s in subtopics:
            base = s.replace(" — ", " ")
            queries.extend([
                f"{base} 2024 site:reputable news",
                f"{base} report pdf",
            ])
        # De-duplicate while preserving order
        seen = set()
        queries = [q for q in queries if not (q in seen or seen.add(q))]
        
        # Limit to HOW_MANY_SEARCHES (matching old deep_research behavior)
        queries = queries[:HOW_MANY_SEARCHES]

        constraints = [
            "Prefer reputable sources with clear authorship",
            "Collect publication date when available",
        ]

        return ResearchPlan(topic=topic, subtopics=subtopics, queries=queries, constraints=constraints)
