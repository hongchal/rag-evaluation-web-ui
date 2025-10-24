"""Evaluation Dataset Model"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class EvaluationDataset(Base):
    """평가 데이터셋 모델"""

    __tablename__ = "evaluation_datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Dataset file path (JSON)
    dataset_uri = Column(Text, nullable=False)

    # Metadata
    num_queries = Column(Integer, default=0, nullable=False)
    num_documents = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    evaluations = relationship("Evaluation", back_populates="dataset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<EvaluationDataset(id={self.id}, name='{self.name}', queries={self.num_queries})>"

