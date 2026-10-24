"""
FIN SIGHT AI - Hybrid Retriever
Combines FAISS semantic search and BM25 keyword search using reciprocal rank fusion.
"""
import time
from typing import List, Dict, Any, Optional

import numpy as np

from src.retrieval.vector_store import FAISSVectorStore
from src.retrieval.keyword_search import KeywordSearcher
from src.retrieval.embeddings import EmbeddingGenerator
from src.utils.config import RETRIEVAL_TOP_K
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def _reciprocal_rank_fusion(
    semantic_results: List[Dict[str, Any]],
    keyword_results: List[Dict[str, Any]],
    k: int = 60,
    semantic_weight: float = 0.6,
    keyword_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Merge two ranked lists using Reciprocal Rank Fusion (RRF).

    Args:
        k: RRF constant (default 60 following the original paper).
        semantic_weight / keyword_weight: Relative weights.

    Returns:
        Merged, re-ranked list of chunk dicts.
    """
    scores: Dict[str, float] = {}
    chunks_by_id: Dict[str, Dict[str, Any]] = {}

    for rank, item in enumerate(semantic_results):
        cid = item["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + semantic_weight * (1.0 / (k + rank + 1))
        chunks_by_id[cid] = item

    for rank, item in enumerate(keyword_results):
        cid = item["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + keyword_weight * (1.0 / (k + rank + 1))
        chunks_by_id[cid] = item

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    merged = []
    for cid in sorted_ids:
        item = chunks_by_id[cid].copy()
        item["rrf_score"] = scores[cid]
        merged.append(item)
    return merged


class HybridRetriever:
    """
    Combines FAISS and BM25 retrieval with RRF re-ranking.

    Usage:
        retriever = HybridRetriever(vector_store, keyword_searcher, embedding_gen)
        results = retriever.retrieve("What is the total revenue?", top_k=5)
    """

    def __init__(
        self,
        vector_store: FAISSVectorStore,
        keyword_searcher: KeywordSearcher,
        embedding_generator: EmbeddingGenerator,
        top_k: int = RETRIEVAL_TOP_K,
    ):
        self.vector_store = vector_store
        self.keyword_searcher = keyword_searcher
        self.embedding_generator = embedding_generator
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant chunks for a query.

        Args:
            query: User's natural language question.
            top_k: Override default top_k if provided.

        Returns:
            Ranked list of chunk dicts with text, metadata, and scores.
        """
        k = top_k or self.top_k
        start = time.time()

        # 1. Semantic retrieval
        try:
            query_embedding = self.embedding_generator.embed_query(query)
            semantic_results = self.vector_store.search(query_embedding, top_k=k * 2)
        except Exception as exc:
            logger.error("Semantic retrieval failed: %s", exc)
            semantic_results = []

        # 2. Keyword retrieval
        try:
            keyword_results = self.keyword_searcher.search(query, top_k=k * 2)
        except Exception as exc:
            logger.error("Keyword retrieval failed: %s", exc)
            keyword_results = []

        # 3. Merge with RRF
        if semantic_results and keyword_results:
            merged = _reciprocal_rank_fusion(semantic_results, keyword_results)
        elif semantic_results:
            merged = semantic_results
        else:
            merged = keyword_results

        results = merged[:k]
        elapsed = time.time() - start
        logger.info(
            "Retrieval: query='%s…', semantic=%d, keyword=%d, merged=%d, time=%.2fs",
            query[:40], len(semantic_results), len(keyword_results), len(results), elapsed,
        )
        return results

    @staticmethod
    def format_context(results: List[Dict[str, Any]], max_chars: int = 6000) -> str:
        """
        Format retrieved chunks into a context string for the LLM.

        Args:
            results: List of chunk dicts from retrieve().
            max_chars: Maximum total character count.

        Returns:
            Formatted context string with page citations.
        """
        parts = []
        total_chars = 0
        for i, r in enumerate(results, 1):
            pages = r.get("page_numbers", [])
            page_ref = f"(Page {', '.join(str(p) for p in pages)})" if pages else ""
            chunk_text = f"[Excerpt {i}] {page_ref}\n{r['text']}"
            if total_chars + len(chunk_text) > max_chars:
                break
            parts.append(chunk_text)
            total_chars += len(chunk_text)
        return "\n\n---\n\n".join(parts)
