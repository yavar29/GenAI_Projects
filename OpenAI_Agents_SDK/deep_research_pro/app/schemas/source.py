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
