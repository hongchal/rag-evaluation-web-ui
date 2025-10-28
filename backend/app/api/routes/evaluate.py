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
    ComparisonResponse,
    EvaluationListResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/evaluate", tags=["evaluate"])


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
    """Run an evaluation on one or more TEST pipelines."""
    try:
        # Validate inputs
        from app.models.pipeline import Pipeline, PipelineType
        from app.models.evaluation import Evaluation
        
        # Validate pipelines
        pipelines = eval_service.db.query(Pipeline).filter(
            Pipeline.id.in_(eval_request.pipeline_ids)
        ).all()
        
        if len(pipelines) != len(eval_request.pipeline_ids):
            found_ids = [p.id for p in pipelines]
            missing = set(eval_request.pipeline_ids) - set(found_ids)
            raise ValueError(f"Pipelines not found: {missing}")
        
        # Check all are TEST pipelines
        non_test = [p.id for p in pipelines if p.pipeline_type != PipelineType.TEST]
        if non_test:
            raise ValueError(f"Only TEST pipelines can be evaluated. Non-TEST: {non_test}")
        
        # Generate name if not provided
        name = eval_request.name
        if not name:
            pipeline_names = ", ".join([p.name for p in pipelines])
            name = f"Evaluation: {pipeline_names}"
        
        # Create evaluation record
        evaluation = Evaluation(
            name=name,
            description=eval_request.description,
            pipeline_ids=eval_request.pipeline_ids,
            rag_id=None,  # Legacy field
            dataset_id=None,  # Legacy field
            status="pending",
            progress=0.0,
        )
        eval_service.db.add(evaluation)
        eval_service.db.commit()
        eval_service.db.refresh(evaluation)
        
        # Run evaluation in background
        from app.core.database import SessionLocal
        background_tasks.add_task(
            _run_evaluation_task,
            evaluation.id,
            SessionLocal(),
            eval_service.qdrant_service,
        )
        
        logger.info("evaluation_queued", evaluation_id=evaluation.id, pipeline_ids=eval_request.pipeline_ids)
        return EvaluationResponse.model_validate(evaluation)
        
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
    """Compare multiple TEST pipelines."""
    try:
        comparison = eval_service.compare_pipelines(
            compare_request.pipeline_ids,
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
    from app.schemas.evaluation import MetricsResponse
    from app.models.pipeline import Pipeline
    
    evaluation = eval_service.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found"
        )
    
    # Build response with metrics
    response = EvaluationResponse.model_validate(evaluation)
    
    # Add metrics from results if available
    if evaluation.results and evaluation.status == "completed":
        metrics_list = []
        for result in evaluation.results:
            pipeline = None
            if result.pipeline_id:
                pipeline = eval_service.db.query(Pipeline).filter(Pipeline.id == result.pipeline_id).first()
            
            metrics_list.append(MetricsResponse(
                pipeline_id=result.pipeline_id,
                pipeline_name=pipeline.name if pipeline else None,
                ndcg_at_k=result.ndcg_at_k,
                mrr=result.mrr,
                precision_at_k=result.precision_at_k,
                recall_at_k=result.recall_at_k,
                hit_rate=result.hit_rate,
                map_score=result.map_score,
                chunking_time=result.chunking_time,
                embedding_time=result.embedding_time,
                retrieval_time=result.retrieval_time,
                total_time=result.total_time,
                num_chunks=result.num_chunks,
                avg_chunk_size=result.avg_chunk_size,
            ))
        response.metrics = metrics_list
    
    return response


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
    return EvaluationResponse.model_validate(evaluation)


@router.get("", response_model=EvaluationListResponse)
def list_evaluations(
    pipeline_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    eval_service: EvaluationService = Depends(get_evaluation_service),
):
    """List evaluations with optional filters."""
    from app.schemas.evaluation import MetricsResponse
    from app.models.pipeline import Pipeline
    
    evaluations = eval_service.list_evaluations(
        pipeline_id=pipeline_id,
        skip=skip,
        limit=limit,
    )
    
    # Build responses with metrics
    responses = []
    for evaluation in evaluations:
        response = EvaluationResponse.model_validate(evaluation)
        
        # Add metrics if completed
        if evaluation.results and evaluation.status == "completed":
            metrics_list = []
            for result in evaluation.results:
                pipeline = None
                if result.pipeline_id:
                    pipeline = eval_service.db.query(Pipeline).filter(Pipeline.id == result.pipeline_id).first()
                
                metrics_list.append(MetricsResponse(
                    pipeline_id=result.pipeline_id,
                    pipeline_name=pipeline.name if pipeline else None,
                    ndcg_at_k=result.ndcg_at_k,
                    mrr=result.mrr,
                    precision_at_k=result.precision_at_k,
                    recall_at_k=result.recall_at_k,
                    hit_rate=result.hit_rate,
                    map_score=result.map_score,
                    chunking_time=result.chunking_time,
                    embedding_time=result.embedding_time,
                    retrieval_time=result.retrieval_time,
                    total_time=result.total_time,
                    num_chunks=result.num_chunks,
                    avg_chunk_size=result.avg_chunk_size,
                ))
            response.metrics = metrics_list
        
        responses.append(response)
    
    return EvaluationListResponse(total=len(responses), items=responses)


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


@router.post("/{evaluation_id}/analyze")
def analyze_evaluation(
    evaluation_id: int,
    eval_service: EvaluationService = Depends(get_evaluation_service),
):
    """Generate AI-powered analysis of evaluation results using Claude."""
    from app.services.claude_analysis_service import ClaudeAnalysisService
    from app.models.pipeline import Pipeline
    from app.schemas.evaluation import MetricsResponse
    
    try:
        # Get evaluation
        evaluation = eval_service.get_evaluation(evaluation_id)
        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evaluation {evaluation_id} not found"
            )
        
        # Check if completed
        if evaluation.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Evaluation must be completed before analysis"
            )
        
        # Build metrics list
        if not evaluation.results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No evaluation results available"
            )
        
        metrics_list = []
        for result in evaluation.results:
            pipeline = None
            if result.pipeline_id:
                pipeline = eval_service.db.query(Pipeline).filter(Pipeline.id == result.pipeline_id).first()
            
            metrics_list.append({
                "pipeline_id": result.pipeline_id,
                "pipeline_name": pipeline.name if pipeline else None,
                "ndcg_at_k": result.ndcg_at_k,
                "mrr": result.mrr,
                "precision_at_k": result.precision_at_k,
                "recall_at_k": result.recall_at_k,
                "hit_rate": result.hit_rate,
                "map_score": result.map_score,
                "chunking_time": result.chunking_time,
                "embedding_time": result.embedding_time,
                "retrieval_time": result.retrieval_time,
                "total_time": result.total_time,
                "num_chunks": result.num_chunks,
                "avg_chunk_size": result.avg_chunk_size,
            })
        
        # Get dataset name if available
        dataset_name = None
        if evaluation.results and evaluation.results[0].result_metadata:
            dataset_name = evaluation.results[0].result_metadata.get("dataset_name")
        
        # Generate analysis
        analysis_service = ClaudeAnalysisService()
        analysis = analysis_service.analyze_evaluation_results(
            evaluation_name=evaluation.name,
            metrics=metrics_list,
            dataset_name=dataset_name
        )
        
        logger.info("evaluation_analysis_generated", evaluation_id=evaluation_id)
        
        return {
            "evaluation_id": evaluation_id,
            "analysis": analysis
        }
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("evaluation_analysis_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analysis: {str(e)}"
        )

