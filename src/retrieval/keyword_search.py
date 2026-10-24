"""
FIN SIGHT AI - Keyword Search (BM25)
Lightweight keyword-based retrieval using BM25 ranking.
"""
from typing import List, Dict, Any

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class KeywordSearcher:
    """
    BM25-based keyword retrieval over document chunks.
    Uses rank_bm25 for scoring.
    """

    def __init__(self):
        self._bm25 = None
        self._chunks: List[Dict[str, Any]] = []
        self._tokenized_corpus: List[List[str]] = []

    def build(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Build the BM25 index from a list of chunk dicts.

        Args:
            chunks: List of {'text': str, ...} dicts.
        """
        from rank_bm25 import BM25Okapi

        self._chunks = chunks
        self._tokenized_corpus = [
            self._tokenize(c["text"]) for c in chunks
        ]
        self._bm25 = BM25Okapi(self._tokenized_corpus)
        logger.info("BM25 index built: %d documents", len(chunks))

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for the most relevant chunks using BM25.

        Args:
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of result dicts with 'text', 'metadata', 'score', 'source'.
        """
        if self._bm25 is None:
            logger.warning("BM25 index not built. Returning empty results.")
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        # Get top-k indices by score
        import numpy as np
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            chunk = self._chunks[idx]
            results.append({
                "chunk_id": chunk.get("chunk_id", f"chunk_{idx}"),
                "text": chunk["text"],
                "page_numbers": chunk.get("page_numbers", []),
                "metadata": chunk.get("metadata", {}),
                "score": score,
                "source": "keyword",
            })
        return results

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace + lowercase tokenisation."""
        import re
        # Keep numbers and words
        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return tokens
