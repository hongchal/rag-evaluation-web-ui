"""RAG API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.rag_service import RAGService
from app.schemas.rag import (
    RAGCreate,
    RAGUpdate,
    RAGResponse,
    RAGListResponse,
)

router = APIRouter(prefix="/api/rags", tags=["rags"])


@router.post("", response_model=RAGResponse, status_code=status.HTTP_201_CREATED)
def create_rag(
    rag_data: RAGCreate,
    db: Session = Depends(get_db),
):
    """Create a new RAG configuration."""
    try:
        rag = RAGService.create_rag(
            db=db,
            name=rag_data.name,
            description=rag_data.description,
            chunking_module=rag_data.chunking.module,
            chunking_params=rag_data.chunking.params,
            embedding_module=rag_data.embedding.module,
            embedding_params=rag_data.embedding.params,
            reranking_module=rag_data.reranking.module,
            reranking_params=rag_data.reranking.params,
        )
        return RAGResponse.from_orm(rag)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=RAGListResponse)
def list_rags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all RAG configurations."""
    rags = RAGService.list_rags(db, skip=skip, limit=limit)
    items = [RAGResponse.from_orm(rag) for rag in rags]
    return RAGListResponse(total=len(items), items=items)


@router.get("/{rag_id}", response_model=RAGResponse)
def get_rag(
    rag_id: int,
    db: Session = Depends(get_db),
):
    """Get a RAG configuration by ID."""
    rag = RAGService.get_rag(db, rag_id)
    if not rag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RAG configuration {rag_id} not found"
        )
    return RAGResponse.from_orm(rag)


@router.patch("/{rag_id}", response_model=RAGResponse)
def update_rag(
    rag_id: int,
    rag_data: RAGUpdate,
    db: Session = Depends(get_db),
):
    """
    Update RAG configuration (파라미터만 수정 가능).
    
    수정 가능:
    - name, description
    - embedding_params (예: model_name, base_url 등)
    - chunking_params, reranking_params
    
    수정 불가:
    - 모듈 타입 (chunking_module, embedding_module, reranking_module)
    """
    try:
        rag = RAGService.update_rag(
            db=db,
            rag_id=rag_id,
            name=rag_data.name,
            description=rag_data.description,
            chunking_params=rag_data.chunking_params,
            embedding_params=rag_data.embedding_params,
            reranking_params=rag_data.reranking_params,
        )
        if not rag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"RAG configuration {rag_id} not found"
            )
        return RAGResponse.from_orm(rag)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{rag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rag(
    rag_id: int,
    db: Session = Depends(get_db),
):
    """Delete a RAG configuration."""
    try:
        success = RAGService.delete_rag(db, rag_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"RAG configuration {rag_id} not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

