"""Base Chunk model for all chunk types."""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class BaseChunk:
    """
    Base chunk class for all chunking strategies.
    
    Attributes:
        document_id: Parent document ID
        content: Chunk text content
        chunk_index: Index of chunk within document
        id: Unique chunk identifier (format: {document_id}_{chunk_index})
        start_char: Start character position in original document
        end_char: End character position in original document
        metadata: Additional metadata (tokens, overlap, etc.)
    """
    document_id: str
    content: str
    chunk_index: int
    id: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        
        # Auto-generate ID if not provided
        if self.id is None:
            self.id = f"{self.document_id}_{self.chunk_index}"
    
    @property
    def num_tokens(self) -> Optional[int]:
        """Get number of tokens from metadata."""
        return self.metadata.get("num_tokens")
    
    @property
    def chunk_type(self) -> Optional[str]:
        """Get chunk type from metadata."""
        return self.metadata.get("chunk_type", "default")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "metadata": self.metadata,
        }

