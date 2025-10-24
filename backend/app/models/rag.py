"""RAG Configuration Model"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class RAGConfiguration(Base):
    """RAG 구성 모델 (청킹 + 임베딩 + 리랭킹)"""

    __tablename__ = "rag_configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Chunking configuration
    chunking_module = Column(String(100), nullable=False)  # recursive, hierarchical, semantic, late_chunking
    chunking_params = Column(JSON, nullable=False, default=dict)

    # Embedding configuration
    embedding_module = Column(String(100), nullable=False)  # bge_m3, matryoshka, vllm_http
    embedding_params = Column(JSON, nullable=False, default=dict)

    # Reranking configuration (필수)
    reranking_module = Column(String(100), nullable=False)  # cross_encoder, bm25, colbert, none
    reranking_params = Column(JSON, nullable=False, default=dict)

    # Qdrant collection name
    collection_name = Column(String(255), nullable=False, unique=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    syncs = relationship("DataSourceSync", back_populates="rag", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="rag", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RAGConfiguration(id={self.id}, name='{self.name}', collection='{self.collection_name}')>"

    @property
    def display_name(self) -> str:
        """표시용 이름"""
        return f"{self.name} ({self.chunking_module}/{self.embedding_module}/{self.reranking_module})"

