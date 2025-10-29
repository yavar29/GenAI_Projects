import math, numpy as np
import faiss
import pickle
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class Chunk:
    id: str
    text: str
    meta: Dict[str, Any]

class VectorStore:
    def __init__(self, persist_dir: str = "vector_store"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True)
        
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunks: List[Chunk] = []
        self.dimension: Optional[int] = None
        
        # Try to load existing store
        self._load_from_disk()

    def _get_index_path(self) -> Path:
        return self.persist_dir / "faiss_index.bin"
    
    def _get_chunks_path(self) -> Path:
        return self.persist_dir / "chunks.pkl"
    
    def _get_metadata_path(self) -> Path:
        return self.persist_dir / "metadata.pkl"

    def _load_from_disk(self):
        """Load existing FAISS index and chunks from disk"""
        index_path = self._get_index_path()
        chunks_path = self._get_chunks_path()
        metadata_path = self._get_metadata_path()
        
        if all(path.exists() for path in [index_path, chunks_path, metadata_path]):
            try:
                # Load FAISS index
                self.index = faiss.read_index(str(index_path))
                self.dimension = self.index.d
                
                # Load chunks
                with open(chunks_path, 'rb') as f:
                    self.chunks = pickle.load(f)
                
                # Load metadata
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                    print(f"[FAISS] Loaded existing vector store: {len(self.chunks)} chunks, dimension {self.dimension}")
                
            except Exception as e:
                print(f"[FAISS] Error loading existing store: {e}")
                self.index = None
                self.chunks = []
                self.dimension = None

    def _save_to_disk(self):
        """Save FAISS index and chunks to disk"""
        if self.index is None or len(self.chunks) == 0:
            return
            
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self._get_index_path()))
            
            # Save chunks
            with open(self._get_chunks_path(), 'wb') as f:
                pickle.dump(self.chunks, f)
            
            # Save metadata
            metadata = {
                "chunk_count": len(self.chunks),
                "dimension": self.dimension,
                "index_type": "faiss_flat_ip"
            }
            with open(self._get_metadata_path(), 'wb') as f:
                pickle.dump(metadata, f)
                
            print(f"[FAISS] Saved vector store: {len(self.chunks)} chunks to {self.persist_dir}")
            
        except Exception as e:
            print(f"[FAISS] Error saving store: {e}")

    def add(self, embeddings: np.ndarray, chunks: List[Chunk]):
        """Add new embeddings and chunks to the store"""
        if len(embeddings) == 0 or len(chunks) == 0:
            return
            
        # Initialize index if first time
        if self.index is None:
            self.dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
            print(f"[FAISS] Created new index with dimension {self.dimension}")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings.astype('float32'))
        
        # Add to chunks list
        self.chunks.extend(chunks)
        
        # Save to disk
        self._save_to_disk()

    def search(self, query_vec: np.ndarray, top_k: int = 4):
        """Search for similar chunks using FAISS"""
        if self.index is None or len(self.chunks) == 0:
            return []
        
        # Normalize query vector for cosine similarity
        faiss.normalize_L2(query_vec.reshape(1, -1))
        
        # Search using FAISS
        scores, indices = self.index.search(query_vec.reshape(1, -1).astype('float32'), top_k)
        
        # Return results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.chunks):  # Valid index
                results.append((float(score), self.chunks[idx]))
        
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        return {
            "chunk_count": len(self.chunks),
            "dimension": self.dimension,
            "index_type": "faiss_flat_ip" if self.index else None,
            "persist_dir": str(self.persist_dir),
            "is_loaded": self.index is not None
        }

    def clear(self):
        """Clear the vector store and remove persisted files"""
        self.index = None
        self.chunks = []
        self.dimension = None
        
        # Remove persisted files
        for path in [self._get_index_path(), self._get_chunks_path(), self._get_metadata_path()]:
            if path.exists():
                path.unlink()
        
        print("[FAISS] Cleared vector store")

# Legacy compatibility - keep the old interface working
def create_vector_store() -> VectorStore:
    """Create a new VectorStore instance"""
    return VectorStore()