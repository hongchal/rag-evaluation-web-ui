"""Pipeline Model - RAG Configuration + DataSource(s) or Dataset"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Enum as SQLEnum, JSON, Float
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


# Many-to-Many relationship table for datasources
pipeline_datasources = Table(
    "pipeline_datasources",
    Base.metadata,
    Column("pipeline_id", Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), primary_key=True),
    Column("datasource_id", Integer, ForeignKey("datasources.id", ondelete="CASCADE"), primary_key=True),
)


class PipelineType(str, enum.Enum):
    """Pipeline 타입"""
    NORMAL = "normal"  # DataSource 기반 (일반 쿼리용)
    TEST = "test"      # EvaluationDataset 기반 (테스트용)


class PipelineStatus(str, enum.Enum):
    """Pipeline 인덱싱 상태"""
    PENDING = "pending"      # 생성됨, 인덱싱 대기 중
    INDEXING = "indexing"    # 인덱싱 진행 중
    READY = "ready"          # 인덱싱 완료, 사용 가능
    FAILED = "failed"        # 인덱싱 실패


class Pipeline(Base):
    """
    Pipeline: RAG Configuration + Data Source(s) OR Dataset
    
    두 가지 타입:
    1. Normal Pipeline (DataSource 기반):
       - RAG 설정 + 실제 데이터 소스
       - 일반적인 쿼리/검색용
    
    2. Test Pipeline (Dataset 기반):
       - RAG 설정 + 평가 데이터셋
       - 테스트용, Query 시 정답 청크와 비교 가능
    
    Query 시 pipeline_id 하나만으로 실행 가능합니다.
    """

    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Pipeline 타입
    pipeline_type = Column(SQLEnum(PipelineType), nullable=False, index=True)
    
    # RAG Configuration 참조
    rag_id = Column(
        Integer,
        ForeignKey("rag_configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Dataset 참조 (TEST 타입인 경우)
    dataset_id = Column(
        Integer,
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Indexing status
    status = Column(
        SQLEnum(PipelineStatus),
        nullable=False,
        default=PipelineStatus.PENDING,
        index=True
    )
    indexing_progress = Column(Float, nullable=True)  # 0.0 ~ 100.0
    indexing_stats = Column(JSON, nullable=True)  # {"total_docs": 10, "indexed_docs": 5, "total_chunks": 100}
    indexing_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    rag = relationship("RAGConfiguration", backref="pipelines")
    dataset = relationship("EvaluationDataset", backref="pipelines")
    datasources = relationship(
        "DataSource",
        secondary=pipeline_datasources,
        backref="pipelines"
    )

    def __repr__(self):
        return f"<Pipeline(id={self.id}, name='{self.name}', type={self.pipeline_type})>"

    @property
    def display_name(self) -> str:
        """표시용 이름"""
        if self.pipeline_type == PipelineType.NORMAL:
            datasource_count = len(self.datasources)
            return f"{self.name} (Normal, {datasource_count} datasources)"
        else:
            dataset_name = self.dataset.name if self.dataset else "Unknown"
            return f"{self.name} (Test, Dataset: {dataset_name})"
    
    @property
    def is_test_pipeline(self) -> bool:
        """테스트 파이프라인 여부"""
        return self.pipeline_type == PipelineType.TEST

