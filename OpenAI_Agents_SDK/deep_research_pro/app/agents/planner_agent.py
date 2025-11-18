from __future__ import annotations
from typing import List, Optional
from agents import Agent, ModelSettings
from app.schemas.plan import QueryResponse, FollowUpDecisionResponse
from openai import AsyncOpenAI
from app.core.safe import safe_run_async


def _validate_query_response(resp: QueryResponse) -> QueryResponse:
    """Lightweight sanity checks and gentle normalization for QueryGenerator output."""
    # Ensure we have at least one query
    if not resp.queries:
        raise ValueError("QueryGeneratorAgent returned no queries.")

    # Soft validation: warn but allow small query counts (1-2) for simple topics
    if len(resp.queries) < 3:
        print(
            f"Note: QueryGeneratorAgent returned {len(resp.queries)} query/queries. "
            "This may be appropriate for simple topics, but consider if more coverage is needed."
        )
    
    # Hard-cap only ridiculous lengths (>12) to avoid prompt bloat
    if len(resp.queries) > 12:
        print(
            f"Warning: QueryGeneratorAgent returned {len(resp.queries)} queries; "
            "truncating to first 12 to avoid prompt bloat."
        )
        resp.queries = resp.queries[:12]

    # Ensure recommended_source_count is at least 1
    if resp.recommended_source_count <= 0:
        print(
            "Warning: recommended_source_count was <= 0; "
            "defaulting to 25."
        )
        resp.recommended_source_count = 25

    return resp


def _validate_followup_response(resp: FollowUpDecisionResponse) -> FollowUpDecisionResponse:
    """Lightweight sanity checks and gentle normalization for FollowUpDecision output."""
    # Case 1: No follow-up requested → queries must be empty
    if not resp.should_follow_up:
        if resp.queries:
            print(
                "Warning: FollowUpDecisionAgent set should_follow_up=False "
                "but returned non-empty queries; clearing queries."
            )
        resp.queries = []
        return resp

    # Case 2: Follow-up requested → normalize and validate queries
    # Normalize: strip whitespace, drop empty/null, dedupe while preserving order
    cleaned_queries: list[str] = []
    seen: set[str] = set()
    for q in resp.queries or []:
        if not q:
            continue
        q_norm = q.strip()
        if not q_norm:
            continue
        # Use lowercased version for deduping, but keep original casing in output
        key = q_norm.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned_queries.append(q_norm)

    resp.queries = cleaned_queries

    # If should_follow_up=True but we ended up with no usable queries,
    # treat this as "no follow-up" in practice.
    if not resp.queries:
        print(
            "Warning: FollowUpDecisionAgent set should_follow_up=True "
            "but no valid follow-up queries were returned after normalization; "
            "forcing should_follow_up=False."
        )
        resp.should_follow_up = False
        return resp

    # Hard upper bound: avoid runaway follow-up plans
    if len(resp.queries) > 4:
        print(
            f"Warning: FollowUpDecisionAgent returned {len(resp.queries)} "
            "follow-up queries; truncating to first 4 to keep the wave focused."
        )
        resp.queries = resp.queries[:4]

    return resp



class QueryGeneratorAgent:
    """
    Query Generator Agent: Given a user query, generates diverse search queries.
    The number of queries is determined by the agent based on topic complexity
    (typically 3-12 queries, with simple topics needing fewer and complex topics needing more).
    """
    def __init__(self, model: str = "gpt-4o", openai_client: Optional[AsyncOpenAI] = None):
        _ = openai_client
        self.agent = Agent(
        name="QueryGenerator",
        instructions=(
            "You are a research planning specialist.\n\n"
            "Return the answer as JSON with keys thoughts (analysis steps), queries (list of queries), and recommended_source_count.\n\n"
            "Your task is to analyze a user's research topic and produce a structured JSON plan for web research.\n\n"
            "GOALS:\n"
            "- Identify the main facets of the topic (definitions/background, statistics/data, trends, case studies,\n"
            "  risks/limitations, expert opinions, historical evolution, comparisons, adoption, etc.).\n"
            "- From those facets, craft diverse search queries that together give broad and deep coverage of the topic.\n"
            "- Choose the number of queries based on topic complexity: simple topics may need 3–5 queries, moderate topics 5–8, complex topics 8–12.\n"
            "- Estimate how many distinct high-quality sources should be consulted overall, based on the topic's complexity.\n\n"
            "OUTPUT FORMAT (IMPORTANT):\n"
            "- Return ONLY a single valid JSON object with this exact structure (no markdown, no backticks, no extra text):\n"
            "{\n"
            "  \"thoughts\": \"<short paragraph summarizing your planning and rationale>\",\n"
            "  \"queries\": [\n"
            "    \"<query 1>\",\n"
            "    \"<query 2>\",\n"
            "    \"<query 3>\",\n"
            "    \"<query 4>\",\n"
            "    \"<you may include more queries as needed based on topic complexity (typically 3-12 total)>\"\n"
            "  ],\n"
            "  \"recommended_source_count\": <integer>\n"
            "}\n\n"
            "GUIDELINES FOR QUERIES:\n"
            "- Choose the number of queries based on topic complexity:\n"
            "  * Simple topics (basic definitions, single concepts): around 3–4 queries.\n"
            "  * Moderately complex topics (explanations, how-to guides, single topics): around 5–7 queries.\n"
            "  * Very complex, multi-faceted topics (comprehensive analysis, comparisons, multiple dimensions): up to 8–10 queries.\n"
            "- Each query must be standalone and suitable for a web search.\n"
            "- Avoid trivial rephrasings: each query should target a clearly distinct angle or subtopic.\n"
            "- Use neutral, information-seeking language (avoid leading or biased wording).\n\n"
            "GUIDELINES FOR recommended_source_count:\n"
            "- Simple queries (basic definitions, single concepts): about 10–15 sources.\n"
            "- Moderate queries (explanations, how-to guides, single topics): about 20–30 sources.\n"
            "- Complex queries (multi-faceted analysis, comparisons): about 35–50 sources.\n"
            "- Very complex queries (comprehensive comparisons, multiple dimensions): 50+ sources.\n"
            "- Consider:\n"
            "  * Number of entities being compared (e.g., 'X vs Y vs Z' needs more sources).\n"
            "  * Breadth of topic (e.g., 'AI in healthcare' vs. 'AI in radiology').\n"
            "  * Depth required (e.g., 'explain X' vs. 'comprehensive analysis of X').\n"
            "  * Number of queries you generated (more queries typically require more sources overall).\n\n"
            "IMPORTANT:\n"
            "- Do not include any explanation or commentary outside the JSON object.\n"
            "- Use double quotes for all JSON keys and string values.\n"
            "- Ensure the JSON is syntactically valid so it can be parsed directly."
        ),
        model=model,
        model_settings=ModelSettings(temperature=0.2),
        output_type=QueryResponse,
    )


    async def generate_async(self, query: str) -> QueryResponse:
        """Generate search queries for the given query."""
        out: QueryResponse = await safe_run_async(self.agent, query, QueryResponse)
        return _validate_query_response(out)


