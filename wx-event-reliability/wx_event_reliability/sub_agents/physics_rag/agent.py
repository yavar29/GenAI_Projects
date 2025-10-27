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

"""Physics RAG agent for Weather Analyst: retrieves concise physics context/explanations."""

import os
from typing import Optional

from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai import init as vertexai_init
from vertexai.preview import rag

# Import your prompt function/string for this agent
# (Keep the API identical to the ADK sample; define `return_instructions_weather_rag` in .prompts)
from .prompt import return_instructions_weather_rag

load_dotenv()


def _maybe_init_vertex():
    """Initialize Vertex AI if project/location are provided (safe no-op if not)."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if project:
        vertexai_init(project=project, location=location)


def _resolve_rag_corpus() -> str:
    """
    Resolve a RAG corpus resource name.
    Priority:
      1) RAG_CORPUS (full resource: projects/…/locations/…/ragCorpora/…)
      2) GOOGLE_RAG_CORPUS_DISPLAY_NAME (find by display name via list_corpora)
    """
    # 1) Full resource provided
    full = os.environ.get("RAG_CORPUS")
    if full and full.startswith("projects/"):
        return full

    # 2) Lookup by display name
    display = os.environ.get("GOOGLE_RAG_CORPUS_DISPLAY_NAME")
    if display:
        # Ensure Vertex is initialized for list_corpora
        _maybe_init_vertex()
        for page in rag.list_corpora().pages:
            for corpus in page.rag_corpora:
                if getattr(corpus, "display_name", "") == display:
                    return corpus.name

    raise ValueError(
        "RAG corpus not configured. Set either:\n"
        "  - RAG_CORPUS=projects/…/locations/…/ragCorpora/…  (full resource name), or\n"
        "  - GOOGLE_RAG_CORPUS_DISPLAY_NAME=<your_corpus_display_name>  (will be resolved via list_corpora)"
    )


# Build the retrieval tool (mirrors ADK sample, renamed and tuned for physics notes)
ask_vertex_retrieval = VertexAiRagRetrieval(
    name="physics_rag_search",
    description=(
        "Retrieve short, high-signal physics/context snippets from the Vertex AI RAG corpus to "
        "explain weather mechanisms (e.g., heat waves, wind patterns, precipitation physics)."
    ),
    rag_resources=[
        rag.RagResource(rag_corpus=_resolve_rag_corpus())
    ],
    similarity_top_k=5,              # start tight; raise to 8–10 if recall is low
    vector_distance_threshold=0.5,   # filter weak matches; relax (e.g., 0.6) if too strict
)


# Keep the same ADK shape as the sample
physics_rag_agent = Agent(
    model="gemini-2.5-pro",
    name="physics_rag_agent",
    instruction=return_instructions_weather_rag(),
    tools=[ask_vertex_retrieval],
)

