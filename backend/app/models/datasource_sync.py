"""Data Source Sync Model"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class SyncStatus(str, enum.Enum):
    """동기화 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncStep(str, enum.Enum):
    """동기화 단계"""
    LOADING = "loading"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"


class DataSourceSync(Base):
    """데이터 소스 동기화 기록 (어떤 RAG가 처리했는지)"""

    __tablename__ = "datasource_syncs"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    rag_id = Column(Integer, ForeignKey("rag_configurations.id", ondelete="CASCADE"), nullable=False, index=True)
    datasource_id = Column(Integer, ForeignKey("datasources.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status
    status = Column(SQLEnum(SyncStatus), default=SyncStatus.PENDING, nullable=False, index=True)
    progress = Column(Float, default=0.0, nullable=False)  # 0.0 ~ 1.0
    current_step = Column(SQLEnum(SyncStep), default=SyncStep.LOADING, nullable=False)

    # Metrics
    num_chunks = Column(Integer, default=0, nullable=False)
    sync_time = Column(Float, nullable=True)  # seconds
    memory_usage = Column(Float, nullable=True)  # MB

    # Error handling
    error_message = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    rag = relationship("RAGConfiguration", back_populates="syncs")
    datasource = relationship("DataSource", back_populates="syncs")

    # Unique constraint: 하나의 RAG는 하나의 DataSource를 한 번만 처리
    __table_args__ = (
        UniqueConstraint("rag_id", "datasource_id", name="uq_rag_datasource"),
    )

    def __repr__(self):
        return f"<DataSourceSync(id={self.id}, rag_id={self.rag_id}, datasource_id={self.datasource_id}, status='{self.status}')>"

