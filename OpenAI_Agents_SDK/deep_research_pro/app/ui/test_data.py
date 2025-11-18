"""
Test data generator for UI testing without API calls.
Generates realistic fake data for reports, analytics, and live logs.
"""

from __future__ import annotations
import asyncio
import random
from typing import List, Optional
from datetime import datetime, timedelta

from app.schemas.report import ResearchReport, Section
from app.schemas.source import SourceDoc
from app.schemas.analytics import (
    AnalyticsPayload,
    SessionOverview,
    SourceTypeStat,
    DomainStat,
    PublicationBucketStat,
    CredibilityStat,
    SectionCoverageStat,
    CitationFrequencyStat,
    WaveStat,
    EfficiencyMetrics,
)
from app.core.render import render_markdown


def generate_fake_sources(topic: str, count: int = 8) -> List[SourceDoc]:
    """Generate fake sources related to the topic."""
    domains = [
        "nature.com",
        "science.org",
        "arxiv.org",
        "ieee.org",
        "techcrunch.com",
        "wired.com",
        "mit.edu",
        "stanford.edu",
        "harvard.edu",
        "bbc.com",
        "reuters.com",
        "theguardian.com",
    ]
    
    sources = []
    for i in range(1, count + 1):
        year = random.choice([2023, 2024, 2025])
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        date_str = f"{year}-{month:02d}-{day:02d}"
        
        domain = random.choice(domains)
        title = f"{topic}: Research Findings {i} - {domain.split('.')[0].title()}"
        url = f"https://www.{domain}/article/{i}-{topic.lower().replace(' ', '-')}"
        
        snippet = f"This article discusses key aspects of {topic}, providing insights into recent developments and future trends. The research highlights important findings that contribute to our understanding of the subject matter."
        
        sources.append(
            SourceDoc(
                title=title,
                url=url,
                snippet=snippet,
                content=f"Full content about {topic} from source {i}. This includes detailed analysis, methodology, and conclusions.",
                published=date_str,
                source_type="web",
                provider=domain,
            )
        )
    
    return sources


def generate_fake_report(topic: str, sources: List[SourceDoc]) -> ResearchReport:
    """Generate a fake research report."""
    
    outline = [
        f"Introduction to {topic}",
        f"Background and Fundamentals of {topic}",
        f"Current State and Recent Developments",
        f"Comparative Analysis and Case Studies",
        f"Future Trends and Outlook",
        f"Limitations and Challenges",
        f"Conclusion and Recommendations",
    ]
    
    sections = [
        Section(
            title=f"Introduction to {topic}",
            summary=f"{topic} represents a significant area of research and development in modern technology and science. This report provides a comprehensive analysis of the current state, key findings, and future directions [1][2]. The importance of understanding {topic} cannot be overstated, as it impacts multiple domains including technology, society, and economics [3].",
            citations=[1, 2, 3],
        ),
        Section(
            title=f"Background and Fundamentals of {topic}",
            summary=f"The foundational concepts of {topic} have evolved significantly over the past decade. Early research focused on basic principles [4][5], while recent advances have expanded our understanding considerably [6]. Key theoretical frameworks include multiple approaches that have been validated through extensive experimentation [7][8].",
            citations=[4, 5, 6, 7, 8],
        ),
        Section(
            title=f"Current State and Recent Developments",
            summary=f"Recent developments in {topic} have shown remarkable progress. Studies published in 2024 and 2025 demonstrate significant improvements in performance and applicability [1][3][6]. Industry adoption has accelerated, with major organizations implementing solutions based on these findings [2][5]. The current landscape shows a diverse ecosystem of approaches and methodologies [4][7].",
            citations=[1, 2, 3, 4, 5, 6, 7],
        ),
        Section(
            title=f"Comparative Analysis and Case Studies",
            summary=f"A comparative analysis reveals distinct advantages and trade-offs among different approaches to {topic}. Case studies from various domains illustrate practical applications and outcomes [1][3][8]. The analysis highlights key factors that influence success, including implementation strategies and resource requirements [2][5][6].",
            citations=[1, 2, 3, 5, 6, 8],
        ),
        Section(
            title=f"Future Trends and Outlook",
            summary=f"Looking ahead, {topic} is expected to continue evolving rapidly. Emerging trends suggest new directions for research and development [4][7]. Predictions indicate significant growth in adoption and refinement of existing approaches [1][3][6]. The future outlook is optimistic, with multiple promising avenues for advancement [2][5].",
            citations=[1, 2, 3, 4, 5, 6, 7],
        ),
        Section(
            title=f"Limitations and Challenges",
            summary=f"Despite significant progress, {topic} faces several limitations and challenges. Current approaches have constraints related to scalability, accuracy, and resource requirements [3][6][8]. Addressing these challenges will require continued research and innovation [1][4][7]. The field must navigate technical, ethical, and practical considerations [2][5].",
            citations=[1, 2, 3, 4, 5, 6, 7, 8],
        ),
        Section(
            title=f"Conclusion and Recommendations",
            summary=f"In conclusion, {topic} represents a dynamic and evolving field with significant potential. The research reviewed in this report demonstrates both achievements and areas for future work [1][2][3]. Recommendations include continued investment in research, collaboration across disciplines, and attention to practical implementation challenges [4][5][6][7][8].",
            citations=[1, 2, 3, 4, 5, 6, 7, 8],
        ),
    ]
    
    notes = [
        f"This report is based on {len(sources)} sources and provides a comprehensive overview of {topic}.",
        "Some limitations include the scope of sources reviewed and the timeframe of the analysis.",
        "Future research could expand on specific sub-topics identified in this report.",
    ]
    
    return ResearchReport(
        topic=topic,
        outline=outline,
        sections=sections,
        sources=sources,
        notes=notes,
    )


