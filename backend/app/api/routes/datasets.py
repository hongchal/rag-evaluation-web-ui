"""EvaluationDataset API endpoints."""

from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import structlog
import json

from app.core.dependencies import get_db
from app.core.config import settings
from app.models.evaluation_dataset import EvaluationDataset
from app.services.file_processor import FileProcessor
from app.schemas.dataset import (
    EvaluationDatasetResponse,
    EvaluationDatasetCreate,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.post("/upload", response_model=EvaluationDatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a JSON file as an evaluation dataset."""
    # Validate file type
    if not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JSON files are supported"
        )
    
    try:
        # Read and parse JSON
        content = await file.read()
        dataset_data = json.loads(content)
        
        # Validate structure
        if "queries" not in dataset_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset must contain 'queries' field"
            )
        
        # Save file
        upload_dir = Path(settings.upload_dir) / "datasets"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Count queries and documents
        num_queries = len(dataset_data.get("queries", []))
        num_documents = len(dataset_data.get("corpus", {}))
        
        # Create dataset record
        dataset = EvaluationDataset(
            name=file.filename.replace('.json', ''),
            description=f"Uploaded dataset with {num_queries} queries",
            dataset_uri=str(file_path),
            num_queries=num_queries,
            num_documents=num_documents,
        )
        
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        logger.info(
            "dataset_uploaded",
            dataset_id=dataset.id,
            name=dataset.name,
            num_queries=num_queries
        )
        
        return EvaluationDatasetResponse.from_orm(dataset)
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON file"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("dataset_upload_failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload dataset: {str(e)}"
        )


@router.post("", response_model=EvaluationDatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(
    dataset_data: EvaluationDatasetCreate,
    db: Session = Depends(get_db),
):
    """Create a dataset record (for datasets already on disk)."""
    # Check if file exists
    dataset_path = Path(dataset_data.dataset_uri)
    if not dataset_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset file not found: {dataset_data.dataset_uri}"
        )
    
    # Parse dataset to get counts
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            dataset_json = json.load(f)
        
        num_queries = len(dataset_json.get("queries", []))
        num_documents = len(dataset_json.get("corpus", {}))
    except Exception as e:
        logger.error("dataset_parse_failed", error=str(e), path=dataset_data.dataset_uri)
        num_queries = 0
        num_documents = 0
    
    # Create dataset record
    dataset = EvaluationDataset(
        name=dataset_data.name,
        description=dataset_data.description,
        dataset_uri=dataset_data.dataset_uri,
        num_queries=num_queries,
        num_documents=num_documents,
    )
    
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    logger.info("dataset_created", dataset_id=dataset.id, name=dataset.name)
    
    return EvaluationDatasetResponse.from_orm(dataset)


@router.get("", response_model=List[EvaluationDatasetResponse])
def list_datasets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all evaluation datasets."""
    datasets = db.query(EvaluationDataset).offset(skip).limit(limit).all()
    return [EvaluationDatasetResponse.from_orm(ds) for ds in datasets]


@router.get("/{dataset_id}", response_model=EvaluationDatasetResponse)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    """Get an evaluation dataset by ID."""
    dataset = db.query(EvaluationDataset).filter(EvaluationDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    return EvaluationDatasetResponse.from_orm(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    """Delete an evaluation dataset."""
    dataset = db.query(EvaluationDataset).filter(EvaluationDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    
    # Delete file if it exists
    try:
        file_path = Path(dataset.dataset_uri)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning(
            "dataset_file_deletion_failed",
            dataset_id=dataset_id,
            error=str(e)
        )
    
    db.delete(dataset)
    db.commit()
    
    logger.info("dataset_deleted", dataset_id=dataset_id)

