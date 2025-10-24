"""Base chunker interface for all chunking implementations."""

from abc import ABC, abstractmethod
from typing import List

from app.models.base_chunk import BaseChunk
from app.models.base_document import BaseDocument


class BaseChunker(ABC):
    """
    Abstract base class for all chunkers.

    All chunking implementations (RecursiveChunker, SemanticChunker, etc.)
    must inherit from this class and implement the abstract methods.

    Common Attributes:
        chunk_size: Target chunk size in tokens
        chunk_overlap: Overlap between chunks in tokens
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 100):
        """
        Initialize base chunker.

        Args:
            chunk_size: Target chunk size in tokens (default: 512)
            chunk_overlap: Overlap between chunks in tokens (default: 100)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @abstractmethod
    def chunk_document(self, document: BaseDocument) -> List[BaseChunk]:
        """
        Split document into chunks.

        Args:
            document: Document to chunk (any subclass of BaseDocument)

        Returns:
            List of chunks (appropriate BaseChunk subclass)
        """
        pass

