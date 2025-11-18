from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.source import SourceDoc

class Subsection(BaseModel):
    """A nested subtopic within a main section."""
    title: str = Field(..., description="Subsection title (e.g., 'Key Technologies', 'Economic Impact', 'Case Study: X')")
    content: str = Field(..., description="Content for this subsection with inline numeric citations like [1], [2]. Can include bullet points, paragraphs, or both.")
    citations: List[int] = Field(default_factory=list, description="List of numeric source IDs cited in this subsection")

class Section(BaseModel):
    title: str
    summary: str = Field(..., description="Narrative with inline numeric citations like [1], [2]. This is the main content/introduction for the section.")
    citations: List[int] = Field(default_factory=list, description="List of numeric source IDs cited in this section")
    subsections: Optional[List[Subsection]] = Field(
        default=None,
        description="Optional list of subsections/subtopics within this section. Use when a section naturally breaks down into distinct subtopics that deserve their own headings."
    )

class ResearchReport(BaseModel):
    topic: str
    outline: List[str] = Field(default_factory=list, description="Bullet list outline (5–10 items) describing what the report covers")
    sections: List[Section] = Field(default_factory=list)
    sources: List[SourceDoc] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list, description="Limitations, confidence notes, or next-step suggestions")
