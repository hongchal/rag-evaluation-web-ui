"""DataSource API endpoints."""

from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import structlog

from app.core.dependencies import get_db
from app.core.config import settings
from app.models.datasource import DataSource, SourceType, SourceStatus
from app.services.file_processor import FileProcessor
from app.schemas.datasource import DataSourceResponse
from app.schemas.sync import SyncResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/datasources", tags=["datasources"])


@router.post("/upload", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_datasource(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a file as a data source."""
    # Validate file type
    allowed_extensions = {".txt", ".pdf", ".json"}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Compute hash
        content_hash = FileProcessor.compute_hash(content)
        
        # Check for duplicates
        existing = (
            db.query(DataSource)
            .filter(DataSource.content_hash == content_hash)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File already exists: {existing.name}"
            )
        
        # Save file
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = await FileProcessor.save_file(content, file.filename, upload_dir)
        
        # Create data source record
        datasource = DataSource(
            name=file.filename,
            source_type=SourceType.FILE,
            source_uri=str(file_path),
            file_size=file_size,
            content_hash=content_hash,
            status=SourceStatus.READY,
            metadata={
                "file_extension": file_extension,
                "original_filename": file.filename,
            }
        )
        
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        
        logger.info(
            "datasource_uploaded",
            datasource_id=datasource.id,
            name=datasource.name,
            size=file_size
        )
        
        return DataSourceResponse.from_orm(datasource)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("datasource_upload_failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("", response_model=List[DataSourceResponse])
def list_datasources(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all data sources."""
    datasources = db.query(DataSource).offset(skip).limit(limit).all()
    return [DataSourceResponse.from_orm(ds) for ds in datasources]


@router.get("/{datasource_id}", response_model=DataSourceResponse)
def get_datasource(
    datasource_id: int,
    db: Session = Depends(get_db),
):
    """Get a data source by ID."""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {datasource_id} not found"
        )
    return DataSourceResponse.from_orm(datasource)


@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_datasource(
    datasource_id: int,
    db: Session = Depends(get_db),
):
    """Delete a data source."""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {datasource_id} not found"
        )
    
    # Delete file if it exists
    try:
        file_path = Path(datasource.source_uri)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning(
            "datasource_file_deletion_failed",
            datasource_id=datasource_id,
            error=str(e)
        )
    
    db.delete(datasource)
    db.commit()
    
    logger.info("datasource_deleted", datasource_id=datasource_id)


@router.get("/{datasource_id}/syncs", response_model=List[SyncResponse])
def get_datasource_syncs(
    datasource_id: int,
    db: Session = Depends(get_db),
):
    """Get all sync records for a data source."""
    # Check if datasource exists
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {datasource_id} not found"
        )
    
    from app.models.datasource_sync import DataSourceSync
    syncs = (
        db.query(DataSourceSync)
        .filter(DataSourceSync.datasource_id == datasource_id)
        .all()
    )
    return [SyncResponse.from_orm(sync) for sync in syncs]

