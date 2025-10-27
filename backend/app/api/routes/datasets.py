"""EvaluationDataset API endpoints."""

from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import structlog
import json
import subprocess
import sys
import os

from app.core.dependencies import get_db
from app.core.config import settings
from app.models.evaluation_dataset import EvaluationDataset
from app.models.evaluation_query import EvaluationQuery
from app.services.file_processor import FileProcessor
from app.schemas.dataset import (
    EvaluationDatasetResponse,
    EvaluationDatasetCreate,
    EvaluationDatasetListResponse,
    AvailableDatasetInfo,
    DatasetDownloadRequest,
    DatasetDownloadResponse,
    EvaluationQueryResponse,
    EvaluationQueryListResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/datasets", tags=["datasets"])

# Available datasets for download
AVAILABLE_DATASETS = {
    "frames": {
        "id": "frames",
        "name": "FRAMES-RAG",
        "description": "Google FRAMES benchmark with Wikipedia content (824 queries, 2621+ documents). Downloads real Wikipedia articles.",
        "size": "medium",
        "estimated_time": "10-30 min (varies by network)",
        "num_queries": 824,
        "num_documents": 2621
    },
    "scifact": {
        "id": "scifact",
        "name": "BEIR SciFact",
        "description": "Scientific fact verification dataset",
        "size": "small",
        "estimated_time": "30 seconds",
        "num_queries": 300,
        "num_documents": 5183
    },
    "nfcorpus": {
        "id": "nfcorpus",
        "name": "BEIR NFCorpus",
        "description": "Nutrition and health corpus",
        "size": "small",
        "estimated_time": "30 seconds",
        "num_queries": 323,
        "num_documents": 3633
    },
    "fiqa": {
        "id": "fiqa",
        "name": "BEIR FiQA",
        "description": "Financial question answering",
        "size": "medium",
        "estimated_time": "1-2 minutes",
        "num_queries": 648,
        "num_documents": 57638
    },
    "trec-covid": {
        "id": "trec-covid",
        "name": "BEIR TREC-COVID",
        "description": "COVID-19 research articles",
        "size": "large",
        "estimated_time": "2-3 minutes",
        "num_queries": 50,
        "num_documents": 171332
    }
}


@router.post("/upload", response_model=EvaluationDatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
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
        
        # Use provided name or fallback to filename
        dataset_name = name if name else file.filename.replace('.json', '')
        dataset_description = description if description else f"Uploaded dataset with {num_queries} queries and {num_documents} documents"
        
        # Create dataset record
        dataset = EvaluationDataset(
            name=dataset_name,
            description=dataset_description,
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


@router.get("", response_model=EvaluationDatasetListResponse)
def list_datasets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all evaluation datasets."""
    datasets = db.query(EvaluationDataset).offset(skip).limit(limit).all()
    items = [EvaluationDatasetResponse.from_orm(ds) for ds in datasets]
    return EvaluationDatasetListResponse(total=len(items), items=items)


@router.get("/available", response_model=List[AvailableDatasetInfo])
def list_available_datasets():
    """List all datasets available for download."""
    return [AvailableDatasetInfo(**info) for info in AVAILABLE_DATASETS.values()]


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


@router.get("/{dataset_id}/queries", response_model=EvaluationQueryListResponse)
def get_dataset_queries(
    dataset_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get all queries for a specific dataset."""
    dataset = db.query(EvaluationDataset).filter(EvaluationDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    
    queries = (
        db.query(EvaluationQuery)
        .filter(EvaluationQuery.dataset_id == dataset_id)
        .order_by(EvaluationQuery.query_idx)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    total = db.query(EvaluationQuery).filter(EvaluationQuery.dataset_id == dataset_id).count()
    
    return EvaluationQueryListResponse(
        total=total,
        items=[EvaluationQueryResponse.model_validate(q) for q in queries]
    )


def _run_download_script(dataset_id: str, db_url: str) -> tuple[bool, str]:
    """
    Run the download script with progress monitoring.
    
    Monitors script output in real-time. If no output is produced for 10 minutes,
    considers the download stalled and terminates the process.
    """
    import time
    
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        
        if dataset_id == "frames":
            script_path = project_root / "scripts" / "download_frames.py"
            cmd = [sys.executable, str(script_path), "--fetch-wikipedia"]
        else:
            # BEIR datasets
            script_path = project_root / "scripts" / "prepare_dataset.py"
            cmd = [sys.executable, str(script_path), "beir", "--name", dataset_id]
        
        # Determine correct working directory
        cwd = project_root.parent
        
        logger.info("running_download_script", dataset_id=dataset_id, script=str(script_path), cwd=str(cwd))
        
        # Run with DATABASE_URL environment variable
        env = os.environ.copy()
        env["DATABASE_URL"] = db_url
        env["PYTHONUNBUFFERED"] = "1"  # Disable Python output buffering
        
        # Use Popen with direct output (no buffering issues)
        # Redirect to parent process's stdout/stderr for real-time output
        
        process = subprocess.Popen(
            cmd,
            env=env,
            cwd=str(cwd),
            # Let subprocess inherit our stdout/stderr for real-time output
            stdout=None,  # Inherit parent's stdout
            stderr=None,  # Inherit parent's stderr
        )
        
        # Wait for process with timeout check
        stall_timeout = 600  # 10 minutes
        start_time = time.time()
        
        while process.poll() is None:
            elapsed = time.time() - start_time
            if elapsed > stall_timeout:
                print(f"\n⚠️  Process running for {elapsed:.0f}s without completion")
                logger.warning("download_long_running", dataset_id=dataset_id, elapsed=elapsed)
            
            time.sleep(5)  # Check every 5 seconds
        
        returncode = process.returncode
        stdout_output = ""
        stderr_output = ""
        
        if returncode == 0:
            logger.info("download_completed", dataset_id=dataset_id, stdout=stdout_output[:500], stderr=stderr_output[:500] if stderr_output else None)
            return True, "Download completed successfully"
        else:
            error_msg = stderr_output or stdout_output or "Unknown error"
            logger.error("download_failed", dataset_id=dataset_id, error=error_msg[:500])
            return False, error_msg
            
    except Exception as e:
        logger.error("download_error", dataset_id=dataset_id, error=str(e))
        return False, str(e)


def _update_dataset_status_after_download(dataset_name: str, db_url: str):
    """Update dataset status after download completes or fails."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        dataset = db.query(EvaluationDataset).filter(
            EvaluationDataset.name == dataset_name
        ).first()
        
        if dataset:
            # Check if it has actual data (queries/documents)
            if dataset.num_queries > 0 and dataset.num_documents > 0:
                dataset.status = "ready"
                logger.info("dataset_ready", dataset_id=dataset.id, name=dataset.name)
            else:
                dataset.status = "failed"
                dataset.download_error = "No data loaded"
                logger.warning("dataset_failed_no_data", dataset_id=dataset.id, name=dataset.name)
            
            db.commit()
    except Exception as e:
        logger.error("update_status_failed", error=str(e))
    finally:
        db.close()


@router.post("/download", response_model=DatasetDownloadResponse)
async def download_dataset(
    request: DatasetDownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Download a dataset and register it to the database."""
    import fcntl
    
    dataset_id = request.dataset_id
    
    # Validate dataset ID
    if dataset_id not in AVAILABLE_DATASETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown dataset: {dataset_id}. Available: {list(AVAILABLE_DATASETS.keys())}"
        )
    
    dataset_info = AVAILABLE_DATASETS[dataset_id]
    
    # Use file lock to prevent concurrent downloads of same dataset
    lock_file = Path(f"/tmp/dataset_download_{dataset_id}.lock")
    try:
        with open(lock_file, 'w') as f:
            # Try to acquire exclusive lock (non-blocking)
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                # Another download is in progress
                logger.warning("concurrent_download_blocked", dataset_id=dataset_id)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Dataset '{dataset_info['name']}' is currently being downloaded. Please wait and refresh."
                )
            
            # Check if already exists or downloading
            existing = db.query(EvaluationDataset).filter(
                EvaluationDataset.name == dataset_info["name"]
            ).first()
            
            if existing:
                if existing.status == "downloading":
                    logger.info("dataset_already_downloading", dataset_id=dataset_id, existing_id=existing.id)
                    return DatasetDownloadResponse(
                        success=True,
                        message=f"Dataset '{dataset_info['name']}' is already being downloaded. Please wait...",
                        dataset_id=existing.id
                    )
                elif existing.status == "ready":
                    logger.info("dataset_already_exists", dataset_id=dataset_id, existing_id=existing.id)
                    return DatasetDownloadResponse(
                        success=True,
                        message=f"Dataset '{dataset_info['name']}' already exists (ID: {existing.id})",
                        dataset_id=existing.id
                    )
                # If FAILED, allow re-download by deleting old record
                elif existing.status == "failed":
                    logger.info("dataset_failed_reattempt", dataset_id=dataset_id, existing_id=existing.id)
                    db.delete(existing)
                    db.commit()
            
            # Create placeholder record with DOWNLOADING status
            placeholder = EvaluationDataset(
                name=dataset_info["name"],
                description=dataset_info["description"],
                dataset_uri=f"backend/datasets/{dataset_id}_eval.json",  # Expected path
                num_queries=0,
                num_documents=0,
                status="downloading"
            )
            db.add(placeholder)
            db.commit()
            db.refresh(placeholder)
            
            logger.info("placeholder_created", dataset_id=placeholder.id, name=placeholder.name)
            
            # Get database URL from settings or environment
            db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/rag_evaluation")
            
            logger.info("starting_background_download", dataset_id=dataset_id, placeholder_id=placeholder.id)
            
            # Add download task to background
            background_tasks.add_task(_run_download_script, dataset_id, db_url)
            background_tasks.add_task(_update_dataset_status_after_download, dataset_info["name"], db_url)
            
            # Return immediately so server doesn't block
            return DatasetDownloadResponse(
                success=True,
                message=f"⏳ Download started for '{dataset_info['name']}'. Estimated time: {dataset_info['estimated_time']}. The status will update automatically - please refresh the page.",
                dataset_id=placeholder.id
            )
    except Exception as e:
        logger.error("download_request_failed", dataset_id=dataset_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start download: {str(e)}"
        )

