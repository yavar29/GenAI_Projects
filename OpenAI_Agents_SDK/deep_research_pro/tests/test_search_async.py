import pytest
from app.agents.search_agent import SearchAgent
from app.tools.hosted_tools import get_search_provider

@pytest.mark.asyncio
async def test_search_agent_async_stub():
    """Test async search path with stub provider."""
    web_search = get_search_provider("stub")
    sa = SearchAgent(search_func=web_search)
    out = await sa.search_many_async(["unit test query"], limit_total=3)
    assert len(out) >= 2
    assert out[0].title
    assert str(out[0].url).startswith("https://")

