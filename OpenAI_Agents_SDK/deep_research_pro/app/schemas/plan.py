from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List

class QueryResponse(BaseModel):
    """Response from Query Generator Agent."""
    thoughts: str = Field(..., description="Analysis and strategy for generating queries")
    queries: List[str] = Field(..., description="5-7 diverse search queries")

class FollowUpDecisionResponse(BaseModel):
    """Response from Follow-Up Decision Agent."""
    should_follow_up: bool = Field(..., description="Whether more research is needed")
    reasoning: str = Field(..., description="Reasoning for the decision")
    queries: List[str] = Field(default_factory=list, description="2-4 targeted follow-up queries if should_follow_up=True")
