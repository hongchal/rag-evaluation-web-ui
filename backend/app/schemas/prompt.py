"""Pydantic schemas for prompt templates."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PromptTemplateBase(BaseModel):
    """Base schema for prompt template."""
    name: str = Field(..., min_length=1, max_length=255, description="Prompt template name")
    system_prompt: str = Field(..., min_length=1, description="System prompt content")
    description: Optional[str] = Field(None, description="Optional description")


class PromptTemplateCreate(PromptTemplateBase):
    """Schema for creating a new prompt template."""
    pass


class PromptTemplateUpdate(BaseModel):
    """Schema for updating a prompt template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    system_prompt: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None


class PromptTemplateResponse(PromptTemplateBase):
    """Schema for prompt template response."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptTemplateListResponse(BaseModel):
    """Schema for list of prompt templates."""
    total: int
    items: list[PromptTemplateResponse]

