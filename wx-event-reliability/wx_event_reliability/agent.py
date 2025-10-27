# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Weather Analyst: geocode, time-window parsing, model-aware retrieval, and concise answers.
   If relevant, adds a brief physics note via RAG (Vertex AI RAG corpus)."""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .sub_agents.weather_query import weather_query_agent
from .sub_agents.physics_rag import physics_rag_agent

# Match sample style: declare model at top for easy switching
MODEL = "gemini-2.5-pro"  # or "gemini-2.0-flash" if you prefer lower latency

weather_coordinator = LlmAgent(
    name="weather_coordinator",
    model=MODEL,
    description=(
        "Understands flexible weather questions about a location and time window, "
        "derives lat/lon and the correct date range (e.g., last weekend, holidays, multi-day), "
        "fetches variables (temperature, wind, precipitation, humidity and all other variables.) from Open-Meteo "
        "and summarizes results with units. If the user asks 'why' or a physics note is relevant, "
        "delegates to a physics RAG sub-agent for a short intuitive explanation."
    ),
    instruction=prompt.WEATHER_COORDINATOR_PROMPT,
    # Key in the final tool/agent output to bubble up as the message result
    # (useful if your sub-agents return structured payloads and you want a specific field)
    output_key="final_answer",
    tools=[
        AgentTool(agent=weather_query_agent),
        AgentTool(agent=physics_rag_agent),
    ],
)

# For ADK discovery consistency with samples
root_agent = weather_coordinator

