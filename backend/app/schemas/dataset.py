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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QueryItem(BaseModel):
    """평가 쿼리 항목"""
    query: str
    relevant_doc_ids: List[str]
    metadata: Optional[Dict[str, Any]] = None


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

