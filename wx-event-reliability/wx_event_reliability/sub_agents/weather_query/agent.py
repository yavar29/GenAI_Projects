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

"""weather_query_agent: geocode → time window → variables → Open-Meteo fetch → summary."""

from google.adk import Agent

# Import the agent prompt text
from . import prompt

# Import function tools (must be FunctionTool-decorated in your tools package)
from ..tools.geocode import geocode_place
from ..tools.variables import pick_variables
from ..tools.model_hint import detect_model_hint
from ..tools.openmeteo import fetch_openmeteo
from ..tools.summarizers import summarise_weather
from ..tools.compare import parse_comparative_query, compare_weather

MODEL = "gemini-2.5-pro"

weather_query_agent = Agent(
    model=MODEL,
    name="weather_query_agent",
    instruction=prompt.WEATHER_QUERY_PROMPT,
    description=(
        "Parses location/time (incl. rich NL dates), infers variables (explicit or implicit), "
        "retrieves data from Open-Meteo, and returns a concise, unit-aware answer."
    ),
    output_key="final_answer",
    tools=[
        geocode_place,
        pick_variables,
        detect_model_hint,
        fetch_openmeteo,
        summarise_weather,
        compare_weather,
        parse_comparative_query,
    ],
)

