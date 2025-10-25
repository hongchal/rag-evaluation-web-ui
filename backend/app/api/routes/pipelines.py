"""Pipeline API endpoints."""

from typing import Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status
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
router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])


def get_pipeline_service(
    db: Session = Depends(get_db),
    qdrant_service: QdrantService = Depends(get_qdrant_service)
) -> PipelineService:
    """Dependency to get PipelineService instance."""
    return PipelineService(db, qdrant_service)


@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    pipeline_data: Union[NormalPipelineCreate, TestPipelineCreate],
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """
    Create a new pipeline.
    
    Two types of pipelines:
    
    1. **Normal Pipeline** (pipeline_type="normal"):
       - RAG Configuration + DataSources
       - For general querying with real documents
       - Automatically chunks and indexes datasources
    
    2. **Test Pipeline** (pipeline_type="test"):
       - RAG Configuration + EvaluationDataset
       - For testing with ground truth
       - Query results can be compared with golden chunks
       - Automatically chunks and indexes dataset documents
    
    After creating a pipeline, you can use its ID for queries.
    """
    try:
        # Dispatch based on pipeline type
        if pipeline_data.pipeline_type == "normal":
            pipeline = pipeline_service.create_normal_pipeline(pipeline_data)
        else:  # test
            pipeline = pipeline_service.create_test_pipeline(pipeline_data)
        
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
    rag_id: Optional[int] = None,
    datasource_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    pipeline_service: PipelineService = Depends(get_pipeline_service),
):
    """
    List pipelines with optional filters.
    
    Query Parameters:
    - rag_id: Filter by RAG configuration ID
    - datasource_id: Filter by datasource ID (pipelines containing this datasource)
    - skip: Number of items to skip (pagination)
    - limit: Maximum number of items to return
    """
    pipelines, total = pipeline_service.list_pipelines(
        rag_id=rag_id,
        datasource_id=datasource_id,
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

