"""Data Source Sync Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SyncRequest(BaseModel):
    """동기화 요청"""
    rag_id: int = Field(..., description="RAG configuration ID")
    datasource_id: int = Field(..., description="Data source ID")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "rag_id": 1,
            "datasource_id": 1
        }
    })


class SyncStatus(BaseModel):
    """동기화 상태"""
    status: str = Field(..., description="Sync status (pending, processing, completed, failed)")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress (0.0 ~ 1.0)")
    current_step: str = Field(..., description="Current step (loading, chunking, embedding, indexing, completed)")


class SyncProgress(SyncStatus):
    """동기화 진행 상황 (실시간)"""
    num_chunks: int = Field(default=0, description="Number of chunks processed")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class SyncResponse(BaseModel):
    """동기화 응답"""
    id: int
    rag_id: int
    datasource_id: int
    status: str
    progress: float
    current_step: str
    num_chunks: int
    sync_time: Optional[float] = None
    memory_usage: Optional[float] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyncListResponse(BaseModel):
    """동기화 목록 응답"""
    total: int
    items: list[SyncResponse]