class FollowUpDecisionAgent:
    """Decides if additional research waves are needed and generates follow-up queries."""
    def __init__(self, model: str = "gpt-4o", openai_client: Optional[AsyncOpenAI] = None):
        if openai_client:
            # SDK reads from environment
            pass
        self.agent = Agent(
            name="FollowUpDecision",
            instructions=(
                "You analyze current research findings and decide whether additional web-research waves are needed.\n\n"
                "Respond in JSON with should_follow_up (true/false), reasoning (explanation), and queries "
                "(1–4 high-impact follow-up queries if needed; prefer fewer when only a small number of serious gaps remain).\n\n"
                "Your decision should be based on whether important gaps remain, such as:\n"
                "- Missing or weak data/statistics.\n"
                "- Clearly conflicting claims between sources.\n"
                "- Major angles that have not been explored (e.g., risks, limitations, comparisons, practical applications).\n"
                "- Lack of concrete case studies or real-world examples where they would be useful.\n"
                "- Insufficient technical depth for a research-grade answer.\n\n"
                "If more research is needed, propose 1–4 targeted follow-up queries that directly address the specific gaps.\n"
                "If no further research is needed, explain why the current findings are sufficient.\n\n"
                "OUTPUT FORMAT (IMPORTANT):\n"
                "- Return ONLY a single valid JSON object with this exact structure (no markdown, no backticks, no extra text):\n"
                "{\n"
                "  \"should_follow_up\": true/false,\n"
                "  \"reasoning\": \"<short paragraph explaining your decision and referencing specific gaps or sufficiency>\",\n"
                "  \"queries\": [\n"
                "    \"<follow-up query 1>\",\n"
                "    \"<follow-up query 2>\",\n"
                "    \"<optional follow-up query 3>\",\n"
                "    \"<optional follow-up query 4>\"\n"
                "  ]\n"
                "}\n\n"
                "DECISION RULES:\n"
                "- Set \"should_follow_up\" to true only if addressing the identified gaps would materially improve the report's accuracy,\n"
                "  completeness, or balance.\n"
                "- Set \"should_follow_up\" to false when remaining gaps are minor (stylistic polish, edge cases, or curiosities that do not\n"
                "  change the main conclusions).\n"
                "- When \"should_follow_up\" is false, set \"queries\" to an empty list [].\n\n"
                "GUIDELINES FOR FOLLOW-UP QUERIES:\n"
                "- Each query must be concrete, targeted, and clearly tied to a specific missing or weak area in the current findings.\n"
                "- Do not simply restate broad angles that are already well-covered; instead, narrow or sharpen them (e.g., by timeframe,\n"
                "  region, method, population, or specific scenario) if you revisit a similar aspect.\n"
                "- Prefer 1–2 high-impact follow-up queries when only a few critical gaps remain; use 3–4 only for genuinely complex,\n"
                "  under-covered topics where multiple distinct gaps must be addressed.\n"
                "- Focus on gaps that are most important for research quality (not minor curiosities).\n\n"
                "IMPORTANT:\n"
                "- Do not include any explanation or commentary outside the JSON object.\n"
                "- Use double quotes for all JSON keys and string values.\n"
                "- Ensure the JSON is syntactically valid so it can be parsed directly."
            ),
            model=model,
            model_settings=ModelSettings(temperature=0.2),
            output_type=FollowUpDecisionResponse,
        )

    async def decide_async(self, original_query: str, findings_text: str) -> FollowUpDecisionResponse:
        """Decide if follow-up research is needed."""
        prompt = f"Original Query: {original_query}\n\nCurrent Findings:\n{findings_text}"
        out: FollowUpDecisionResponse = await safe_run_async(
            self.agent, prompt, FollowUpDecisionResponse
        )
        return _validate_followup_response(out)

