"""Pydantic schemas for chat sessions and messages."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatMessageBase(BaseModel):
    """Base chat message schema."""
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Retrieved sources for assistant messages")
    tokens_used: Optional[int] = Field(None, description="Tokens used for generation")
    generation_time: Optional[float] = Field(None, description="Time taken to generate response")


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a chat message."""
    pass


class ChatMessageResponse(ChatMessageBase):
    """Schema for chat message response."""
    id: int
    session_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ChatSessionBase(BaseModel):
    """Base chat session schema."""
    title: str = Field(..., min_length=1, max_length=255, description="Session title")
    pipeline_id: int = Field(..., description="Pipeline ID used in this session")
    model_type: str = Field(..., description="Model type (claude or vllm)")
    model_name: str = Field(..., description="Model name")
    llm_config: Optional[Dict[str, Any]] = Field(None, description="Full model configuration")


class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a chat session."""
    messages: List[ChatMessageCreate] = Field(default_factory=list, description="Initial messages")


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    messages: Optional[List[ChatMessageCreate]] = None


class ChatSessionResponse(ChatSessionBase):
    """Schema for chat session response."""
    id: int
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


class ChatSessionListResponse(BaseModel):
    """Schema for chat session list response."""
    id: int
    title: str
    pipeline_id: int
    model_type: str
    model_name: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

