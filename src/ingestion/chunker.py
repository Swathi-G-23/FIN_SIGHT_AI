"""
FIN SIGHT AI - Text Chunker
Splits cleaned text into overlapping chunks while preserving page metadata.
"""
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any

from src.utils.config import CHUNK_SIZE, CHUNK_OVERLAP
from src.utils.logging_config import get_logger
from src.ingestion.text_cleaner import clean_text

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """A single text chunk with metadata."""
    chunk_id: str            # unique identifier: "{doc_id}_chunk_{idx}"
    document_id: str
    text: str
    page_numbers: List[int]  # pages this chunk spans
    chunk_index: int
    char_start: int
    char_end: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class TextChunker:
    """
    Split document text into overlapping chunks.

    Strategy:
    - Split full text at page boundaries first.
    - Within each page, split by paragraphs, then by character count.
    - Overlap by repeating the last N characters of the previous chunk.
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(
        self,
        document_id: str,
        pages: List[Any],  # List[PageContent]
        doc_metadata: Dict[str, Any] | None = None,
    ) -> List[TextChunk]:
        """
        Chunk a document's pages into overlapping TextChunk objects.

        Args:
            document_id: Unique identifier for this document.
            pages: List of PageContent objects from the PDF extractor.
            doc_metadata: Optional document-level metadata.

        Returns:
            List of TextChunk objects.
        """
        start = time.time()
        doc_metadata = doc_metadata or {}

        # Build page-aware segments
        segments: List[Dict[str, Any]] = []
        for page in pages:
            cleaned = clean_text(page.text)
            if not cleaned.strip():
                continue
            segments.append({
                "page_number": page.page_number,
                "text": cleaned,
            })

        chunks = self._create_chunks(document_id, segments, doc_metadata)
        elapsed = time.time() - start

        logger.info(
            "Chunking complete: %d pages -> %d chunks (%.2fs)",
            len(pages), len(chunks), elapsed,
        )
        return chunks

    def _create_chunks(
        self,
        document_id: str,
        segments: List[Dict[str, Any]],
        doc_metadata: Dict[str, Any],
    ) -> List[TextChunk]:
        """
        Create overlapping chunks from page segments.
        """
        chunks: List[TextChunk] = []
        chunk_index = 0
        carry_over = ""  # overlap text from previous chunk

        for seg in segments:
            page_num = seg["page_number"]
            text = (carry_over + "\n" + seg["text"]).strip() if carry_over else seg["text"]

            # Split into sub-chunks within this page
            sub_chunks = self._split_text(text, self.chunk_size)

            for i, sub_text in enumerate(sub_chunks):
                if not sub_text.strip():
                    continue

                chunk = TextChunk(
                    chunk_id=f"{document_id}_chunk_{chunk_index}",
                    document_id=document_id,
                    text=sub_text,
                    page_numbers=[page_num],
                    chunk_index=chunk_index,
                    char_start=0,  # relative positions within page
                    char_end=len(sub_text),
                    metadata={
                        **doc_metadata,
                        "page_number": page_num,
                        "sub_chunk_index": i,
                    },
                )
                chunks.append(chunk)
                chunk_index += 1

            # Carry over the tail of this page's text as overlap
            full_page_text = seg["text"]
            if len(full_page_text) > self.chunk_overlap:
                carry_over = full_page_text[-self.chunk_overlap:]
            else:
                carry_over = full_page_text

        return chunks

    def _split_text(self, text: str, max_size: int) -> List[str]:
        """
        Split text into chunks of at most max_size characters.
        Attempts to split on paragraph or sentence boundaries first.
        """
        if len(text) <= max_size:
            return [text]

        sub_chunks: List[str] = []
        # Try to split on double-newlines (paragraphs)
        paragraphs = text.split("\n\n")

        current = ""
        for para in paragraphs:
            if len(current) + len(para) + 2 <= max_size:
                current = (current + "\n\n" + para).strip() if current else para
            else:
                if current:
                    sub_chunks.append(current)
                # If single paragraph is too long, split by sentences
                if len(para) > max_size:
                    sub_chunks.extend(self._split_by_sentence(para, max_size))
                    current = ""
                else:
                    current = para

        if current:
            sub_chunks.append(current)

        return sub_chunks if sub_chunks else [text[:max_size]]

    def _split_by_sentence(self, text: str, max_size: int) -> List[str]:
        """Fall-back: split by sentence, then by character."""
        import re
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: List[str] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) + 1 <= max_size:
                current = (current + " " + sent).strip()
            else:
                if current:
                    chunks.append(current)
                if len(sent) > max_size:
                    # Hard split
                    for i in range(0, len(sent), max_size):
                        chunks.append(sent[i:i + max_size])
                    current = ""
                else:
                    current = sent
        if current:
            chunks.append(current)
        return chunks
