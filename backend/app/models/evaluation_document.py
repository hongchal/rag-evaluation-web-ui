"""Evaluation Document Model - Documents in evaluation datasets"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class EvaluationDocument(Base):
    """평가 문서 모델 - 데이터셋의 개별 문서"""

    __tablename__ = "evaluation_documents"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Document ID in the dataset (e.g., "frames_q0_doc0")
    doc_id = Column(String(255), nullable=False, index=True)
    
    # Document content
    content = Column(Text, nullable=False)
    title = Column(Text, nullable=True)  # Changed to Text to support long titles
    
    # Document metadata
    extra_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    dataset = relationship("EvaluationDataset", back_populates="documents")
    
    # Unique constraint on dataset_id + doc_id
    __table_args__ = (
        {'sqlite_autoincrement': True}
    )
    
    def __repr__(self):
        return f"<EvaluationDocument(id={self.id}, doc_id='{self.doc_id}', title='{self.title}')>"

    def to_dict(self):
        """Convert to dictionary for evaluation"""
        return {
            "id": self.doc_id,
            "content": self.content,
            "title": self.title,
            "metadata": self.extra_metadata or {}
        }

