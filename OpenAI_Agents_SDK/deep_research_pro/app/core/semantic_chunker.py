"""Semantic chunking: uses LLM to detect section boundaries and split text into natural chunks."""

from typing import List
from openai import AsyncOpenAI

TARGET_CHUNK_SIZE = 1800
MIN_CHUNK_SIZE = 900
OVERLAP = 150

class SemanticChunker:
    def __init__(self, client: AsyncOpenAI, model_name: str = "gpt-4o-mini"):
        self.client = client
        self.model_name = model_name

    async def detect_breakpoints(self, text: str) -> List[int]:
        """Use LLM to identify logical breakpoints (character indices) in text."""
        prompt = f"""
            You are a document-structure analysis model.
            Identify natural section boundaries in the following text.
            Return ONLY a list of integer indices (character offsets) where good splits occur.
            Prefer boundaries at:
            - New sections
            - Headings
            - Paragraph breaks
            - Topic shifts

            Text:
            {text[:12000]}

            Return format:
            [12, 89, 150, 2300, ...]
            """
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )



        try:
            # Evaluate string like "[12, 331, 1222]" into python list
            indices = eval(response.choices[0].message.content.strip())
            if not isinstance(indices, list):
                return []
            return [i for i in indices if isinstance(i, int)]
        except:
            return []



    def merge_close_points(self, points: List[int]) -> List[int]:
        """Merge breakpoints that are too close together."""
        if not points:
            return []
        points.sort()
        merged = [points[0]]
        for p in points[1:]:
            if p - merged[-1] > MIN_CHUNK_SIZE:
                merged.append(p)
        return merged

    def chunk_from_breakpoints(self, text: str, points: List[int]) -> List[str]:
        """Split text using detected breakpoints with overlap."""
        if not points:
            return [text]
        chunks = []
        last = 0

        for p in points:
            chunk = text[last:p].strip()
            if len(chunk) > MIN_CHUNK_SIZE:
                chunks.append(chunk)
                last = p

        final_chunk = text[last:].strip()
        if final_chunk:
            chunks.append(final_chunk)

        overlapped = []

        for i, c in enumerate(chunks):
            if i == 0:
                overlapped.append(c)
            else:
                prev = chunks[i - 1]
                overlap = prev[-OVERLAP:]
                overlapped.append(overlap + "\n" + c)
        return overlapped

    async def create_chunks(self, text: str) -> List[str]:
        """Full semantic chunking pipeline: detect breakpoints, merge, chunk."""

        if len(text) < TARGET_CHUNK_SIZE:
            return [text]

        points = await self.detect_breakpoints(text)
        points = self.merge_close_points(points)
        chunks = self.chunk_from_breakpoints(text, points)

        return chunks

