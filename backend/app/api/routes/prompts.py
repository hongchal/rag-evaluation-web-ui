"""API routes for prompt template management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import structlog

from app.core.dependencies import get_db
from app.models.prompt import PromptTemplate
from app.schemas.prompt import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateListResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_prompt_template(
    prompt_data: PromptTemplateCreate,
    db: Session = Depends(get_db),
):
    """Create a new prompt template."""
    try:
        prompt = PromptTemplate(
            name=prompt_data.name,
            system_prompt=prompt_data.system_prompt,
            description=prompt_data.description,
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        
        logger.info("prompt_template_created", prompt_id=prompt.id, name=prompt.name)
        return prompt
        
    except Exception as e:
        db.rollback()
        logger.error("prompt_template_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create prompt template: {str(e)}"
        )


@router.get("", response_model=PromptTemplateListResponse)
def list_prompt_templates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all prompt templates."""
    prompts = db.query(PromptTemplate).order_by(PromptTemplate.created_at.desc()).offset(skip).limit(limit).all()
    total = db.query(PromptTemplate).count()
    
    return PromptTemplateListResponse(
        total=total,
        items=prompts
    )


@router.get("/{prompt_id}", response_model=PromptTemplateResponse)
def get_prompt_template(
    prompt_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific prompt template."""
    prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt template {prompt_id} not found"
        )
    
    return prompt


@router.put("/{prompt_id}", response_model=PromptTemplateResponse)
def update_prompt_template(
    prompt_id: int,
    prompt_data: PromptTemplateUpdate,
    db: Session = Depends(get_db),
):
    """Update a prompt template."""
    prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt template {prompt_id} not found"
        )
    
    try:
        # Update fields if provided
        if prompt_data.name is not None:
            prompt.name = prompt_data.name
        if prompt_data.system_prompt is not None:
            prompt.system_prompt = prompt_data.system_prompt
        if prompt_data.description is not None:
            prompt.description = prompt_data.description
        
        db.commit()
        db.refresh(prompt)
        
        logger.info("prompt_template_updated", prompt_id=prompt.id)
        return prompt
        
    except Exception as e:
        db.rollback()
        logger.error("prompt_template_update_failed", prompt_id=prompt_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompt template: {str(e)}"
        )


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt_template(
    prompt_id: int,
    db: Session = Depends(get_db),
):
    """Delete a prompt template."""
    prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt template {prompt_id} not found"
        )
    
    try:
        db.delete(prompt)
        db.commit()
        
        logger.info("prompt_template_deleted", prompt_id=prompt_id)
        
    except Exception as e:
        db.rollback()
        logger.error("prompt_template_deletion_failed", prompt_id=prompt_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete prompt template: {str(e)}"
        )

