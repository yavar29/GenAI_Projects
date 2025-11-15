"""
Unit tests for WriterAgent.

Tests that the WriterAgent can handle dummy sources and produce expected JSON structure.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.writer_agent import WriterAgent
from app.schemas.source import SourceDoc
from app.schemas.report import ResearchReport


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    return MagicMock()


@pytest.fixture
def dummy_sources():
    """Create dummy SourceDoc objects for testing."""
    return [
        SourceDoc(
            title="AI in Healthcare: Current Applications",
            url="https://example.com/ai-healthcare",
            snippet="AI is transforming healthcare through diagnostic tools and treatment optimization.",
            content="Artificial intelligence is revolutionizing healthcare by enabling early disease detection, personalized treatment plans, and improved patient outcomes. Key applications include medical imaging analysis, drug discovery, and predictive analytics.",
            published="2024-01-15",
            source_type="web",
            provider="openai",
        ),
        SourceDoc(
            title="Healthcare AI Statistics 2024",
            url="https://example.com/ai-stats",
            snippet="Recent studies show 85% of hospitals are implementing AI solutions.",
            content="A comprehensive survey of 500 hospitals revealed that 85% are actively implementing AI solutions. The market is expected to reach $102 billion by 2028. Key areas include radiology, pathology, and administrative automation.",
            published="2024-02-20",
            source_type="web",
            provider="openai",
        ),
        SourceDoc(
            title="Challenges in Healthcare AI Adoption",
            url="https://example.com/ai-challenges",
            snippet="Data privacy and regulatory compliance remain major barriers.",
            content="While AI offers significant benefits, healthcare organizations face challenges including data privacy concerns, regulatory compliance (HIPAA, GDPR), lack of skilled personnel, and integration with existing systems. These barriers slow adoption rates.",
            published="2024-03-10",
            source_type="web",
            provider="openai",
        ),
    ]


@pytest.mark.asyncio
async def test_writer_agent_produces_structured_output(mock_openai_client, dummy_sources):
    """Test that WriterAgent produces valid structured output with sections."""
    agent = WriterAgent(model="gpt-4o", openai_client=mock_openai_client)
    
    # Mock the agent's run method to return a structured response
    mock_output = {
        "outline": [
            "Introduction to AI in Healthcare",
            "Current Applications and Statistics",
            "Challenges and Limitations",
        ],
        "sections": [
            {
                "title": "Introduction to AI in Healthcare",
                "summary": "Artificial intelligence is transforming healthcare through various applications including diagnostic tools and treatment optimization [1].",
                "citations": [1],
            },
            {
                "title": "Current Applications and Statistics",
                "summary": "Recent studies indicate that 85% of hospitals are implementing AI solutions, with the market expected to reach $102 billion by 2028 [2].",
                "citations": [2],
            },
            {
                "title": "Challenges and Limitations",
                "summary": "Despite benefits, healthcare organizations face challenges including data privacy, regulatory compliance, and integration issues [3].",
                "citations": [3],
            },
        ],
        "notes": [
            "Further research needed on long-term outcomes",
            "Regulatory frameworks are evolving rapidly",
        ],
    }
    
    with patch("app.agents.writer_agent.safe_run_async") as mock_safe_run:
        from app.agents.writer_agent import WriterOutput
        mock_safe_run.return_value = WriterOutput(**mock_output)
        
        result = await agent.draft_async(
            topic="AI in Healthcare",
            subtopics=["Background", "Statistics", "Challenges"],
            summaries=[
                f"Title: {s.title}\nURL: {s.url}\nSummary: {s.content}"
                for s in dummy_sources
            ],
            sources=dummy_sources,
        )
        
        # Validate result structure
        assert isinstance(result, ResearchReport)
        assert result.topic == "AI in Healthcare"
        assert len(result.sections) == 3
        assert len(result.outline) == 3
        assert len(result.notes) == 2
        
        # Validate sections have required fields
        for section in result.sections:
            assert section.title is not None
            assert section.summary is not None
            assert len(section.summary) > 0
            assert isinstance(section.citations, list)
        
        # Validate citations reference valid sources
        all_citation_ids = []
        for section in result.sections:
            all_citation_ids.extend(section.citations)
        
        # All citations should be valid (1-indexed)
        assert all(1 <= cid <= len(dummy_sources) for cid in all_citation_ids)


@pytest.mark.asyncio
async def test_writer_agent_handles_empty_sources(mock_openai_client):
    """Test that WriterAgent handles empty source list gracefully."""
    agent = WriterAgent(model="gpt-4o", openai_client=mock_openai_client)
    
    mock_output = {
        "outline": ["Introduction"],
        "sections": [
            {
                "title": "Introduction",
                "summary": "This topic requires further research as no sources were provided.",
                "citations": [],
            }
        ],
        "notes": ["No sources available for this research topic"],
    }
    
    with patch("app.agents.writer_agent.safe_run_async") as mock_safe_run:
        from app.agents.writer_agent import WriterOutput
        mock_safe_run.return_value = WriterOutput(**mock_output)
        
        result = await agent.draft_async(
            topic="Test Topic",
            subtopics=[],
            summaries=[],
            sources=[],
        )
        
        assert isinstance(result, ResearchReport)
        assert len(result.sections) >= 1


@pytest.mark.asyncio
async def test_writer_agent_validates_minimum_sections(mock_openai_client, dummy_sources):
    """Test that WriterAgent validates minimum section count."""
    agent = WriterAgent(model="gpt-4o", openai_client=mock_openai_client)
    
    # Mock output with only 1 section (should fail validation)
    mock_output = {
        "outline": ["Only Section"],
        "sections": [
            {
                "title": "Only Section",
                "summary": "This is the only section.",
                "citations": [1],
            }
        ],
        "notes": [],
    }
    
    with patch("app.agents.writer_agent.safe_run_async") as mock_safe_run:
        from app.agents.writer_agent import WriterOutput
        mock_safe_run.return_value = WriterOutput(**mock_output)
        
        # Should raise ValueError for too few sections
        with pytest.raises(ValueError, match="too few sections"):
            await agent.draft_async(
                topic="Test Topic",
                subtopics=[],
                summaries=[f"Title: {s.title}\nSummary: {s.content}" for s in dummy_sources],
                sources=dummy_sources,
            )


@pytest.mark.asyncio
async def test_writer_agent_with_subtopics(mock_openai_client, dummy_sources):
    """Test that WriterAgent uses subtopics to structure the report."""
    agent = WriterAgent(model="gpt-4o", openai_client=mock_openai_client)
    
    subtopics = ["Background & Fundamentals", "Statistics & Data", "Risks & Challenges"]
    
    mock_output = {
        "outline": [
            "Background & Fundamentals",
            "Statistics & Data",
            "Risks & Challenges",
        ],
        "sections": [
            {
                "title": "Background & Fundamentals",
                "summary": "AI is transforming healthcare [1].",
                "citations": [1],
            },
            {
                "title": "Statistics & Data",
                "summary": "85% of hospitals are implementing AI [2].",
                "citations": [2],
            },
            {
                "title": "Risks & Challenges",
                "summary": "Data privacy remains a major barrier [3].",
                "citations": [3],
            },
        ],
        "notes": [],
    }
    
    with patch("app.agents.writer_agent.safe_run_async") as mock_safe_run:
        from app.agents.writer_agent import WriterOutput
        mock_safe_run.return_value = WriterOutput(**mock_output)
        
        result = await agent.draft_async(
            topic="AI in Healthcare",
            subtopics=subtopics,
            summaries=[f"Title: {s.title}\nSummary: {s.content}" for s in dummy_sources],
            sources=dummy_sources,
        )
        
        # Verify subtopics influenced structure
        section_titles = [s.title for s in result.sections]
        assert len(section_titles) == 3
        # At least one section should reflect subtopic themes
        assert any("Background" in title or "Statistics" in title or "Risks" in title 
                  for title in section_titles)

