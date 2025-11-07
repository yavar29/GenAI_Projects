from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field
from app.schemas.source import SourceDoc

class Section(BaseModel):
    title: str
    summary: str = Field(..., description="3–5 sentences, concise and factual")
    citations: List[str] = Field(default_factory=list, description="List of URLs cited in this section")

class ResearchReport(BaseModel):
    topic: str
    sections: List[Section] = Field(default_factory=list)
    sources: List[SourceDoc] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list, description="Limitations or confidence notes")