def generate_fake_analytics(topic: str, report: ResearchReport, num_waves: int = 3) -> AnalyticsPayload:
    """Generate fake analytics data."""
    
    # Overview
    word_count = sum(len(section.summary.split()) for section in report.sections)
    overview = SessionOverview(
        topic=topic,
        word_count=word_count,
        num_sections=len(report.sections),
        num_sources=len(report.sources),
        num_web_sources=len([s for s in report.sources if s.source_type == "web"]),
        num_file_sources=len([s for s in report.sources if s.source_type == "file"]),
    )
    
    # Source type stats
    source_type_stats = [
        SourceTypeStat(source_type="web", count=overview.num_web_sources),
        SourceTypeStat(source_type="file", count=overview.num_file_sources),
    ]
    
    # Domain stats
    domains = {}
    for source in report.sources:
        if source.provider:
            domain = source.provider.split('.')[0] if '.' in source.provider else source.provider
            domains[domain] = domains.get(domain, 0) + 1
    
    domain_stats = [
        DomainStat(domain=domain, count=count)
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    
    # Publication stats
    years = {}
    for source in report.sources:
        if source.published:
            try:
                year = int(source.published.split('-')[0])
                years[year] = years.get(year, 0) + 1
            except (ValueError, IndexError):
                pass
    
    publication_stats = [
        PublicationBucketStat(bucket=str(year), count=count)
        for year, count in sorted(years.items())
    ]
    
    # Credibility stats (fake distribution)
    credibility_stats = [
        CredibilityStat(score=5, count=len(report.sources) // 2),
        CredibilityStat(score=4, count=len(report.sources) // 3),
        CredibilityStat(score=3, count=len(report.sources) // 6),
    ]
    
    # Section coverage
    section_coverage = [
        SectionCoverageStat(
            section_title=section.title,
            word_count=len(section.summary.split()),
            citation_count=len(section.citations),
        )
        for section in report.sections
    ]
    
    # Citation frequencies
    citation_counts = {}
    for section in report.sections:
        for citation_id in section.citations:
            citation_counts[citation_id] = citation_counts.get(citation_id, 0) + 1
    
    citation_frequencies = [
        CitationFrequencyStat(
            source_id=source_id,
            title=report.sources[source_id - 1].title if source_id <= len(report.sources) else f"Source {source_id}",
            count=count,
        )
        for source_id, count in sorted(citation_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    
    # Sections with most citations
    sections_with_most_citations = sorted(
        section_coverage,
        key=lambda x: x.citation_count,
        reverse=True
    )[:5]
    
    # Wave stats
    wave_stats = []
    base_queries = 3
    base_sources = 2
    
    for wave in range(1, num_waves + 1):
        wave_stats.append(
            WaveStat(
                wave_index=wave,
                num_queries=base_queries + random.randint(0, 2),
                num_sources_discovered=base_sources + random.randint(1, 3),
                duration_seconds=random.uniform(15.0, 45.0),
                wave_text_added=random.randint(200, 500) if wave > 1 else None,
                wave_text_rewritten=random.randint(50, 150) if wave > 1 else None,
                wave_citations_added=random.randint(2, 5) if wave > 1 else None,
                wave_quality_change_score=random.uniform(0.1, 0.3) if wave > 1 else None,
            )
        )
    
    # Efficiency metrics
    efficiency = EfficiencyMetrics(
        queries_executed=sum(w.num_queries for w in wave_stats),
        total_sources_seen=sum(w.num_sources_discovered for w in wave_stats),
        unique_sources_used=len(report.sources),
        cache_hit_rate=random.uniform(0.3, 0.6),
        waves_completed=num_waves,
        total_duration_seconds=sum(w.duration_seconds or 0 for w in wave_stats),
    )
    
    return AnalyticsPayload(
        overview=overview,
        source_type_stats=source_type_stats,
        domain_stats=domain_stats,
        publication_stats=publication_stats,
        credibility_stats=credibility_stats,
        section_coverage=section_coverage,
        citation_frequencies=citation_frequencies,
        sections_with_most_citations=sections_with_most_citations,
        wave_stats=wave_stats,
        efficiency=efficiency,
    )


async def generate_fake_live_log(topic: str, num_waves: int = 3) -> str:
    """Generate fake live log messages that simulate the research process."""
    
    log_lines = []
    log_lines.append(f"🚀 Starting research on: {topic}\n")
    log_lines.append("=" * 60 + "\n")
    
    await asyncio.sleep(0.5)
    
    # Wave 1
    log_lines.append(f"\n📊 Wave 1: Initial Research\n")
    log_lines.append("🔍 Generating search queries...\n")
    await asyncio.sleep(0.3)
    log_lines.append("✅ Generated 3 search queries\n")
    await asyncio.sleep(0.2)
    log_lines.append("🔎 Executing searches...\n")
    await asyncio.sleep(0.4)
    log_lines.append("✅ Found 5 relevant sources\n")
    await asyncio.sleep(0.3)
    log_lines.append("📝 Analyzing sources and generating initial report...\n")
    await asyncio.sleep(0.5)
    log_lines.append("✅ Wave 1 complete: 2 sections written, 3 citations added\n")
    
    if num_waves > 1:
        await asyncio.sleep(0.3)
        log_lines.append(f"\n📊 Wave 2: Deepening Research\n")
        log_lines.append("🔍 Identifying gaps in coverage...\n")
        await asyncio.sleep(0.3)
        log_lines.append("✅ Generated 2 additional queries\n")
        await asyncio.sleep(0.2)
        log_lines.append("🔎 Executing targeted searches...\n")
        await asyncio.sleep(0.4)
        log_lines.append("✅ Found 3 new sources\n")
        await asyncio.sleep(0.3)
        log_lines.append("📝 Expanding report with new findings...\n")
        await asyncio.sleep(0.5)
        log_lines.append("✅ Wave 2 complete: 250 words added, 4 citations added\n")
    
    if num_waves > 2:
        await asyncio.sleep(0.3)
        log_lines.append(f"\n📊 Wave 3: Refinement\n")
        log_lines.append("🔍 Verifying information and checking for gaps...\n")
        await asyncio.sleep(0.3)
        log_lines.append("✅ Generated 1 verification query\n")
        await asyncio.sleep(0.2)
        log_lines.append("🔎 Executing verification search...\n")
        await asyncio.sleep(0.4)
        log_lines.append("✅ Found 2 additional sources\n")
        await asyncio.sleep(0.3)
        log_lines.append("📝 Refining report and adding final details...\n")
        await asyncio.sleep(0.5)
        log_lines.append("✅ Wave 3 complete: 150 words rewritten, 2 citations added\n")
    
    await asyncio.sleep(0.3)
    log_lines.append(f"\n✨ Research Complete!\n")
    log_lines.append("=" * 60 + "\n")
    log_lines.append(f"📄 Final report: {len(log_lines)} sections, {8} sources\n")
    log_lines.append("✅ All waves completed successfully\n")
    
    return "".join(log_lines)


async def generate_fake_research_stream(
    topic: str,
    queries: list,
    num_sources: int,
    num_waves: int,
    uploaded_files: list,
) -> None:
    """
    Generate a fake research stream that yields results similar to the real one.
    This simulates the research process without making API calls.
    """
    
    # Generate fake sources
    sources = generate_fake_sources(topic, count=min(num_sources, 10))
    
    # Generate fake report
    report = generate_fake_report(topic, sources)
    
    # Generate fake analytics
    analytics = generate_fake_analytics(topic, report, num_waves=num_waves)
    
    # Convert sources to table format
    sources_data = [
        [source.title, source.url, source.source_type]
        for source in sources
    ]
    
    # Render report to markdown
    report_md = render_markdown(report)
    
    # Generate live log progressively
    log_lines = []
    log_lines.append(f"🚀 Starting research on: {topic}\n")
    log_lines.append("=" * 60 + "\n")
    
    # Yield initial state
    yield (report_md, sources_data, "".join(log_lines), None)
    await asyncio.sleep(0.5)
    
    # Wave 1
    log_lines.append(f"\n📊 Wave 1: Initial Research\n")
    log_lines.append("🔍 Generating search queries...\n")
    yield (report_md, sources_data, "".join(log_lines), None)
    await asyncio.sleep(0.3)
    
    log_lines.append("✅ Generated 3 search queries\n")
    log_lines.append("🔎 Executing searches...\n")
    yield (report_md, sources_data, "".join(log_lines), None)
    await asyncio.sleep(0.4)
    
    log_lines.append("✅ Found 5 relevant sources\n")
    log_lines.append("📝 Analyzing sources and generating initial report...\n")
    yield (report_md, sources_data, "".join(log_lines), None)
    await asyncio.sleep(0.5)
    
    log_lines.append("✅ Wave 1 complete: 2 sections written, 3 citations added\n")
    yield (report_md, sources_data, "".join(log_lines), None)
    
    if num_waves > 1:
        await asyncio.sleep(0.3)
        log_lines.append(f"\n📊 Wave 2: Deepening Research\n")
        log_lines.append("🔍 Identifying gaps in coverage...\n")
        yield (report_md, sources_data, "".join(log_lines), None)
        await asyncio.sleep(0.3)
        
        log_lines.append("✅ Generated 2 additional queries\n")
        log_lines.append("🔎 Executing targeted searches...\n")
        yield (report_md, sources_data, "".join(log_lines), None)
        await asyncio.sleep(0.4)
        
        log_lines.append("✅ Found 3 new sources\n")
        log_lines.append("📝 Expanding report with new findings...\n")
        yield (report_md, sources_data, "".join(log_lines), None)
        await asyncio.sleep(0.5)
        
        log_lines.append("✅ Wave 2 complete: 250 words added, 4 citations added\n")
        yield (report_md, sources_data, "".join(log_lines), None)
    
    if num_waves > 2:
        await asyncio.sleep(0.3)
        log_lines.append(f"\n📊 Wave 3: Refinement\n")
        log_lines.append("🔍 Verifying information and checking for gaps...\n")
        yield (report_md, sources_data, "".join(log_lines), None)
        await asyncio.sleep(0.3)
        
        log_lines.append("✅ Generated 1 verification query\n")
        log_lines.append("🔎 Executing verification search...\n")
        yield (report_md, sources_data, "".join(log_lines), None)
        await asyncio.sleep(0.4)
        
        log_lines.append("✅ Found 2 additional sources\n")
        log_lines.append("📝 Refining report and adding final details...\n")
        yield (report_md, sources_data, "".join(log_lines), None)
        await asyncio.sleep(0.5)
        
        log_lines.append("✅ Wave 3 complete: 150 words rewritten, 2 citations added\n")
        yield (report_md, sources_data, "".join(log_lines), None)
    
    await asyncio.sleep(0.3)
    log_lines.append(f"\n✨ Research Complete!\n")
    log_lines.append("=" * 60 + "\n")
    log_lines.append(f"📄 Final report: {len(report.sections)} sections, {len(sources)} sources\n")
    log_lines.append("✅ All waves completed successfully\n")
    
    # Final yield with analytics
    yield (report_md, sources_data, "".join(log_lines), analytics)

