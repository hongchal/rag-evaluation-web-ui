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


class SearchRequest(BaseModel):
    """검색 요청"""
    query: str = Field(..., min_length=1, description="Search query")
    rag_id: int = Field(..., description="RAG configuration ID to use")
    datasource_ids: Optional[List[int]] = Field(None, description="Filter by data source IDs (optional)")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "query": "What are the main features of the product?",
            "rag_id": 1,
            "datasource_ids": [1, 2],
            "top_k": 10
        }
    })


class SearchResponse(BaseModel):
    """검색 응답"""
    query: str
    rag_id: int
    results: List[RetrievedChunk]
    total: int = Field(..., description="Total number of results")
    retrieval_time: float = Field(..., description="Retrieval time in seconds")


class AnswerRequest(SearchRequest):
    """답변 생성 요청 (검색 + LLM 생성)"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "query": "What are the main features of the product?",
            "rag_id": 1,
            "datasource_ids": [1, 2],
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

