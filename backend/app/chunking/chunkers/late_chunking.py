"""Late Chunking Wrapper for Jina v3 embeddings.

This chunker wraps the JinaLocalLateChunkingEmbedder to provide
a unified interface compatible with the evaluation framework.
"""

from typing import List
import re
import structlog

from .base_chunker import BaseChunker
from app.models.base_chunk import BaseChunk
from app.models.base_document import BaseDocument

logger = structlog.get_logger(__name__)


class LateChunkingWrapper(BaseChunker):
    """
    Late Chunking Wrapper for evaluation framework.

    This chunker creates sentence-level chunks that will be embedded
    using the Jina Late Chunking technique (single forward pass per document).

    Note: The actual late chunking optimization happens in the embedder,
    but we still need to define the chunking boundaries here.
    """

    def __init__(
        self,
        sentences_per_chunk: int = 3,
        min_chunk_tokens: int = 50,
        max_chunk_tokens: int = 500,
        # Backward compatibility: accept chunk_size and ignore other common params
        chunk_size: int = None,
        chunk_overlap: int = None,
        **kwargs  # Ignore any other unexpected params
    ):
        """
        Initialize Late Chunking Wrapper.

        Args:
            sentences_per_chunk: Number of sentences to group per chunk
            min_chunk_tokens: Minimum tokens per chunk
            max_chunk_tokens: Maximum tokens per chunk
            chunk_size: (Optional) For compatibility - mapped to max_chunk_tokens
            chunk_overlap: (Optional) Ignored - kept for compatibility
            **kwargs: Additional parameters (ignored)
        """
        # Use chunk_size as max_chunk_tokens if provided
        if chunk_size is not None:
            max_chunk_tokens = chunk_size
        
        self.sentences_per_chunk = sentences_per_chunk
        self.min_chunk_tokens = min_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens

        logger.info(
            "initializing_late_chunking_wrapper",
            sentences_per_chunk=sentences_per_chunk,
            min_chunk_tokens=min_chunk_tokens,
            max_chunk_tokens=max_chunk_tokens,
        )

    def chunk_document(self, document: BaseDocument) -> List[BaseChunk]:
        """
        Chunk document into sentence groups for late chunking.

        Args:
            document: Document to chunk

        Returns:
            List of BaseChunks (sentence groups)
        """
        content = document.content

        # Split into sentences (simple heuristic)
        sentences = self._split_into_sentences(content)

        if not sentences:
            logger.warning("no_sentences_found", doc_id=document.id)
            return []

        # Group sentences
        sentence_groups = self._group_sentences(sentences)

        # Create chunks
        chunks = []
        for i, group_text in enumerate(sentence_groups):
            chunk = BaseChunk(
                document_id=document.id,
                content=group_text,
                chunk_index=i,
                metadata={
                    "chunk_method": "late_chunking",
                    "sentences_per_chunk": self.sentences_per_chunk,
                    "num_tokens": len(group_text.split()),  # Approximate
                    "source_type": document.source_type,
                    "filename": document.filename,
                    "file_type": document.file_type,
                },
            )
            chunks.append(chunk)

        logger.debug(
            "document_chunked_for_late_chunking",
            doc_id=document.id,
            num_chunks=len(chunks),
            num_sentences=len(sentences),
        )

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using simple heuristics.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with spacy/nltk)
        # Handles: ". ", "! ", "? ", but preserves "Dr.", "Mr.", etc.
        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_pattern, text)

        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _group_sentences(self, sentences: List[str]) -> List[str]:
        """
        Group sentences into chunks based on configuration.

        Args:
            sentences: List of sentences

        Returns:
            List of grouped sentence texts
        """
        groups = []
        current_group = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = len(sentence.split())

            # Check if adding this sentence would exceed max tokens
            if current_tokens + sentence_tokens > self.max_chunk_tokens and current_group:
                # Finalize current group
                groups.append(" ".join(current_group))
                current_group = [sentence]
                current_tokens = sentence_tokens
            else:
                # Add to current group
                current_group.append(sentence)
                current_tokens += sentence_tokens

                # Check if we've reached sentences_per_chunk
                if len(current_group) >= self.sentences_per_chunk:
                    # Check if we meet minimum token requirement
                    if current_tokens >= self.min_chunk_tokens:
                        groups.append(" ".join(current_group))
                        current_group = []
                        current_tokens = 0

        # Add remaining sentences
        if current_group:
            group_text = " ".join(current_group)
            # Merge with last group if too small
            if current_tokens < self.min_chunk_tokens and groups:
                groups[-1] = groups[-1] + " " + group_text
            else:
                groups.append(group_text)

        return groups

    def get_stats(self) -> dict:
        """Get chunker statistics."""
        return {
            "chunker_type": "late_chunking_wrapper",
            "sentences_per_chunk": self.sentences_per_chunk,
            "min_chunk_tokens": self.min_chunk_tokens,
            "max_chunk_tokens": self.max_chunk_tokens,
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"LateChunkingWrapper("
            f"sentences_per_chunk={self.sentences_per_chunk}, "
            f"min_tokens={self.min_chunk_tokens}, "
            f"max_tokens={self.max_chunk_tokens})"
        )
