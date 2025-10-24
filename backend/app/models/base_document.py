"""Base Document model for all document types."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class BaseDocument:
    """
    Base document class for all document types (txt, pdf, json, etc.).
    
    Attributes:
        id: Unique document identifier
        content: Full text content of the document
        source_type: Type of source (file, url, database, etc.)
        source_uri: Original source location
        metadata: Additional metadata (filename, page_number, etc.)
        created_at: Document creation timestamp
    """
    id: str
    content: str
    source_type: str = "file"
    source_uri: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    @property
    def filename(self) -> Optional[str]:
        """Get filename from metadata."""
        return self.metadata.get("filename")
    
    @property
    def file_type(self) -> Optional[str]:
        """Get file type from metadata."""
        return self.metadata.get("file_type")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "source_type": self.source_type,
            "source_uri": self.source_uri,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

