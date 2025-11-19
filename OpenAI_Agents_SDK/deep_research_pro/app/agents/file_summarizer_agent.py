# file_summarizer_agent.py
import asyncio
import fitz  # PyMuPDF
import docx
from typing import List, Optional
from openai import AsyncOpenAI

from app.core.semantic_chunker import SemanticChunker
from app.schemas.source import SourceDoc

CHUNK_SUMMARY_MODEL = "gpt-4o-mini"  # Simple summarization task
FINAL_MERGE_MODEL = "gpt-4o-mini"  # Merging summaries is straightforward

class FileSummarizerAgent:
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.chunker = SemanticChunker(client)

    # --------- TEXT EXTRACTION ----------

    def extract_pdf(self, filepath: str) -> str:
        text = ""
        with fitz.open(filepath) as doc:
            for page in doc:
                text += page.get_text()
        return text

    def extract_docx(self, filepath: str) -> str:
        doc = docx.Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs])

    def extract_txt(self, filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def extract_text(self, filepath: str) -> str:
        filepath = filepath.lower()
        if filepath.endswith(".pdf"):
            return self.extract_pdf(filepath)
        elif filepath.endswith(".docx"):
            return self.extract_docx(filepath)
        elif filepath.endswith(".txt"):
            return self.extract_txt(filepath)
        else:
            raise ValueError(f"Unsupported file type: {filepath}")

    # --------- CHUNK SUMMARIZATION ----------

    async def summarize_chunk(self, chunk: str) -> str:
        prompt = f"""
Summarize the following document chunk into 5–7 sentences.
Keep only the most important factual information.

Chunk:
{chunk}
"""

        response = await self.client.chat.completions.create(
            model=CHUNK_SUMMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()

    async def merge_summaries(self, summaries: List[str]) -> str:
        prompt = f"""
You are merging multiple chunk summaries from the same document.
Output a single, coherent 1–2 paragraph executive summary.

Chunk Summaries:
{summaries}
"""

        response = await self.client.chat.completions.create(
            model=FINAL_MERGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    # --------- MAIN PIPELINE ----------

    async def process_file(self, filepath: str) -> SourceDoc:
        raw_text = self.extract_text(filepath)

        # Semantic chunking
        chunks = await self.chunker.create_chunks(raw_text)

        # Parallel chunk summarization
        try:
            chunk_summaries = await asyncio.gather(
                *(self.summarize_chunk(chunk) for chunk in chunks),
                return_exceptions=True
            )
            # Filter out exceptions and log them
            valid_summaries = []
            for i, summary in enumerate(chunk_summaries):
                if isinstance(summary, Exception):
                    # Log error but continue with other chunks
                    print(f"Warning: Failed to summarize chunk {i}: {summary}")
                else:
                    valid_summaries.append(summary)
            
            if not valid_summaries:
                raise ValueError("All chunk summarizations failed")
            
            chunk_summaries = valid_summaries
        except Exception as e:
            raise RuntimeError(f"Error during parallel chunk summarization: {e}")

        # Merge
        merged = await self.merge_summaries(chunk_summaries)

        # Return as SourceDoc
        # Use a valid URL format that clearly marks it as a user upload
        safe_filename = filepath.split('/')[-1].replace(' ', '_')
        url = f"https://user-upload.local/{safe_filename}"
        
        return SourceDoc(
            title=f"User File: {filepath.split('/')[-1]}",
            url=url,
            snippet=merged[:350],
            content=merged,
            published=None,
            source_type="file",
            provider="user-upload",
        )

