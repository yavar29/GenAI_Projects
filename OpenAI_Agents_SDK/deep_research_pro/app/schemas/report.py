from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field
from app.schemas.source import SourceDoc

class Section(BaseModel):
    title: str
    summary: str = Field(..., description="Narrative with inline numeric citations like [1], [2].")
    citations: List[int] = Field(default_factory=list, description="List of numeric source IDs cited in this section")

class ResearchReport(BaseModel):
    topic: str
    outline: List[str] = Field(default_factory=list, description="Bullet list outline (5–10 items) describing what the report covers")
    sections: List[Section] = Field(default_factory=list)
    sources: List[SourceDoc] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list, description="Limitations, confidence notes, or next-step suggestions")
