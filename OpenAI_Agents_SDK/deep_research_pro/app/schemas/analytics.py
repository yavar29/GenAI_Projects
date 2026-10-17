# app/schemas/analytics.py

from __future__ import annotations

from typing import List, Dict, Optional

from pydantic import BaseModel


class SourceTypeStat(BaseModel):
    source_type: str        # "web", "file", etc.
    count: int


class DomainStat(BaseModel):
    domain: str             # e.g. "nih.gov"
    count: int


class PublicationBucketStat(BaseModel):
    bucket: str             # e.g. "2020", "2021-2023", "2024-Q1"
    count: int


class CredibilityStat(BaseModel):
    score: int              # 1–5
    count: int


class SectionCoverageStat(BaseModel):
    section_title: str
    word_count: int
    citation_count: int


class CitationFrequencyStat(BaseModel):
    source_id: int          # 1-based index matching sources list
    title: str
    count: int


class WaveStat(BaseModel):
    wave_index: int         # 1..N
    num_queries: int
    num_sources_discovered: int
    duration_seconds: Optional[float] = None


class EfficiencyMetrics(BaseModel):
    queries_executed: int
    total_sources_seen: int
    unique_sources_used: int
    cache_hit_rate: Optional[float] = None
    waves_completed: int
    total_duration_seconds: Optional[float] = None


class SessionOverview(BaseModel):
    topic: str
    word_count: int
    num_sections: int
    num_sources: int
    num_web_sources: int
    num_file_sources: int


class AnalyticsPayload(BaseModel):
    """
    Single object the dashboard consumes.
    You will populate this later inside ResearchManager.
    """
    overview: SessionOverview

    # 1. Source distribution / quality
    source_type_stats: List[SourceTypeStat] = []
    domain_stats: List[DomainStat] = []
    publication_stats: List[PublicationBucketStat] = []
    credibility_stats: List[CredibilityStat] = []

    # 2. Coverage & citations
    section_coverage: List[SectionCoverageStat] = []
    citation_frequencies: List[CitationFrequencyStat] = []
    sections_with_most_citations: List[SectionCoverageStat] = []

    # 3. Process / efficiency
    wave_stats: List[WaveStat] = []
    efficiency: Optional[EfficiencyMetrics] = None

    # For future extension if needed
    extra: Dict[str, object] = {}

