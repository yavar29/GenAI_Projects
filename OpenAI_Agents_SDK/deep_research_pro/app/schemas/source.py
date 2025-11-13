from __future__ import annotations
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

class SourceDoc(BaseModel):
    title: str = Field(..., description="Human-readable title")
    url: HttpUrl
    snippet: str = Field(default="", description="Short abstract/summary")
    published: Optional[str] = Field(default=None, description="ISO date or human date if available")
    source_type: str = Field(default="web", description='e.g., "news", "blog", "paper", "web"')
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
