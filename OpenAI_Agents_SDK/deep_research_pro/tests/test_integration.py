"""
Integration tests for key workflows.

Tests end-to-end scenarios with mocked external dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.research_manager import ResearchManager
from app.schemas.source import SourceDoc


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    return MagicMock()


@pytest.mark.asyncio
async def test_research_pipeline_with_mocked_agents(mock_openai_client):
    """Test that the research pipeline can execute with mocked agents."""
    with patch("app.core.research_manager.make_async_client", return_value=mock_openai_client):
        manager = ResearchManager(
            client=mock_openai_client,
            max_sources=10,
            max_waves=1,  # Single wave for faster test
            topk_per_query=3,
            num_searches=2,
        )
        
        # Mock the planner to return queries
        mock_queries = ["test query 1", "test query 2"]
        manager.planner.generate_async = AsyncMock(return_value=MagicMock(queries=mock_queries))
        
        # Mock web search to return results
        mock_search_results = [
            {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1", "published": "2024-01-01"},
            {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2", "published": "2024-01-02"},
        ]
        manager.web_search_async = AsyncMock(return_value=("Query summary", mock_search_results))
        
        # Mock search agent summarization
        manager.search_agent.summarize_result_async = AsyncMock(return_value="Detailed summary text")
        
        # Mock follow-up decision (no follow-up needed)
        manager.followup_agent.decide_async = AsyncMock(return_value=MagicMock(should_follow_up=False))
        
        # Mock writer agent
        from app.schemas.report import ResearchReport, Section
        mock_report = ResearchReport(
            topic="Test Topic",
            outline=["Section 1", "Section 2"],
            sections=[
                Section(title="Section 1", summary="Content 1", citations=[1]),
                Section(title="Section 2", summary="Content 2", citations=[2]),
            ],
            sources=[],
            notes=[],
        )
        manager.writer.draft_async = AsyncMock(return_value=mock_report)
        
        # Execute pipeline
        results = []
        async for result in manager.run(topic="Test Topic"):
            results.append(result)
        
        # Should yield at least one result (final report)
        assert len(results) > 0
        
        # Final result should have report markdown
        final_report_md, sources_data, status_text, analytics = results[-1]
        assert final_report_md is not None
        assert len(final_report_md) > 0
        assert "Test Topic" in final_report_md or "Section 1" in final_report_md


@pytest.mark.asyncio
async def test_file_processing_integration(mock_openai_client):
    """Test file processing workflow with mocked file agent."""
    with patch("app.core.research_manager.make_async_client", return_value=mock_openai_client):
        manager = ResearchManager(
            client=mock_openai_client,
            max_sources=10,
            max_waves=1,
        )
        
        # Mock file agent
        mock_file_source = SourceDoc(
            title="User File: test.pdf",
            url="https://user-upload.local/test.pdf",
            snippet="File summary snippet",
            content="Full file content summary",
            published=None,
            source_type="file",
            provider="user-upload",
        )
        manager.file_agent.process_file = AsyncMock(return_value=mock_file_source)
        
        # Process files
        status_messages = []
        result = await manager.process_uploaded_files(
            filepaths=["/fake/path/test.pdf"],
            status_messages=status_messages,
        )
        
        # Should return processed source
        assert len(result) == 1
        assert result[0].source_type == "file"
        assert "test.pdf" in result[0].title
        assert len(status_messages) > 0

