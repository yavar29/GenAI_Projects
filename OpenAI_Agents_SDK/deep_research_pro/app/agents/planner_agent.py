from __future__ import annotations
from typing import List, Optional
from agents import Agent, Runner, ModelSettings
from app.schemas.plan import QueryResponse, FollowUpDecisionResponse
from openai import AsyncOpenAI

class QueryGeneratorAgent:
    """
    Query Generator Agent: Given a user query, generates 5-7 diverse search queries.
    Similar to reference query_agent.py.
    """
    def __init__(self, model: str = "gpt-4o", openai_client: Optional[AsyncOpenAI] = None):
        if openai_client:
            # SDK reads from environment
            pass
        self.agent = Agent(
            name="QueryGenerator",
            instructions=(
                "You are a research planning specialist.\n\n"
                "Given a user query, generate **5–7 diverse search queries** that explore:\n"
                "- definitions & background\n"
                "- statistics & data\n"
                "- trends\n"
                "- case studies\n"
                "- industry adoption\n"
                "- risks & limitations\n"
                "- expert opinions\n"
                "- historical evolution\n"
                "- comparisons with alternatives\n\n"
                "Before listing the queries, think step-by-step about:\n"
                "- what aspects of the topic need investigation\n"
                "- what information is still missing\n"
                "- which angles provide the deepest insight\n\n"
                "Output exactly 5–7 queries."
            ),
            model=model,
            model_settings=ModelSettings(temperature=0.2),
            output_type=QueryResponse,
        )

    async def generate_async(self, query: str) -> QueryResponse:
        """Generate search queries for the given query."""
        result = await Runner.run(self.agent, input=query)
        return result.final_output_as(QueryResponse)


class FollowUpDecisionAgent:
    """
    Follow-Up Decision Agent: Decides if more research is needed and generates follow-up queries.
    Similar to reference follow_up_agent.py.
    """
    def __init__(self, model: str = "gpt-4o", openai_client: Optional[AsyncOpenAI] = None):
        if openai_client:
            # SDK reads from environment
            pass
        self.agent = Agent(
            name="FollowUpDecision",
            instructions=(
                "You analyze current findings and decide if additional research waves are needed.\n\n"
                "Trigger follow-up queries if:\n"
                "- Data or statistics are missing\n"
                "- There are conflicting sources\n"
                "- The topic has unexplored angles\n"
                "- Case studies are missing\n"
                "- Technical depth is insufficient\n"
                "- Trends or future implications are missing\n\n"
                "If follow-up is needed:\n"
                "Generate 2–4 targeted follow-up queries addressing the exact gaps.\n\n"
                "If not:\n"
                "Set should_follow_up=False.\n\n"
                "Always provide detailed reasoning."
            ),
            model=model,
            model_settings=ModelSettings(temperature=0.2),
            output_type=FollowUpDecisionResponse,
        )

    async def decide_async(self, original_query: str, findings_text: str) -> FollowUpDecisionResponse:
        """Decide if follow-up research is needed."""
        prompt = f"Original Query: {original_query}\n\nCurrent Findings:\n{findings_text}"
        result = await Runner.run(self.agent, input=prompt)
        return result.final_output_as(FollowUpDecisionResponse)
