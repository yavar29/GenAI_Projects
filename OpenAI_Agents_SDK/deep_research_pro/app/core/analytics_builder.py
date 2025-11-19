# app/core/analytics_builder.py

from __future__ import annotations
from typing import List, Optional, Dict
import re
from collections import Counter
from urllib.parse import urlparse
from app.schemas.report import ResearchReport
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


def _safe_word_count(text: str) -> int:
    if not text:
        return 0
    return len(text.split())


def _extract_domain(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return None


def _bucket_publication_date(published: Optional[str]) -> str:
    """
    Extract year from publication date string.
    Handles various formats:
    - "2025-06-04"
    - "May 14, 2025"
    - "Jun 09, 2025"
    - "14 May 2025"
    - "2025"
    - etc.
    
    Returns the year as a string (e.g., '2025') or 'Unknown' if no year found.
    """
    if not published:
        return "Unknown"
    
    # Use regex to find any 4-digit year (1900-2099)
    # Look for years that are reasonable (1900-2099)
    year_pattern = r'\b(19\d{2}|20[0-9]{2})\b'
    matches = re.findall(year_pattern, str(published))
    
    if matches:
        # Return the first (most likely) year found
        # If multiple years, prefer the most recent one
        years = [int(m) for m in matches]
        return str(max(years))  # Return the most recent year
    
    return "Unknown"

# credibility score can be improved by using more advanced algorithms and data sources based on the domain, source type, and publication date.
def _score_credibility(url: str, source_type: str, published: Optional[str] = None) -> int:
    """
    Enhanced credibility scoring based on domain, source type, and publication date.
    Returns 1-5 score:
    5 = Highest (academic, government, peer-reviewed)
    4 = High (established news, reputable orgs, research institutions)
    3 = Medium (commercial, general news, file uploads)
    2 = Low (blogs, unknown domains)
    1 = Lowest (suspicious or unverifiable)
    """
    # File uploads get medium score (user-provided content)
    if (source_type or "").lower() == "file":
        return 3
    
    domain = _extract_domain(url)
    if not domain:
        return 2
    
    # Remove www. prefix if present for matching
    domain_clean = domain.replace("www.", "")
    
    # ========== SCORE 5: Highest Credibility ==========
    # Academic and government domains
    academic_tlds = (".edu", ".gov", ".ac.uk", ".ac.za", ".ac.jp", ".ac.cn", 
                     ".ac.in", ".ac.au", ".ac.nz", ".ac.il", ".ac.ae")
    if domain.endswith(academic_tlds):
        return 5
    
    # Known academic/research platforms and institutions
    academic_domains = [
        "arxiv.org", "pubmed", "scholar.google", "researchgate.net", 
        "ieee.org", "acm.org", "springer.com", "nature.com", "science.org",
        "cell.com", "thelancet.com", "nejm.org", "bmj.com", "jstor.org",
        "plos.org", "biorxiv.org", "medrxiv.org", "ssrn.com", "nber.org",
        "mit.edu", "stanford.edu", "harvard.edu", "cambridge.org", "oxford.ac.uk",
        "nih.gov", "cdc.gov", "who.int", "un.org", "europa.eu"
    ]
    if any(ad in domain_clean for ad in academic_domains):
        return 5
    
    # ========== SCORE 4: High Credibility ==========
    # Established news organizations (international and major national)
    news_domains = [
        "reuters.com", "ap.org", "apnews.com", "bbc.com", "bbc.co.uk",
        "nytimes.com", "washingtonpost.com", "theguardian.com", "wsj.com",
        "ft.com", "economist.com", "bloomberg.com", "cnn.com", "npr.org",
        "pbs.org", "propublica.org", "theatlantic.com", "newyorker.com",
        "time.com", "newsweek.com", "usatoday.com", "latimes.com",
        "chicagotribune.com", "bostonglobe.com", "politico.com", "axios.com",
        "aljazeera.com", "dw.com", "france24.com", "lemonde.fr", "spiegel.de",
        "asahi.com", "scmp.com", "straitstimes.com"
    ]
    if any(nd in domain_clean for nd in news_domains):
        return 4
    
    # Reputable organizations and think tanks
    org_domains = [
        "brookings.edu", "cato.org", "heritage.org", "cfr.org", "rand.org",
        "pewresearch.org", "gallup.com", "worldbank.org", "imf.org", "oecd.org",
        "wto.org", "ilo.org", "unicef.org", "amnesty.org", "hrw.org",
        "transparency.org", "wikipedia.org"
    ]
    if any(od in domain_clean for od in org_domains):
        return 4
    
    # Government and international organization domains
    if domain.endswith((".org", ".int", ".eu")):
        # Check if it's a known reputable org
        if any(od in domain_clean for od in org_domains):
            return 4
       
    
    # ========== SCORE 3: Medium Credibility ==========
    # Commercial domains - check for known reputable commercial sites
    reputable_commercial = [
        "microsoft.com", "google.com", "apple.com", "amazon.com", "meta.com",
        "github.com", "stackoverflow.com", "reddit.com", "medium.com",
        "techcrunch.com", "wired.com", "verge.com", "arstechnica.com",
        "forbes.com", "businessinsider.com", "cnbc.com", "marketwatch.com"
    ]
    if any(rc in domain_clean for rc in reputable_commercial):
        return 3
    
    # Generic .com domains
    if domain.endswith(".com"):
        return 3
    
    # Generic .org domains (not in our known list)
    if domain.endswith(".org"):
        return 3
    
    # ========== SCORE 2: Low Credibility ==========
    # Blog platforms and social media
    blog_platforms = [
        "blogspot.com", "wordpress.com", "tumblr.com", "livejournal.com",
        "substack.com", "ghost.org", "wix.com", "squarespace.com"
    ]
    if any(bp in domain_clean for bp in blog_platforms):
        return 2
    
    # Social media (generally lower credibility for research)
    social_media = [
        "twitter.com", "x.com", "facebook.com", "instagram.com", "linkedin.com",
        "youtube.com", "tiktok.com", "pinterest.com"
    ]
    if any(sm in domain_clean for sm in social_media):
        return 2
    
    # Unknown or suspicious domains
    # Check for common suspicious patterns
    suspicious_patterns = ["bit.ly", "tinyurl", "goo.gl", "t.co", "ow.ly"]
    if any(sp in domain_clean for sp in suspicious_patterns):
        return 1
    
    # Everything else (unknown domains)
    return 2


def build_analytics_payload(
    topic: str,
    report: ResearchReport,
    sources: List[SourceDoc],
    wave_stats: Optional[List[WaveStat]] = None,
    efficiency: Optional[EfficiencyMetrics] = None,
) -> AnalyticsPayload:
    """
    Build a fully-populated AnalyticsPayload from the final report and sources.
    This is purely a post-processing helper: it does NOT modify the report or
    sources. You can call this at the end of your ResearchManager.run() and
    pass the result to your analytics dashboard state.
    """

    # ------------------------ OVERVIEW ------------------------
    # Approximate word count by summing section summaries
    total_text = "\n\n".join(sec.summary or "" for sec in report.sections)
    word_count = _safe_word_count(total_text)
    num_sections = len(report.sections)
    num_sources = len(sources)
    num_file_sources = sum(
        1 for s in sources if (s.source_type or "").lower() == "file"
    )
    num_web_sources = num_sources - num_file_sources

    overview = SessionOverview(
        topic=topic,
        word_count=word_count,
        num_sections=num_sections,
        num_sources=num_sources,
        num_web_sources=num_web_sources,
        num_file_sources=num_file_sources,
    )

    # ------------------------ SOURCE DISTRIBUTION ------------------------
    # Source types
    type_counter: Counter[str] = Counter()
    # Domains
    domain_counter: Counter[str] = Counter()
    # Publication buckets
    pub_counter: Counter[str] = Counter()
    # Credibility scores (if present)
    cred_counter: Counter[int] = Counter()

    for src in sources:
        stype = (src.source_type or "unknown").lower()
        type_counter[stype] += 1

        domain = _extract_domain(src.url)
        if domain:
            domain_counter[domain] += 1

        bucket = _bucket_publication_date(src.published)
        pub_counter[bucket] += 1

        # Calculate credibility score if not present
        credibility_score = getattr(src, "credibility_score", None)
        if credibility_score is None:
            credibility_score = _score_credibility(src.url, src.source_type, src.published)
        cred_counter[int(credibility_score)] += 1

    source_type_stats = [
        SourceTypeStat(source_type=t, count=c)
        for t, c in type_counter.most_common()
    ]

    domain_stats = [
        DomainStat(domain=d, count=c)
        for d, c in domain_counter.most_common()
    ]

    publication_stats = [
        PublicationBucketStat(bucket=b, count=c)
        for b, c in sorted(pub_counter.items(), key=lambda x: x[0])
    ]

    credibility_stats = [
        CredibilityStat(score=score, count=cnt)
        for score, cnt in sorted(cred_counter.items(), key=lambda x: x[0])
    ]

    # ------------------------ SECTION COVERAGE & CITATIONS ------------------------
    section_coverage: List[SectionCoverageStat] = []
    all_citations: List[int] = []

    for sec in report.sections:
        text = sec.summary or ""
        wc = _safe_word_count(text)
        citations = sec.citations or []
        citation_count = len(citations)
        all_citations.extend(citations)

        section_coverage.append(
            SectionCoverageStat(
                section_title=sec.title or "(Untitled section)",
                word_count=wc,
                citation_count=citation_count,
            )
        )

    # Sort to find sections with most citations (top 5)
    sections_with_most_citations = sorted(
        section_coverage,
        key=lambda s: s.citation_count,
        reverse=True,
    )[:5]

    # ------------------------ CITATION FREQUENCIES ------------------------
    citation_frequencies: List[CitationFrequencyStat] = []

    if sources and all_citations:
        freq_counter: Counter[int] = Counter(all_citations)
        for src_id, count in freq_counter.most_common():
            # src_id is 1-based index into sources
            if 1 <= src_id <= len(sources):
                src = sources[src_id - 1]
                title = src.title or f"Source {src_id}"
            else:
                title = f"Source {src_id}"

            citation_frequencies.append(
                CitationFrequencyStat(
                    source_id=src_id,
                    title=title,
                    count=count,
                )
            )

    # ------------------------ PROCESS & EFFICIENCY ------------------------
    # wave_stats and efficiency are passed through if provided
    wave_stats = wave_stats or []

    analytics = AnalyticsPayload(
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
        extra={},
    )

    return analytics

