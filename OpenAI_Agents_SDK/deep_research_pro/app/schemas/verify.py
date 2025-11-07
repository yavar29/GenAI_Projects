from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, conlist, confloat

class SectionMetrics(BaseModel):
    llm_conf: confloat(ge=0.0, le=1.0) = Field(..., description="Raw LLM confidence in [0,1].")
    coverage: confloat(ge=0.0, le=1.0) = Field(..., description="Claims→citations coverage in [0,1].")
    quality: confloat(ge=0.0, le=1.0) = Field(..., description="Source quality score in [0,1].")
    recency: confloat(ge=0.0, le=1.0) = Field(..., description="Freshness score in [0,1].")
    final: confloat(ge=0.0, le=1.0) = Field(..., description="Blended confidence in [0,1].")

class SectionReview(BaseModel):
    section_title: str = Field(..., description="Title of the section being evaluated.")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence score in [0,1]. (Final if strict mode on)")
    reasoning: str = Field(..., description="Short justification for the confidence score.")
    issues: List[str] = Field(default_factory=list, description="Potential issues, gaps, or risks.")
    cited_urls: List[str] = Field(default_factory=list, description="URLs actually relied upon in the check.")
    metrics: Optional[SectionMetrics] = Field(default=None, description="Optional metrics breakdown when strict mode is enabled.")

class VerificationOutput(BaseModel):
    overall_confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Overall confidence across sections.")
    reviews: conlist(SectionReview, min_length=1) = Field(..., description="Per-section reviews.")
    methodology: str = Field(..., description="1–3 sentences describing how the check was performed.")
