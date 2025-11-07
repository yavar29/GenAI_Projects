from app.agents.search_agent import SearchAgent
from app.tools.hosted_tools import load_hosted_tools

def test_search_agent_with_stub():
    tools = load_hosted_tools()
    sa = SearchAgent(search_func=tools["web_search"])
    out = sa.search_many(["unit test query"], limit_total=3)
    assert len(out) >= 2
    assert out[0].title
    assert str(out[0].url).startswith("https://")
