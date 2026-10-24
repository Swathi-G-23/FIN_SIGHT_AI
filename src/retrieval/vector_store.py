"""
FIN SIGHT AI - Vector Store
Provides a FAISS-backed vector store with a ChromaDB fallback option.
Abstracts the underlying store behind a common interface.
"""
import os
import time
import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import numpy as np

from src.utils.config import INDEXES_DIR
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class FAISSVectorStore:
    """
    FAISS-based vector store.

    Stores:
      - FAISS index (for similarity search)
      - Chunk texts and metadata (pickled alongside the index)
    """

    def __init__(self, document_id: str):
        self.document_id = document_id
        self.index_dir = INDEXES_DIR / document_id
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self._index = None
        self._chunks: List[Dict[str, Any]] = []   # {text, metadata}
        self._is_built = False

    # ------------------------------------------------------------------ #
    # Build / Load
    # ------------------------------------------------------------------ #

    def build(
        self,
        embeddings: np.ndarray,
        chunks: List[Any],   # List[TextChunk]
    ) -> None:
        """
        Build a FAISS index from pre-computed embeddings.

        Args:
            embeddings: float32 array of shape (N, dim).
            chunks: Corresponding TextChunk objects.
        """
        import faiss

        start = time.time()
        embeddings = embeddings.astype(np.float32)
        n, dim = embeddings.shape
        logger.info("Building FAISS index: %d vectors, dim=%d", n, dim)

        # Inner-product index (works for normalised vectors → cosine similarity)
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)

        # Store chunk data for retrieval
        self._chunks = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "text": c.text,
                "page_numbers": c.page_numbers,
                "chunk_index": c.chunk_index,
                "metadata": c.metadata,
            }
            for c in chunks
        ]

        self._is_built = True
        self._save()

        logger.info(
            "FAISS index built and saved: %d vectors, %.2fs",
            n, time.time() - start,
        )

    def _save(self) -> None:
        """Persist the index and chunk metadata to disk."""
        import faiss
        index_path = self.index_dir / "faiss.index"
        meta_path = self.index_dir / "chunks.pkl"

        faiss.write_index(self._index, str(index_path))
        with open(meta_path, "wb") as f:
            pickle.dump(self._chunks, f)
        logger.debug("Index saved to %s", self.index_dir)

    def load(self) -> bool:
        """
        Load a previously saved index from disk.
        Returns True if successful, False if no saved index exists.
        """
        import faiss
        index_path = self.index_dir / "faiss.index"
        meta_path = self.index_dir / "chunks.pkl"

        if not index_path.exists() or not meta_path.exists():
            return False

        try:
            self._index = faiss.read_index(str(index_path))
            with open(meta_path, "rb") as f:
                self._chunks = pickle.load(f)
            self._is_built = True
            logger.info("FAISS index loaded: %d vectors", self._index.ntotal)
            return True
        except Exception as exc:
            logger.error("Failed to load index: %s", exc)
            return False

    def index_exists(self) -> bool:
        """Check if a saved index exists for this document."""
        return (self.index_dir / "faiss.index").exists()

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for the most similar chunks.

        Args:
            query_embedding: 1-D float32 array (normalised).
            top_k: Number of results to return.

        Returns:
            List of dicts with 'text', 'metadata', 'score', 'page_numbers'.
        """
        if not self._is_built:
            raise RuntimeError("Index not built or loaded. Call build() or load() first.")

        query = query_embedding.astype(np.float32).reshape(1, -1)
        scores, indices = self._index.search(query, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._chunks):
                continue
            chunk = self._chunks[idx]
            results.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "page_numbers": chunk["page_numbers"],
                "metadata": chunk["metadata"],
                "score": float(score),
                "source": "semantic",
            })
        return results

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @property
    def all_chunks(self) -> List[Dict[str, Any]]:
        return self._chunks


class VectorStoreFactory:
    """Factory to create vector stores. Extend here to add ChromaDB."""

    @staticmethod
    def create(document_id: str, backend: str = "faiss") -> "FAISSVectorStore":
        if backend == "faiss":
            return FAISSVectorStore(document_id)
        elif backend == "chroma":
            raise NotImplementedError(
                "ChromaDB backend is available as a future extension. "
                "Install chromadb and implement ChromaVectorStore."
            )
        else:
            raise ValueError(f"Unknown vector store backend: {backend}")
