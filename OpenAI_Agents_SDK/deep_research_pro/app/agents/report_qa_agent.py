# app/agents/report_qa_agent.py

from __future__ import annotations

from typing import Optional

from agents import Agent, ModelSettings
from openai import AsyncOpenAI

from app.core.safe import safe_run_async


class ReportQAAgent:
    """
    Answers follow-up questions based on the generated research report
    and its sources. This turns the static report into an interactive
    Q&A experience.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        openai_client: Optional[AsyncOpenAI] = None,
    ) -> None:
        # The Agents SDK reads auth from env; we keep openai_client for symmetry.
        self._client = openai_client

        self.agent = Agent(
            name="ReportQAAssistant",
            instructions=(
                "You are an assistant that answers questions based strictly on a given research report and its sources.\n\n"
                "You will receive:\n"
                "- The full markdown of the research report that was previously generated.\n"
                "- A list of sources with numeric IDs in the format [1], [2], ... (title, URL, type, published).\n"
                "- A follow-up question from the user.\n\n"
                "Your job:\n"
                "- Answer the question using ONLY information that can be reasonably inferred from the report and sources.\n"
                "- If the report already contains an answer, reuse and summarize it in a clearer, more direct way.\n"
                "- You may quote or paraphrase parts of the report, but keep the answer focused on the question.\n"
                "- If multiple sources in the list support your answer, use numeric citations like [1], [3].\n"
                "- If the information is not in the report or sources, say you cannot answer confidently instead of guessing.\n\n"
                "Section navigation:\n"
                "- The report is organized into sections with headings (e.g., '## Key Takeaways', '## Limitations & Open Questions').\n"
                "- When your answer is closely tied to a specific section, explicitly point the user to it using phrasing like:\n"
                "  'See section: Key Takeaways' or 'See section: Practical implications'.\n"
                "- Only reference section names that actually appear as headings in the report markdown. Do NOT invent new section titles.\n\n"
                "Formatting rules:\n"
                "- Use short sections, bullet lists, or numbered steps when helpful.\n"
                "- Keep responses concise but substantive: usually 3–8 short paragraphs or a paragraph plus a list.\n"
                "- Always ground specific factual statements in the report or sources.\n"
                "- Never invent new citations or refer to sources that are not listed.\n"
            ),
            model=model,
            model_settings=ModelSettings(
                temperature=0.25,
                max_output_tokens=1000,
            ),
        )

    async def answer_async(
        self,
        question: str,
        report_markdown: str,
        sources_text: str,
    ) -> str:
        """
        Answer a user question given the full report markdown and a textual
        representation of the sources table.
        """
        prompt = (
            f"User question:\n{question}\n\n"
            "Here is the full research report (in markdown):\n"
            "---------------- REPORT START ----------------\n"
            f"{report_markdown}\n"
            "---------------- REPORT END ------------------\n\n"
            "Here is the list of sources with numeric IDs:\n"
            "---------------- SOURCES ---------------------\n"
            f"{sources_text}\n"
            "----------------------------------------------\n\n"
            "Now answer the user's question based ONLY on this report and these sources. "
            "If the answer is not supported, say so explicitly."
        )

        result = await safe_run_async(self.agent, prompt, str)
        return (result or "").strip()

