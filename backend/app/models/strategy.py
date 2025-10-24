"""Strategy model for RAG configurations."""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Strategy(Base):
    """
    DEPRECATED: Use RAGConfiguration instead.
    
    This model is kept for backward compatibility with the existing web UI.
    New implementations should use RAGConfiguration which provides:
    - Qdrant collection management
    - Relationship with evaluations and syncs
    - Better naming (module instead of strategy)
    """

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    # Strategy components
    chunking_strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    chunking_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    embedding_strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    embedding_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    reranking_strategy: Mapped[str] = mapped_column(String(50), nullable=True)
    reranking_params: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name={self.name})>"
