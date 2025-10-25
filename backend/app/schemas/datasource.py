"""Data Source Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DataSourceBase(BaseModel):
    """데이터 소스 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="Data source name")
    source_type: str = Field(..., description="Source type (file, url, database, api)")
    source_uri: str = Field(..., description="Source URI (file path, URL, etc.)")


class DataSourceCreate(DataSourceBase):
    """데이터 소스 생성 요청"""
    metadata: Optional[str] = Field(None, description="Additional metadata (JSON string)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Product Documentation",
            "source_type": "file",
            "source_uri": "/uploads/product_docs.pdf",
            "metadata": "{\"category\": \"documentation\", \"version\": \"1.0\"}"
        }
    })


class DataSourceUpdate(BaseModel):
    """데이터 소스 수정 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, description="Status (pending, active, inactive, error)")
    metadata: Optional[str] = None


class DataSourceResponse(DataSourceBase):
    """데이터 소스 응답"""
    id: int
    file_size: Optional[int] = None
    content_hash: Optional[str] = None
    status: str
    file_type: Optional[str] = Field(None, description="File extension (pdf, txt, json, etc.)")
    source_metadata: Optional[str] = Field(None, alias="source_metadata")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DataSourceListResponse(BaseModel):
    """데이터 소스 목록 응답"""
    total: int
    items: list[DataSourceResponse]


class UploadResponse(BaseModel):
    """파일 업로드 응답"""
    datasource_id: int
    filename: str
    file_size: int
    content_hash: str
    message: str = "File uploaded successfully"

