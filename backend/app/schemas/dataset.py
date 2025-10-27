"""Evaluation Dataset Schemas"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class EvaluationDatasetBase(BaseModel):
    """평가 데이터셋 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")


class EvaluationDatasetUploadRequest(EvaluationDatasetBase):
    """데이터셋 업로드 요청"""
    dataset_uri: str = Field(..., description="Dataset file path (JSON)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Product QA Dataset",
            "description": "Questions and answers about products",
            "dataset_uri": "/datasets/product_qa.json"
        }
    })


class EvaluationDatasetCreate(EvaluationDatasetBase):
    """데이터셋 생성 요청"""
    dataset_uri: str
    num_queries: int = Field(default=0, ge=0)
    num_documents: int = Field(default=0, ge=0)


class EvaluationDatasetUpdate(BaseModel):
    """데이터셋 수정 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class EvaluationDatasetResponse(EvaluationDatasetBase):
    """데이터셋 응답"""
    id: int
    dataset_uri: str
    num_queries: int
    num_documents: int
    status: str = Field(..., description="Dataset status: downloading, ready, failed")
    download_error: Optional[str] = Field(None, description="Error message if download failed")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QueryItem(BaseModel):
    """평가 쿼리 항목"""
    query: str
    relevant_doc_ids: List[str]
    metadata: Optional[Dict[str, Any]] = None


class EvaluationQueryResponse(BaseModel):
    """평가 쿼리 상세 응답"""
    id: int
    dataset_id: int
    query: str
    expected_answer: Optional[str] = None
    relevant_doc_ids: List[str] = Field(default_factory=list)
    difficulty: Optional[str] = None
    query_type: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    query_idx: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationQueryListResponse(BaseModel):
    """평가 쿼리 목록 응답"""
    total: int
    items: List[EvaluationQueryResponse]


class DocumentItem(BaseModel):
    """평가 문서 항목"""
    doc_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class EvaluationDatasetDetail(EvaluationDatasetResponse):
    """데이터셋 상세 정보 (queries, documents 포함)"""
    queries: List[QueryItem] = Field(default_factory=list)
    documents: List[DocumentItem] = Field(default_factory=list)


class EvaluationDatasetListResponse(BaseModel):
    """데이터셋 목록 응답"""
    total: int
    items: List[EvaluationDatasetResponse]


class AvailableDatasetInfo(BaseModel):
    """다운로드 가능한 데이터셋 정보"""
    id: str = Field(..., description="Dataset identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Dataset description")
    size: str = Field(..., description="Dataset size (small, medium, large)")
    estimated_time: str = Field(..., description="Estimated download time")
    num_queries: int = Field(..., description="Number of queries")
    num_documents: int = Field(..., description="Number of documents")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "scifact",
            "name": "BEIR SciFact",
            "description": "Scientific fact verification dataset",
            "size": "small",
            "estimated_time": "30 seconds",
            "num_queries": 300,
            "num_documents": 5183
        }
    })


class DatasetDownloadRequest(BaseModel):
    """데이터셋 다운로드 요청"""
    dataset_id: str = Field(..., description="Dataset ID to download")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "dataset_id": "scifact"
        }
    })


class DatasetDownloadResponse(BaseModel):
    """데이터셋 다운로드 응답"""
    success: bool = Field(..., description="Whether download was successful")
    message: str = Field(..., description="Status message")
    dataset_id: Optional[int] = Field(None, description="Database ID of the downloaded dataset")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "Successfully downloaded and registered 'BEIR SciFact'",
            "dataset_id": 1
        }
    })

