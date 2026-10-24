"""
FIN SIGHT AI - Embeddings
Generates and caches sentence embeddings using sentence-transformers.
"""
import time
import threading
from typing import List

import numpy as np

from src.utils.config import EMBEDDING_MODEL
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

_model_lock = threading.Lock()
_cached_model = None
_cached_model_name: str = ""


def _get_model(model_name: str = EMBEDDING_MODEL):
    """Return a cached SentenceTransformer model instance."""
    global _cached_model, _cached_model_name

    with _model_lock:
        if _cached_model is not None and _cached_model_name == model_name:
            return _cached_model

        logger.info("Loading embedding model: %s", model_name)
        start = time.time()
        from sentence_transformers import SentenceTransformer
        _cached_model = SentenceTransformer(model_name)
        _cached_model_name = model_name
        logger.info("Embedding model loaded in %.2fs", time.time() - start)
        return _cached_model


class EmbeddingGenerator:
    """Generate embeddings for text chunks."""

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            self._model = _get_model(self.model_name)

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 64,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of strings to embed.
            batch_size: Batch size for encoding.
            show_progress: Whether to show a progress bar.

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        self._ensure_model()
        start = time.time()
        logger.info("Generating embeddings for %d texts…", len(texts))

        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True,  # cosine similarity via dot product
        )
        elapsed = time.time() - start
        logger.info(
            "Embeddings generated: shape=%s, time=%.2fs",
            embeddings.shape, elapsed,
        )
        return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string."""
        self._ensure_model()
        vec = self._model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vec[0]

    @property
    def embedding_dim(self) -> int:
        self._ensure_model()
        return self._model.get_sentence_embedding_dimension()
