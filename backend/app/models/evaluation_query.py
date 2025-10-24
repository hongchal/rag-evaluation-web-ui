"""Evaluation Query Model - Individual queries in evaluation datasets"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship

from app.core.database import Base


class EvaluationQuery(Base):
    """평가 쿼리 모델 - 데이터셋의 개별 쿼리"""

    __tablename__ = "evaluation_queries"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Query content
    query = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    
    # Relevant documents (stored as JSON array of document IDs)
    relevant_doc_ids = Column(JSON, nullable=False, default=list)
    
    # Query metadata
    difficulty = Column(String(50), nullable=True)  # easy, medium, hard
    query_type = Column(String(100), nullable=True)  # single-hop, multi-hop, etc.
    extra_metadata = Column(JSON, nullable=True, default=dict)
    
    # Query index in original dataset
    query_idx = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    dataset = relationship("EvaluationDataset", back_populates="queries")
    
    def __repr__(self):
        return f"<EvaluationQuery(id={self.id}, dataset_id={self.dataset_id}, query='{self.query[:50]}...')>"

    def to_dict(self):
        """Convert to dictionary for evaluation"""
        return {
            "id": self.id,
            "query": self.query,
            "expected_answer": self.expected_answer,
            "relevant_doc_ids": self.relevant_doc_ids,
            "difficulty": self.difficulty,
            "query_type": self.query_type,
            "metadata": self.extra_metadata or {}
        }

