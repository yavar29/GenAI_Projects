from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

class SourceDoc(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = None
    content: Optional[str] = None
    published: Optional[str] = None
    source_type: str = "web"  # now supports: "web", "file"
    provider: Optional[str] = Field(default=None, description="Search provider or site label")

class SearchResult(BaseModel):
    """Per-result summary from search_agent."""
    id: int = Field(..., description="Numeric ID from Source Index")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    summary: str = Field(..., description="2-3 paragraph summary of this result")

class SourceItem(BaseModel):
    """Source with numeric ID for deterministic citations."""
    id: int = Field(..., description="Numeric ID (1..K)")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    snippet: str = Field(default="", description="Short snippet from search")
    date: Optional[str] = Field(default=None, description="Publication date if available")
    domain: Optional[str] = Field(default=None, description="Domain name if available")
