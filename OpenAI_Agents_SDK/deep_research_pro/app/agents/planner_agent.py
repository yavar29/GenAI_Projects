from __future__ import annotations
from typing import List
from app.schemas.plan import ResearchPlan

class PlannerAgent:
    """
    Iteration 1A: simple heuristic planner.
    Expands a topic into subtopics, concrete search queries, and a few constraints.
    """
    def plan(self, topic: str) -> ResearchPlan:
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

        constraints = [
            "Prefer reputable sources with clear authorship",
            "Collect publication date when available",
        ]

        return ResearchPlan(topic=topic, subtopics=subtopics, queries=queries, constraints=constraints)
