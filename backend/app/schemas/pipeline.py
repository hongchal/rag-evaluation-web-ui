"""Pipeline Schemas"""
from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PipelineBase(BaseModel):
    """Pipeline 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")


class NormalPipelineCreate(PipelineBase):
    """Normal Pipeline 생성 요청 (DataSource 기반)"""
    pipeline_type: Literal["normal"] = "normal"
    rag_id: int = Field(..., description="RAG configuration ID")
    datasource_ids: List[int] = Field(..., min_length=1, description="Data source IDs to include")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Product Documentation Pipeline",
            "description": "RAG pipeline for product documentation with multiple sources",
            "pipeline_type": "normal",
            "rag_id": 1,
            "datasource_ids": [1, 2, 3]
        }
    })


class TestPipelineCreate(PipelineBase):
    """Test Pipeline 생성 요청 (EvaluationDataset 기반)"""
    pipeline_type: Literal["test"] = "test"
    rag_id: int = Field(..., description="RAG configuration ID")
    dataset_id: int = Field(..., description="Evaluation dataset ID")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "FRAMES Test Pipeline",
            "description": "Test pipeline for FRAMES dataset evaluation",
            "pipeline_type": "test",
            "rag_id": 1,
            "dataset_id": 1
        }
    })


class PipelineUpdate(BaseModel):
    """Pipeline 업데이트 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    datasource_ids: Optional[List[int]] = Field(None, min_length=1, description="Update data sources")


class DataSourceInfo(BaseModel):
    """Pipeline에 포함된 DataSource 정보"""
    id: int
    name: str
    source_type: str
    status: str
    
    model_config = ConfigDict(from_attributes=True)


class RAGConfigInfo(BaseModel):
    """Pipeline에 포함된 RAG 설정 정보"""
    id: int
    name: str
    chunking_module: str
    embedding_module: str
    reranking_module: str
    collection_name: str
    
    model_config = ConfigDict(from_attributes=True)


class DatasetInfo(BaseModel):
    """Pipeline에 포함된 Dataset 정보"""
    id: int
    name: str
    description: Optional[str]
    query_count: int = Field(..., alias="num_queries")
    document_count: int = Field(..., alias="num_documents")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PipelineResponse(PipelineBase):
    """Pipeline 응답"""
    id: int
    pipeline_type: str
    rag_id: int
    dataset_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # Nested objects
    rag: RAGConfigInfo
    datasources: List[DataSourceInfo] = []
    dataset: Optional[DatasetInfo] = None
    
    model_config = ConfigDict(from_attributes=True)


class PipelineListResponse(BaseModel):
    """Pipeline 목록 응답"""
    total: int
    items: List[PipelineResponse]

