"""Pipeline API endpoints."""

from typing import Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import structlog

from app.core.dependencies import get_db, get_qdrant_service
from app.services.pipeline_service import PipelineService
from app.services.qdrant_service import QdrantService
from app.schemas.pipeline import (
    NormalPipelineCreate,
    TestPipelineCreate,
    PipelineUpdate,
    PipelineResponse,
    PipelineListResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


def get_pipeline_service(
    db: Session = Depends(get_db),
    qdrant_service: QdrantService = Depends(get_qdrant_service)
) -> PipelineService:
    """Dependency to get PipelineService instance."""
    return PipelineService(db, qdrant_service)


@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    pipeline_data: Union[NormalPipelineCreate, TestPipelineCreate],
    background_tasks: BackgroundTasks,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """
    Create a new pipeline.
    
    파이프라인은 PENDING 상태로 생성되고 즉시 반환됩니다.
    인덱싱은 백그라운드에서 진행되며, GET /api/pipelines/{id}로 상태를 확인할 수 있습니다.
    
    Two types of pipelines:
    
    1. **Normal Pipeline** (pipeline_type="normal"):
       - RAG Configuration + DataSources
       - For general querying with real documents
       - Automatically chunks and indexes datasources in background
    
    2. **Test Pipeline** (pipeline_type="test"):
       - RAG Configuration + EvaluationDataset
       - For testing with ground truth
       - Query results can be compared with golden chunks
       - Automatically chunks and indexes dataset documents in background
    
    Status values:
    - `pending`: 생성됨, 인덱싱 대기 중
    - `indexing`: 인덱싱 진행 중
    - `ready`: 인덱싱 완료, 쿼리 가능
    - `failed`: 인덱싱 실패
    """
    try:
        # Create pipeline in PENDING status
        if pipeline_data.pipeline_type == "normal":
            pipeline = pipeline_service.create_normal_pipeline(pipeline_data)
        else:  # test
            pipeline = pipeline_service.create_test_pipeline(pipeline_data)
        
        # Start indexing in background
        background_tasks.add_task(pipeline_service.index_pipeline, pipeline.id)
        
        logger.info(
            "pipeline_created_indexing_queued",
            pipeline_id=pipeline.id,
            pipeline_type=pipeline.pipeline_type,
            status=pipeline.status
        )
        
        return PipelineResponse.model_validate(pipeline)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("pipeline_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pipeline: {str(e)}"
        )


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    pipeline_id: int,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """Get a pipeline by ID."""
    pipeline = pipeline_service.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )
    return PipelineResponse.model_validate(pipeline)


@router.get("", response_model=PipelineListResponse)
def list_pipelines(
    pipeline_type: Optional[str] = None,
    rag_id: Optional[int] = None,
    datasource_id: Optional[int] = None,
    dataset_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """
    List pipelines with optional filters.
    
    Query Parameters:
    - pipeline_type: Filter by pipeline type ('normal' or 'test')
    - rag_id: Filter by RAG configuration ID
    - datasource_id: Filter by datasource ID (pipelines containing this datasource)
    - dataset_id: Filter by evaluation dataset ID (test pipelines only)
    - skip: Number of items to skip (pagination)
    - limit: Maximum number of items to return
    """
    pipelines, total = pipeline_service.list_pipelines(
        pipeline_type=pipeline_type,
        rag_id=rag_id,
        datasource_id=datasource_id,
        dataset_id=dataset_id,
        skip=skip,
        limit=limit
    )
    
    return PipelineListResponse(
        total=total,
        items=[PipelineResponse.model_validate(p) for p in pipelines]
    )


@router.patch("/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(
    pipeline_id: int,
    pipeline_data: PipelineUpdate,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """
    Update a pipeline.
    
    You can update:
    - Name and description
    - Associated datasources
    
    Note: RAG configuration cannot be changed after creation.
    Create a new pipeline if you need different RAG settings.
    """
    try:
        pipeline = pipeline_service.update_pipeline(pipeline_id, pipeline_data)
        if not pipeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pipeline {pipeline_id} not found"
            )
        return PipelineResponse.model_validate(pipeline)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("pipeline_update_failed", error=str(e), pipeline_id=pipeline_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pipeline: {str(e)}"
        )


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pipeline(
    pipeline_id: int,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """
    Delete a pipeline.
    
    This only deletes the pipeline record, not the RAG configuration or datasources.
    """
    success = pipeline_service.delete_pipeline(pipeline_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )
    logger.info("pipeline_deleted_via_api", pipeline_id=pipeline_id)

