"""Document model for uploaded files."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Document(Base):
    """
    Model for uploaded documents via web UI.
    
    This model stores metadata and content of files uploaded through the web interface.
    
    Note: This is different from BaseDocument (dataclass) which is used for runtime
    document representation in the evaluation system. BaseDocument is used when loading
    files from datasets or processing documents during evaluation.
    
    Usage:
    - Document (SQLAlchemy): File upload system, persistent storage
    - BaseDocument (dataclass): Runtime document processing, evaluation system
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    datasource_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("datasources.id", ondelete="CASCADE"), 
        nullable=True, 
        index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf, txt
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Extracted content
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    num_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    upload_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    datasource = relationship("DataSource", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, datasource_id={self.datasource_id})>"
