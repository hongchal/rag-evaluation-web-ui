"""Query and Search Schemas"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.core.config import settings


class RetrievedChunk(BaseModel):
    """검색된 청크"""
    chunk_id: str = Field(..., description="Chunk ID in vector store")
    datasource_id: Optional[int] = Field(None, description="Data source ID (None for test pipelines)")
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
    top_k: int = Field(default_factory=lambda: settings.default_top_k, ge=1, le=100, description="Number of results to return")
    
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


class GenerationParamsRequest(BaseModel):
    """Generation parameters for answer generation"""
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Temperature (0=deterministic, 1=creative)")
    max_tokens: int = Field(default=1000, ge=100, le=4000, description="Maximum tokens to generate")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")


class ModelConfigRequest(BaseModel):
    """Model configuration for answer generation"""
    type: str = Field(..., description="Model type: 'claude' or 'vllm'")
    model_name: str = Field(..., description="Model name")
    api_key: Optional[str] = Field(None, description="API key for Claude")
    endpoint: Optional[str] = Field(None, description="Endpoint URL for vLLM")
    parameters: GenerationParamsRequest = Field(default_factory=GenerationParamsRequest, description="Generation parameters")
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ['claude', 'vllm']:
            raise ValueError("type must be 'claude' or 'vllm'")
        return v
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: Optional[str], info) -> Optional[str]:
        # Access other fields via info.data
        model_type = info.data.get('type')
        if model_type == 'claude' and not v:
            raise ValueError("api_key is required for Claude")
        if model_type == 'claude' and v and not v.startswith('sk-ant-'):
            raise ValueError("Invalid Claude API key format")
        return v
    
    @field_validator('endpoint')
    @classmethod
    def validate_endpoint(cls, v: Optional[str], info) -> Optional[str]:
        model_type = info.data.get('type')
        if model_type == 'vllm' and not v:
            raise ValueError("endpoint is required for vLLM")
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("endpoint must be a valid HTTP(S) URL")
        return v


class AnswerRequest(BaseModel):
    """답변 생성 요청 (검색 + LLM 생성)"""
    pipeline_id: int = Field(..., description="Pipeline ID for retrieval")
    query: str = Field(..., min_length=1, max_length=10000, description="User question")
    top_k: int = Field(default_factory=lambda: settings.default_top_k, ge=1, le=20, description="Number of chunks to retrieve")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt (overrides default)")
    llm_config: ModelConfigRequest = Field(..., description="Model configuration")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "pipeline_id": 1,
            "query": "What are the main features of the product?",
            "top_k": 10,
            "llm_config": {
                "type": "claude",
                "model_name": "claude-3-sonnet-20240229",
                "api_key": "sk-ant-xxxxx",
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "top_p": 0.9
                }
            }
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

