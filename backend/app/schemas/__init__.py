"""Pydantic schemas for request/response validation."""

from app.schemas.rag import (
    RAGCreate,
    RAGUpdate,
    RAGResponse,
    RAGListResponse,
    ChunkingConfig,
    EmbeddingConfig,
    RerankingConfig,
)
from app.schemas.datasource import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    DataSourceListResponse,
    UploadResponse,
)
from app.schemas.dataset import (
    EvaluationDatasetUploadRequest,
    EvaluationDatasetCreate,
    EvaluationDatasetUpdate,
    EvaluationDatasetResponse,
    EvaluationDatasetDetail,
    EvaluationDatasetListResponse,
    QueryItem,
    DocumentItem,
)
from app.schemas.evaluation import (
    EvaluationCreate,
    CompareRequest,
    EvaluationResponse,
    ComparisonResponse,
    EvaluationListResponse,
    MetricsResponse,
)
from app.schemas.query import (
    SearchRequest,
    SearchResponse,
    AnswerRequest,
    AnswerResponse,
    RetrievedChunk,
)
from app.schemas.pipeline import (
    NormalPipelineCreate,
    TestPipelineCreate,
    PipelineUpdate,
    PipelineResponse,
    PipelineListResponse,
)

__all__ = [
    # RAG
    "RAGCreate",
    "RAGUpdate",
    "RAGResponse",
    "RAGListResponse",
    "ChunkingConfig",
    "EmbeddingConfig",
    "RerankingConfig",
    # DataSource
    "DataSourceCreate",
    "DataSourceUpdate",
    "DataSourceResponse",
    "DataSourceListResponse",
    "UploadResponse",
    # Dataset
    "EvaluationDatasetUploadRequest",
    "EvaluationDatasetCreate",
    "EvaluationDatasetUpdate",
    "EvaluationDatasetResponse",
    "EvaluationDatasetDetail",
    "EvaluationDatasetListResponse",
    "QueryItem",
    "DocumentItem",
    # Evaluation
    "EvaluationCreate",
    "CompareRequest",
    "EvaluationResponse",
    "ComparisonResponse",
    "EvaluationListResponse",
    "MetricsResponse",
    # Query
    "SearchRequest",
    "SearchResponse",
    "AnswerRequest",
    "AnswerResponse",
    "RetrievedChunk",
    # Pipeline
    "NormalPipelineCreate",
    "TestPipelineCreate",
    "PipelineUpdate",
    "PipelineResponse",
    "PipelineListResponse",
]

