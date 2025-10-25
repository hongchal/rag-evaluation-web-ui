"""Evaluation Schemas"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class EvaluationCreate(BaseModel):
    """평가 생성 요청 (TEST 파이프라인 기반)
    
    단일 평가: pipeline_ids에 1개
    비교 평가: pipeline_ids에 2개 이상
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Evaluation name")
    description: Optional[str] = Field(None, description="Evaluation description")
    pipeline_ids: List[int] = Field(..., min_length=1, description="Test pipeline IDs (single or multiple)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "FRAMES Dataset Evaluation",
            "description": "Evaluate test pipeline with FRAMES dataset",
            "pipeline_ids": [1, 2, 3]
        }
    })


class CompareRequest(BaseModel):
    """Pipeline 비교 요청"""
    pipeline_ids: List[int] = Field(..., min_length=2, description="Test pipeline IDs to compare (2 or more)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "pipeline_ids": [1, 2, 3]
        }
    })


class MetricsResponse(BaseModel):
    """평가 메트릭 응답"""
    pipeline_id: Optional[int] = Field(None, description="Pipeline ID")
    pipeline_name: Optional[str] = Field(None, description="Pipeline name")
    
    ndcg_at_k: float = Field(..., description="NDCG@K score")
    mrr: float = Field(..., description="Mean Reciprocal Rank")
    precision_at_k: float = Field(..., description="Precision@K")
    recall_at_k: float = Field(..., description="Recall@K")
    hit_rate: float = Field(..., description="Hit Rate")
    map_score: float = Field(..., description="Mean Average Precision")
    
    # Performance metrics
    chunking_time: float = Field(..., description="Chunking time (seconds)")
    embedding_time: float = Field(..., description="Embedding time (seconds)")
    retrieval_time: float = Field(..., description="Retrieval time (seconds)")
    total_time: float = Field(..., description="Total time (seconds)")
    
    # Chunk statistics
    num_chunks: int = Field(..., description="Number of chunks")
    avg_chunk_size: float = Field(..., description="Average chunk size")

    model_config = ConfigDict(from_attributes=True)


class EvaluationResponse(BaseModel):
    """평가 응답"""
    id: int
    name: str
    description: Optional[str] = None
    pipeline_ids: List[int]
    status: str
    progress: float
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Include metrics if completed (list for multiple pipelines)
    metrics: Optional[List[MetricsResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class ComparisonResponse(BaseModel):
    """Pipeline 비교 응답 (metrics의 리스트로 통합)"""
    evaluation_id: int
    evaluation_name: str
    pipeline_count: int
    metrics: List[MetricsResponse]
    best_pipeline_id: Optional[int] = Field(None, description="Best performing pipeline ID")
    best_metric: Optional[str] = Field(None, description="Metric used for ranking")


class EvaluationListResponse(BaseModel):
    """평가 목록 응답"""
    total: int
    items: List[EvaluationResponse]

