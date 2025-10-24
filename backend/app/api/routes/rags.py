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
)
from app.schemas.sync import SyncResponse

router = APIRouter(prefix="/api/v1/rags", tags=["rags"])


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
            chunking_module=rag_data.chunking_module,
            chunking_params=rag_data.chunking_params,
            embedding_module=rag_data.embedding_module,
            embedding_params=rag_data.embedding_params,
            reranking_module=rag_data.reranking_module,
            reranking_params=rag_data.reranking_params,
        )
        return RAGResponse.from_orm(rag)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[RAGResponse])
def list_rags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all RAG configurations."""
    rags = RAGService.list_rags(db, skip=skip, limit=limit)
    return [RAGResponse.from_orm(rag) for rag in rags]


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


@router.put("/{rag_id}", response_model=RAGResponse)
def update_rag(
    rag_id: int,
    rag_data: RAGUpdate,
    db: Session = Depends(get_db),
):
    """Update a RAG configuration."""
    try:
        rag = RAGService.update_rag(
            db=db,
            rag_id=rag_id,
            name=rag_data.name,
            description=rag_data.description,
            chunking_module=rag_data.chunking_module,
            chunking_params=rag_data.chunking_params,
            embedding_module=rag_data.embedding_module,
            embedding_params=rag_data.embedding_params,
            reranking_module=rag_data.reranking_module,
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
    success = RAGService.delete_rag(db, rag_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RAG configuration {rag_id} not found"
        )


@router.get("/{rag_id}/datasources", response_model=List[SyncResponse])
def get_rag_datasources(
    rag_id: int,
    db: Session = Depends(get_db),
):
    """Get all data sources synced with this RAG."""
    # Check if RAG exists
    rag = RAGService.get_rag(db, rag_id)
    if not rag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RAG configuration {rag_id} not found"
        )
    
    syncs = RAGService.get_datasources(db, rag_id)
    return [SyncResponse.from_orm(sync) for sync in syncs]

