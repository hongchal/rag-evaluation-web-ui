"""Query and Search Schemas"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class RetrievedChunk(BaseModel):
    """검색된 청크"""
    chunk_id: str = Field(..., description="Chunk ID in vector store")
    datasource_id: int = Field(..., description="Data source ID")
    content: str = Field(..., description="Chunk content")
    score: float = Field(..., description="Relevance score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_golden: Optional[bool] = Field(None, description="Whether this chunk is a golden (ground truth) chunk")


class QueryComparison(BaseModel):
    """Test Pipeline 쿼리 결과 비교"""
    query_id: int = Field(..., description="Query ID from dataset")
    query_text: str
    golden_doc_ids: List[str] = Field(..., description="Golden document IDs")
    retrieved_doc_ids: List[str] = Field(..., description="Retrieved document IDs")
    precision_at_k: float = Field(..., description="Precision@K")
    recall_at_k: float = Field(..., description="Recall@K")
    hit_rate: float = Field(..., description="Hit rate (1 if any golden doc retrieved, 0 otherwise)")


class SearchRequest(BaseModel):
    """검색 요청"""
    query: str = Field(..., min_length=1, description="Search query")
    pipeline_id: int = Field(..., description="Pipeline ID to use (includes RAG + DataSources)")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "query": "What are the main features of the product?",
            "pipeline_id": 1,
            "top_k": 10
        }
    })


class SearchResponse(BaseModel):
    """검색 응답"""
    query: str
    pipeline_id: int
    pipeline_type: str = Field(..., description="Pipeline type (normal or test)")
    results: List[RetrievedChunk]
    total: int = Field(..., description="Total number of results")
    retrieval_time: float = Field(..., description="Retrieval time in seconds")
    comparison: Optional[QueryComparison] = Field(None, description="Comparison with golden chunks (test pipelines only)")


class AnswerRequest(SearchRequest):
    """답변 생성 요청 (검색 + LLM 생성)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "query": "What are the main features of the product?",
            "pipeline_id": 1,
            "top_k": 5
        }
    })


class AnswerResponse(BaseModel):
    """답변 생성 응답"""
    query: str
    answer: str = Field(..., description="Generated answer")
    sources: List[RetrievedChunk] = Field(..., description="Source chunks used for answer")
    tokens_used: int = Field(..., description="Number of tokens used")
    generation_time: float = Field(..., description="Total time in seconds")
    retrieval_time: float = Field(..., description="Retrieval time in seconds")
    llm_time: float = Field(..., description="LLM generation time in seconds")

