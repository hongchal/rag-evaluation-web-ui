"""Evaluation API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import structlog

from app.core.dependencies import get_db, get_qdrant_service
from app.services.evaluation_service import EvaluationService
from app.services.qdrant_service import QdrantService
from app.schemas.evaluation import (
    EvaluationCreate,
    CompareRequest,
    EvaluationResponse,
    EvaluationResponse,
    ComparisonResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


def get_evaluation_service(
    db: Session = Depends(get_db),
    qdrant_service: QdrantService = Depends(get_qdrant_service)
) -> EvaluationService:
    """Dependency to get EvaluationService instance."""
    return EvaluationService(db, qdrant_service)


def _run_evaluation_task(evaluation_id: int, db: Session, qdrant_service: QdrantService):
    """Background task to run evaluation."""
    eval_service = EvaluationService(db, qdrant_service)
    try:
        eval_service.evaluate_rag_by_id(evaluation_id)
    except Exception as e:
        logger.error("evaluation_task_failed", evaluation_id=evaluation_id, error=str(e))


@router.post("/run", response_model=EvaluationResponse, status_code=status.HTTP_202_ACCEPTED)
def run_evaluation(
    eval_request: EvaluationCreate,
    background_tasks: BackgroundTasks,
    eval_service: EvaluationService = Depends(get_evaluation_service),
):
    """Run an evaluation of a RAG configuration on a dataset."""
    try:
        # Validate inputs
        from app.models.rag import RAGConfiguration
        from app.models.evaluation_dataset import EvaluationDataset
        from app.models.evaluation import Evaluation
        
        rag = eval_service.db.query(RAGConfiguration).filter(
            RAGConfiguration.id == eval_request.rag_id
        ).first()
        if not rag:
            raise ValueError(f"RAG {eval_request.rag_id} not found")
        
        dataset = eval_service.db.query(EvaluationDataset).filter(
            EvaluationDataset.id == eval_request.dataset_id
        ).first()
        if not dataset:
            raise ValueError(f"Dataset {eval_request.dataset_id} not found")
        
        # Create evaluation record
        evaluation = Evaluation(
            name=eval_request.name or f"Evaluation: {rag.name} on {dataset.name}",
            description=eval_request.description,
            rag_id=eval_request.rag_id,
            dataset_id=eval_request.dataset_id,
            status="pending",
            progress=0.0,
        )
        eval_service.db.add(evaluation)
        eval_service.db.commit()
        eval_service.db.refresh(evaluation)
        
        # Run evaluation in background (pass evaluation_id)
        from app.core.database import SessionLocal
        background_tasks.add_task(
            _run_evaluation_task,
            evaluation.id,
            SessionLocal(),
            eval_service.qdrant_service,
        )
        
        logger.info("evaluation_queued", evaluation_id=evaluation.id)
        return EvaluationResponse.from_orm(evaluation)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("evaluation_start_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start evaluation: {str(e)}"
        )


@router.post("/compare", response_model=ComparisonResponse)
def compare_evaluations(
    compare_request: CompareRequest,
    eval_service: EvaluationService = Depends(get_evaluation_service),
):
    """Compare multiple RAG configurations on the same dataset."""
    try:
        comparison = eval_service.compare_rags(
            compare_request.rag_ids,
            compare_request.dataset_id,
        )
        
        return ComparisonResponse(**comparison)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("evaluation_compare_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare evaluations: {str(e)}"
        )


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
def get_evaluation(
    evaluation_id: int,
    eval_service: EvaluationService = Depends(get_evaluation_service),
):
    """Get evaluation results by ID."""
    evaluation = eval_service.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found"
        )
    return EvaluationResponse.from_orm(evaluation)


@router.get("/{evaluation_id}/status", response_model=EvaluationResponse)
def get_evaluation_status(
    evaluation_id: int,
    eval_service: EvaluationService = Depends(get_evaluation_service),
):
    """Get evaluation progress status."""
    evaluation = eval_service.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found"
        )
    
    return EvaluationResponse(
        id=evaluation.id,
        status=evaluation.status,
        progress=evaluation.progress,
        current_step=evaluation.current_step,
        error_message=evaluation.error_message,
    )


@router.post("/{evaluation_id}/cancel", response_model=EvaluationResponse)
def cancel_evaluation(
    evaluation_id: int,
    eval_service: EvaluationService = Depends(get_evaluation_service),
):
    """Cancel a running evaluation."""
    success = eval_service.cancel_evaluation(evaluation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evaluation {evaluation_id} cannot be cancelled (not found or not running)"
        )
    
    evaluation = eval_service.get_evaluation(evaluation_id)
    return EvaluationResponse.from_orm(evaluation)


@router.get("", response_model=List[EvaluationResponse])
def list_evaluations(
    rag_id: Optional[int] = None,
    dataset_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    eval_service: EvaluationService = Depends(get_evaluation_service),
):
    """List evaluations with optional filters."""
    evaluations = eval_service.list_evaluations(
        rag_id=rag_id,
        dataset_id=dataset_id,
        skip=skip,
        limit=limit,
    )
    return [EvaluationResponse.from_orm(e) for e in evaluations]


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evaluation(
    evaluation_id: int,
    eval_service: EvaluationService = Depends(get_evaluation_service),
):
    """Delete an evaluation."""
    success = eval_service.delete_evaluation(evaluation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found"
        )
    logger.info("evaluation_deleted", evaluation_id=evaluation_id)

