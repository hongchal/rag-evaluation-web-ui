"""Evaluation Schemas"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class EvaluationCreate(BaseModel):
    """평가 생성 요청"""
    name: str = Field(..., min_length=1, max_length=100, description="Evaluation name")
    description: Optional[str] = Field(None, description="Evaluation description")
    rag_id: int = Field(..., description="RAG configuration ID")
    dataset_id: int = Field(..., description="Evaluation dataset ID")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "BGE-M3 Evaluation",
            "description": "Evaluate BGE-M3 with product QA dataset",
            "rag_id": 1,
            "dataset_id": 1
        }
    })


class CompareRequest(BaseModel):
    """RAG 비교 요청"""
    rag_ids: List[int] = Field(..., min_length=2, description="List of RAG IDs to compare")
    dataset_id: int = Field(..., description="Evaluation dataset ID")
    name: Optional[str] = Field(None, description="Comparison name")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "rag_ids": [1, 2, 3],
            "dataset_id": 1,
            "name": "BGE-M3 vs Matryoshka vs VLLM"
        }
    })


class MetricsResponse(BaseModel):
    """평가 메트릭 응답"""
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
    rag_id: int
    dataset_id: int
    status: str
    progress: float
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Include metrics if completed
    metrics: Optional[MetricsResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ComparisonItem(BaseModel):
    """비교 항목"""
    rag_id: int
    rag_name: str
    evaluation_id: int
    metrics: MetricsResponse


class ComparisonResponse(BaseModel):
    """RAG 비교 응답"""
    dataset_id: int
    dataset_name: str
    comparisons: List[ComparisonItem]
    best_rag_id: Optional[int] = Field(None, description="Best performing RAG ID")
    best_metric: Optional[str] = Field(None, description="Metric used for ranking")


class EvaluationListResponse(BaseModel):
    """평가 목록 응답"""
    total: int
    items: List[EvaluationResponse]

