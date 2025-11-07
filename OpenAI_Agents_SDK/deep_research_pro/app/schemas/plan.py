from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List

class ResearchPlan(BaseModel):
    topic: str = Field(..., description="User-supplied topic")
    subtopics: List[str] = Field(default_factory=list, description="2–6 focused sub-areas")
    queries: List[str] = Field(default_factory=list, description="Search engine-friendly queries")
    constraints: List[str] = Field(default_factory=list, description="High-level constraints, e.g., recency, citations")
