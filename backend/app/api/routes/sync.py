"""Sync API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import structlog

from app.core.dependencies import get_db, get_qdrant_service
from app.services.sync_service import SyncService
from app.services.qdrant_service import QdrantService
from app.schemas.sync import (
    SyncRequest,
    SyncResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


def get_sync_service(
    db: Session = Depends(get_db),
    qdrant_service: QdrantService = Depends(get_qdrant_service)
) -> SyncService:
    """Dependency to get SyncService instance."""
    return SyncService(db, qdrant_service)


def _run_sync_task(sync_id: int, db: Session, qdrant_service: QdrantService):
    """Background task to run sync."""
    sync_service = SyncService(db, qdrant_service)
    try:
        sync_service.sync_datasource_by_id(sync_id)
    except Exception as e:
        logger.error("sync_task_failed", sync_id=sync_id, error=str(e))


@router.post("", response_model=SyncResponse, status_code=status.HTTP_202_ACCEPTED)
def start_sync(
    sync_request: SyncRequest,
    background_tasks: BackgroundTasks,
    sync_service: SyncService = Depends(get_sync_service),
):
    """Start synchronization of a data source with a RAG configuration."""
    try:
        # Validate inputs
        from app.models.rag import RAGConfiguration
        from app.models.datasource import DataSource
        from app.models.datasource_sync import DataSourceSync, SyncStatus
        
        rag = sync_service.db.query(RAGConfiguration).filter(
            RAGConfiguration.id == sync_request.rag_id
        ).first()
        if not rag:
            raise ValueError(f"RAG {sync_request.rag_id} not found")
        
        datasource = sync_service.db.query(DataSource).filter(
            DataSource.id == sync_request.datasource_id
        ).first()
        if not datasource:
            raise ValueError(f"DataSource {sync_request.datasource_id} not found")
        
        # Create initial sync record
        sync = DataSourceSync(
            rag_id=sync_request.rag_id,
            datasource_id=sync_request.datasource_id,
            status=SyncStatus.PENDING,
            progress=0.0,
            current_step="Queued",
        )
        sync_service.db.add(sync)
        sync_service.db.commit()
        sync_service.db.refresh(sync)
        
        # Run sync in background (pass sync_id)
        from app.core.database import SessionLocal
        background_tasks.add_task(
            _run_sync_task,
            sync.id,
            SessionLocal(),
            sync_service.qdrant_service,
        )
        
        logger.info("sync_queued", sync_id=sync.id)
        return SyncResponse.from_orm(sync)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("sync_start_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sync: {str(e)}"
        )


@router.get("", response_model=List[SyncResponse])
def list_syncs(
    rag_id: Optional[int] = None,
    datasource_id: Optional[int] = None,
    sync_service: SyncService = Depends(get_sync_service),
):
    """List all sync records with optional filters."""
    if rag_id:
        syncs = sync_service.get_syncs_by_rag(rag_id)
    elif datasource_id:
        syncs = sync_service.get_syncs_by_datasource(datasource_id)
    else:
        from app.models.datasource_sync import DataSourceSync
        syncs = sync_service.db.query(DataSourceSync).all()
    
    return [SyncResponse.from_orm(sync) for sync in syncs]


@router.get("/{sync_id}", response_model=SyncResponse)
def get_sync_status(
    sync_id: int,
    sync_service: SyncService = Depends(get_sync_service),
):
    """Get sync status by ID."""
    sync = sync_service.get_sync(sync_id)
    if not sync:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sync {sync_id} not found"
        )
    return SyncResponse.from_orm(sync)


@router.delete("/{sync_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sync(
    sync_id: int,
    sync_service: SyncService = Depends(get_sync_service),
):
    """Delete a sync record."""
    success = sync_service.delete_sync(sync_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sync {sync_id} not found"
        )
    logger.info("sync_deleted", sync_id=sync_id)


@router.post("/{sync_id}/rebuild", response_model=SyncResponse, status_code=status.HTTP_202_ACCEPTED)
def rebuild_sync(
    sync_id: int,
    background_tasks: BackgroundTasks,
    sync_service: SyncService = Depends(get_sync_service),
):
    """Rebuild/retry a failed sync."""
    try:
        sync = sync_service.get_sync(sync_id)
        if not sync:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sync {sync_id} not found"
            )
        
        # Run retry in background
        background_tasks.add_task(
            sync_service.retry_sync,
            sync_id,
        )
        
        # Update status to pending
        from app.models.datasource_sync import SyncStatus
        sync.status = SyncStatus.PENDING
        sync.progress = 0.0
        sync.current_step = "Queued for retry"
        sync.error_message = None
        sync_service.db.commit()
        sync_service.db.refresh(sync)
        
        logger.info("sync_rebuild_queued", sync_id=sync_id)
        
        return SyncResponse.from_orm(sync)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("sync_rebuild_failed", sync_id=sync_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild sync: {str(e)}"
        )

