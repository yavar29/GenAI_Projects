import math, numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Chunk:
    id: str
    text: str
    meta: Dict[str, Any]

class VectorStore:
    def __init__(self):
        self.vecs = None          # np.ndarray [N, D]
        self.chunks: List[Chunk] = []

    def add(self, embeddings: np.ndarray, chunks: List[Chunk]):
        if self.vecs is None:
            self.vecs = embeddings
        else:
            self.vecs = np.vstack([self.vecs, embeddings])
        self.chunks.extend(chunks)

    def search(self, query_vec: np.ndarray, top_k: int = 4):
        if self.vecs is None or len(self.chunks) == 0:
            return []
        # cosine similarity
        q = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        m = self.vecs / (np.linalg.norm(self.vecs, axis=1, keepdims=True) + 1e-8)
        scores = (m @ q)
        idx = np.argsort(-scores)[:top_k]
        return [(float(scores[i]), self.chunks[i]) for i in idx]
