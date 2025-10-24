"""Semantic Chunker using embedding similarity."""

import uuid
from datetime import datetime
from typing import List

import numpy as np
import structlog
import tiktoken
from app.chunking.chunkers.base_chunker import BaseChunker
from app.core.config import settings
from app.models.base_chunk import BaseChunk
from app.models.base_document import BaseDocument



logger = structlog.get_logger(__name__)


class SemanticChunker(BaseChunker):
    """
    Semantic Chunker using embedding similarity.

    Instead of fixed-size chunks, this creates chunks based on semantic boundaries.
    It splits text when the semantic similarity drops below a threshold.

    Benefits:
    - Better context preservation
    - No mid-sentence cuts
    - Higher retrieval accuracy (30-50% improvement)

    How it works:
    1. Split text into sentences
    2. Embed each sentence
    3. Calculate similarity between adjacent sentences
    4. Create chunk boundary when similarity drops below threshold
    """

    def __init__(
        self,
        embedder=None,
        chunk_size: int = None,
        chunk_overlap: int = None,
        similarity_threshold: float = 0.75,
        min_chunk_tokens: int = 100,
        max_chunk_tokens: int = 800
    ):
        """
        Initialize semantic chunker.

        Args:
            embedder: Embedder instance (required for semantic chunking)
            chunk_size: Target chunk size (default: from settings)
            chunk_overlap: Not used in semantic chunking (kept for compatibility)
            similarity_threshold: Threshold for creating chunk boundaries (0.0-1.0)
                                  Lower = more chunks, Higher = fewer chunks
            min_chunk_tokens: Minimum tokens per chunk
            max_chunk_tokens: Maximum tokens per chunk (force split if exceeded)
        """
        chunk_size = chunk_size if chunk_size is not None else settings.chunk_size
        chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        if embedder is None:
            raise ValueError("Embedder is required for semantic chunking")

        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.min_chunk_tokens = min_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens

        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning("tiktoken_init_failed", error=str(e))
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        logger.info(
            "semantic_chunker_initialized",
            similarity_threshold=similarity_threshold,
            min_tokens=min_chunk_tokens,
            max_tokens=max_chunk_tokens
        )

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Uses multiple delimiters to handle various sentence endings.
        """
        import re

        # Split on sentence boundaries (. ! ?) followed by space or newline
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)

        # Cosine similarity
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _create_semantic_chunks(self, sentences: List[str]) -> List[str]:
        """
        Create chunks based on semantic similarity.

        Process:
        1. Embed all sentences
        2. Calculate similarity between adjacent sentences
        3. Create chunk boundary when similarity drops
        """
        if not sentences:
            return []

        logger.info("embedding_sentences_for_semantic_chunking", count=len(sentences))

        # Embed all sentences (batch processing)
        embeddings_result = self.embedder.embed_texts(sentences)
        embeddings = embeddings_result["dense"]  # Use dense vectors for similarity

        # Calculate similarities between adjacent sentences
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._calculate_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)

        # Create chunks based on similarity drops
        chunks = []
        current_chunk = [sentences[0]]
        current_tokens = len(self.tokenizer.encode(sentences[0]))

        for i in range(1, len(sentences)):
            sentence = sentences[i]
            sentence_tokens = len(self.tokenizer.encode(sentence))

            # Check if we should start a new chunk
            should_split = False

            # Reason 1: Similarity drop below threshold
            if i - 1 < len(similarities) and similarities[i - 1] < self.similarity_threshold:
                should_split = True

            # Reason 2: Exceeding max chunk size
            if current_tokens + sentence_tokens > self.max_chunk_tokens:
                should_split = True

            if should_split and current_tokens >= self.min_chunk_tokens:
                # Finalize current chunk
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logger.info(
            "semantic_chunks_created",
            sentence_count=len(sentences),
            chunk_count=len(chunks),
            avg_similarity=sum(similarities) / len(similarities) if similarities else 0
        )

        return chunks

    def _create_chunk_for_document(
        self,
        document: BaseDocument,
        text: str,
        token_count: int,
        position: int,
        start_char: int,
        end_char: int
    ) -> BaseChunk:
        """Create chunk with semantic metadata."""
        # Build metadata
        metadata = {
            "chunk_method": "semantic",
            "num_tokens": token_count,
            "source_type": document.source_type,
            "filename": document.filename,
            "file_type": document.file_type,
        }
        
        # Add source-specific metadata
        if document.metadata:
            metadata.update(document.metadata)

        return BaseChunk(
            document_id=document.id,
            content=text,
            chunk_index=position,
            start_char=start_char,
            end_char=end_char,
            metadata=metadata
        )

    def chunk_document(self, document: BaseDocument) -> List[BaseChunk]:
        """
        Split document into semantic chunks.

        Args:
            document: Document to chunk

        Returns:
            List of BaseChunk with semantic boundaries
        """
        if not document.content.strip():
            logger.warning("empty_document", document_id=document.id)
            return []

        logger.info("semantic_chunking_document", document_id=document.id)

        try:
            # Enrich content with title
            enriched_content = f"# {document.title}\n\n{document.content}"

            # Split into sentences
            sentences = self._split_into_sentences(enriched_content)

            # Create semantic chunks
            chunk_texts = self._create_semantic_chunks(sentences)

            # Create chunk objects
            chunks = []
            char_offset = 0

            for i, text in enumerate(chunk_texts):
                if not text.strip():
                    continue

                token_count = len(self.tokenizer.encode(text))
                start_char = char_offset
                end_char = char_offset + len(text)
                char_offset = end_char

                chunk = self._create_chunk_for_document(
                    document=document,
                    text=text,
                    token_count=token_count,
                    position=i,
                    start_char=start_char,
                    end_char=end_char
                )
                chunks.append(chunk)

            logger.info(
                "semantic_chunking_completed",
                document_id=document.id,
                chunk_count=len(chunks),
                avg_tokens=sum(c.token_count for c in chunks) / len(chunks) if chunks else 0
            )

            return chunks

        except Exception as e:
            logger.error("semantic_chunking_failed", document_id=document.id, error=str(e))
            raise
