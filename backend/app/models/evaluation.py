"""Evaluation models for RAG performance testing."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, JSON, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Evaluation(Base):
    """Model for evaluation runs."""

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # References
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    strategy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategies.id"), nullable=False, index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, running, completed, failed, cancelled
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Evaluation(id={self.id}, name={self.name}, status={self.status})>"


class EvaluationResult(Base):
    """Model for evaluation results and metrics."""

    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    evaluation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluations.id"), nullable=False, index=True
    )

    # Metrics
    ndcg_at_k: Mapped[float] = mapped_column(Float, nullable=False)
    mrr: Mapped[float] = mapped_column(Float, nullable=False)
    precision_at_k: Mapped[float] = mapped_column(Float, nullable=False)
    recall_at_k: Mapped[float] = mapped_column(Float, nullable=False)
    hit_rate: Mapped[float] = mapped_column(Float, nullable=False)
    map_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Performance metrics
    chunking_time: Mapped[float] = mapped_column(Float, nullable=False)  # seconds
    embedding_time: Mapped[float] = mapped_column(Float, nullable=False)  # seconds
    retrieval_time: Mapped[float] = mapped_column(Float, nullable=False)  # seconds
    total_time: Mapped[float] = mapped_column(Float, nullable=False)  # seconds

    # Chunk statistics
    num_chunks: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_chunk_size: Mapped[float] = mapped_column(Float, nullable=False)

    # Additional data
    query_results: Mapped[dict] = mapped_column(
        JSON, nullable=True
    )  # Sample query results
    metadata: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<EvaluationResult(id={self.id}, evaluation_id={self.evaluation_id}, ndcg={self.ndcg_at_k:.4f})>"
