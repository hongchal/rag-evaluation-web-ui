"""Evaluation Service for RAG performance testing."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
import structlog
import json
import time
import traceback
import numpy as np

from app.core.config import settings
from app.models.rag import RAGConfiguration
from app.models.evaluation import Evaluation, EvaluationResult
from app.models.evaluation_dataset import EvaluationDataset
from app.models.pipeline import Pipeline, PipelineType
from app.services.rag_factory import RAGFactory
from app.services.query_service import QueryService
from app.services.qdrant_service import QdrantService

logger = structlog.get_logger(__name__)


def resolve_dataset_uri(uri: str) -> str:
    """
    Resolve dataset URI to actual file path.
    
    Args:
        uri: Dataset URI (e.g., 'local://datasets/sample.json')
        
    Returns:
        Absolute file path
    """
    if uri.startswith('local://'):
        # Remove 'local://' prefix and resolve relative to backend directory
        relative_path = uri.replace('local://', '')
        backend_dir = Path(__file__).parent.parent.parent  # Go up to backend/
        return str(backend_dir / relative_path)
    elif uri.startswith('file://'):
        # Absolute file path
        return uri.replace('file://', '')
    else:
        # Assume it's already a file path
        return uri


class EvaluationService:
    """Service for evaluating RAG configurations."""

    def __init__(self, db: Session, qdrant_service: QdrantService):
        """
        Initialize EvaluationService.
        
        Args:
            db: Database session
            qdrant_service: Qdrant service instance
        """
        self.db = db
        self.qdrant_service = qdrant_service
        self.query_service = QueryService(db, qdrant_service)

    def evaluate_rag_by_id(self, evaluation_id: int) -> Evaluation:
        """
        Run evaluation using existing evaluation record.
        
        Args:
            evaluation_id: Existing evaluation record ID
            
        Returns:
            Updated Evaluation record
        """
        evaluation = self.get_evaluation(evaluation_id)
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found")
        
        return self._run_evaluation(evaluation)

    def evaluate_pipelines(
        self,
        pipeline_ids: List[int],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation:
        """
        Evaluate one or more TEST pipelines.
        
        Steps:
        1. Validate that all pipelines are TEST type
        2. Create evaluation record
        3. For each pipeline:
           - Run evaluation on its dataset
           - Calculate metrics (NDCG, MRR, etc.)
        4. Save results for each pipeline
        
        Args:
            pipeline_ids: List of TEST pipeline IDs to evaluate
            name: Optional evaluation name
            description: Optional description
            
        Returns:
            Evaluation record with results
            
        Raises:
            ValueError: If pipelines not found or not TEST type
        """
        # Validate pipelines
        pipelines = self.db.query(Pipeline).filter(Pipeline.id.in_(pipeline_ids)).all()
        if len(pipelines) != len(pipeline_ids):
            found_ids = [p.id for p in pipelines]
            missing = set(pipeline_ids) - set(found_ids)
            raise ValueError(f"Pipelines not found: {missing}")
        
        # Check all are TEST pipelines
        non_test = [p.id for p in pipelines if p.pipeline_type != PipelineType.TEST]
        if non_test:
            raise ValueError(f"Only TEST pipelines can be evaluated. Non-TEST pipelines: {non_test}")
        
        # Check all have datasets
        no_dataset = [p.id for p in pipelines if not p.dataset_id]
        if no_dataset:
            raise ValueError(f"Pipelines without dataset: {no_dataset}")
        
        # Generate name if not provided
        if not name:
            pipeline_names = ", ".join([p.name for p in pipelines])
            name = f"Evaluation: {pipeline_names}"
        
        # Create evaluation record
        evaluation = Evaluation(
            name=name,
            description=description,
            pipeline_ids=pipeline_ids,
            rag_id=None,  # Legacy field, nullable now
            dataset_id=None,  # Legacy field, nullable now
            status="pending",
            progress=0.0,
        )
        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)
        
        return self._run_evaluation(evaluation)

    def _run_evaluation(self, evaluation: Evaluation) -> Evaluation:
        """
        Internal method to run evaluation on pipeline(s).
        
        Args:
            evaluation: Evaluation record to run
            
        Returns:
            Updated Evaluation record
        """
        # Load pipelines
        pipeline_ids = evaluation.pipeline_ids
        pipelines = self.db.query(Pipeline).filter(Pipeline.id.in_(pipeline_ids)).all()
        
        if len(pipelines) != len(pipeline_ids):
            raise ValueError(f"Some pipelines not found: {pipeline_ids}")
        
        logger.info(
            "evaluation_started",
            evaluation_id=evaluation.id,
            pipeline_ids=pipeline_ids,
            num_pipelines=len(pipelines)
        )
        
        # Start evaluation
        evaluation.status = "running"
        evaluation.started_at = datetime.utcnow()
        evaluation.current_step = "Starting evaluation"
        self.db.commit()
        
        try:
            # Evaluate each pipeline
            total_pipeline_count = len(pipelines)
            
            for pipeline_idx, pipeline in enumerate(pipelines):
                logger.info(
                    "evaluating_pipeline",
                    evaluation_id=evaluation.id,
                    pipeline_id=pipeline.id,
                    pipeline_name=pipeline.name,
                    progress=f"{pipeline_idx + 1}/{total_pipeline_count}"
                )
                
                evaluation.current_step = f"Evaluating pipeline {pipeline_idx + 1}/{total_pipeline_count}: {pipeline.name}"
                self.db.commit()
                
                # Get dataset from pipeline
                dataset = pipeline.dataset
                if not dataset:
                    logger.error("pipeline_has_no_dataset", pipeline_id=pipeline.id)
                    continue
                
                # Load dataset queries
                dataset_path = resolve_dataset_uri(dataset.dataset_uri)
                logger.info("loading_dataset", uri=dataset.dataset_uri, resolved_path=dataset_path)
                
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    dataset_data = json.load(f)
                
                queries = dataset_data.get("queries", [])
                corpus = dataset_data.get("corpus", {})
                qrels = dataset_data.get("qrels", {})
                
                if not queries:
                    logger.warning("no_queries_in_dataset", dataset_id=dataset.id)
                    continue
                
                num_queries = len(queries)
                
                # Evaluate each query
                all_metrics = []
                query_results = []
                total_retrieval_time = 0.0
                
                for i, query_data in enumerate(queries):
                    query_id = query_data.get("id", str(i))
                    query_text = query_data.get("text", query_data.get("query", ""))
                    
                    if not query_text:
                        logger.warning("empty_query", query_id=query_id)
                        continue
                    
                    # Get ground truth from qrels (BEIR format) or relevant_doc_ids (FRAMES format)
                    if qrels and query_id in qrels:
                        # BEIR format: {"query_id": {"doc_id": relevance_score}}
                        ground_truth = qrels.get(query_id, {})
                    elif "relevant_doc_ids" in query_data:
                        # FRAMES format: Convert list to dict with relevance score 1
                        relevant_ids = query_data.get("relevant_doc_ids", [])
                        ground_truth = {doc_id: 1 for doc_id in relevant_ids}
                        logger.debug(
                            "converted_relevant_doc_ids",
                            query_idx=i,
                            num_relevant=len(relevant_ids),
                            ground_truth=ground_truth
                        )
                    else:
                        ground_truth = {}
                        logger.warning(
                            "no_ground_truth",
                            query_id=query_id,
                            query_idx=i
                        )
                    
                    # Search using pipeline
                    try:
                        search_result = self.query_service.search(
                            pipeline_id=pipeline.id,
                            query=query_text,
                            top_k=settings.default_top_k,
                        )
                        
                        total_retrieval_time += search_result.total_time
                        
                        # Log retrieved chunk IDs and ground truth for debugging
                        retrieved_ids = [chunk.get("id") for chunk in search_result.chunks[:10]]
                        logger.info(
                            "query_evaluation_debug",
                            query_idx=i,
                            query_id=query_id,
                            retrieved_ids=retrieved_ids[:5],  # First 5
                            ground_truth_ids=list(ground_truth.keys())[:5],  # First 5
                            num_retrieved=len(retrieved_ids),
                            num_ground_truth=len(ground_truth)
                        )
                        
                        # Calculate metrics for this query
                        metrics = self._calculate_query_metrics(
                            search_result.chunks,
                            ground_truth,
                            k=10
                        )
                        
                        logger.info(
                            "query_metrics_calculated",
                            query_idx=i,
                            metrics=metrics
                        )
                        
                        all_metrics.append(metrics)
                        
                        # Store sample results (first 5 queries)
                        if i < 5:
                            query_results.append({
                                "query_id": query_id,
                                "query": query_text,
                                "retrieved": [
                                    {
                                        "id": chunk["id"],
                                        "content": chunk["content"][:200],
                                        "score": chunk["score"],
                                    }
                                    for chunk in search_result.chunks[:5]
                                ],
                                "metrics": metrics,
                            })
                        
                    except Exception as e:
                        logger.error(
                            "query_evaluation_failed",
                            evaluation_id=evaluation.id,
                            pipeline_id=pipeline.id,
                            query_id=query_id,
                            error=str(e)
                        )
                    
                    # Update progress
                    overall_progress = (
                        (pipeline_idx * num_queries + i + 1) /
                        (total_pipeline_count * num_queries)
                    ) * 100
                    evaluation.progress = overall_progress
                    self.db.commit()
                
                # Aggregate metrics for this pipeline
                if all_metrics:
                    aggregated_metrics = self._aggregate_metrics(all_metrics)
                    aggregated_metrics["avg_retrieval_time"] = total_retrieval_time / len(all_metrics) if all_metrics else 0.0
                    aggregated_metrics["total_time"] = total_retrieval_time
                    
                    # Get indexing stats from pipeline (actual measured times only)
                    indexing_stats = pipeline.indexing_stats or {}
                    total_chunks_indexed = indexing_stats.get("total_chunks", 0)
                    
                    # Get actual chunking and embedding times from indexing stats
                    # Use 0.0 if not available (will display as N/A in frontend)
                    chunking_time = indexing_stats.get("chunking_time", 0.0)
                    embedding_time = indexing_stats.get("embedding_time", 0.0)
                    
                    if chunking_time == 0.0 or embedding_time == 0.0:
                        logger.warning(
                            "missing_timing_data",
                            pipeline_id=pipeline.id,
                            has_chunking=chunking_time > 0,
                            has_embedding=embedding_time > 0,
                            message="Chunking/embedding times not measured (old pipeline). Please recreate pipeline for accurate timing."
                        )
                    
                    # Create evaluation result for this pipeline
                    result = EvaluationResult(
                        evaluation_id=evaluation.id,
                        pipeline_id=pipeline.id,
                        ndcg_at_k=aggregated_metrics["ndcg_at_k"],
                        mrr=aggregated_metrics["mrr"],
                        precision_at_k=aggregated_metrics["precision_at_k"],
                        recall_at_k=aggregated_metrics["recall_at_k"],
                        hit_rate=aggregated_metrics["hit_rate"],
                        map_score=aggregated_metrics["map_score"],
                        chunking_time=chunking_time,
                        embedding_time=embedding_time,
                        retrieval_time=aggregated_metrics["avg_retrieval_time"],
                        total_time=aggregated_metrics["total_time"],
                        num_chunks=total_chunks_indexed or len(corpus),
                        avg_chunk_size=aggregated_metrics.get("avg_chunk_size", 0.0),
                        query_results=query_results,
                        result_metadata={
                            "num_queries_evaluated": len(all_metrics),
                            "dataset_name": dataset.name,
                            "pipeline_name": pipeline.name,
                            "pipeline_id": pipeline.id,
                        },
                    )
                    self.db.add(result)
                    
                    logger.info(
                        "pipeline_evaluation_completed",
                        evaluation_id=evaluation.id,
                        pipeline_id=pipeline.id,
                        metrics=aggregated_metrics
                    )
            
            # Update evaluation status
            evaluation.status = "completed"
            evaluation.completed_at = datetime.utcnow()
            evaluation.progress = 100.0
            evaluation.current_step = "Completed"
            self.db.commit()
            self.db.refresh(evaluation)
            
            return evaluation
            
        except Exception as e:
            # Handle error
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            logger.error(
                "evaluation_failed",
                evaluation_id=evaluation.id,
                error=error_msg,
                trace=error_trace
            )
            
            evaluation.status = "failed"
            evaluation.error_message = error_msg
            evaluation.completed_at = datetime.utcnow()
            self.db.commit()
            
            raise

    def _calculate_query_metrics(
        self,
        retrieved_chunks: List[Dict[str, Any]],
        ground_truth: Dict[str, float],
        k: int = 10
    ) -> Dict[str, float]:
        """
        Calculate metrics for a single query.
        
        Args:
            retrieved_chunks: List of retrieved chunks
            ground_truth: Dict of {doc_id: relevance_score}
            k: Number of results to consider
            
        Returns:
            Dict of metrics
        """
        # Extract retrieved doc IDs from metadata (not chunk point_id!)
        # The chunk["id"] is the Qdrant point_id like "pipeline_X_dataset_Y_doc_Z_chunk_N"
        # We need the actual doc_id from metadata like "frames_q0_doc0"
        retrieved_ids = []
        for chunk in retrieved_chunks[:k]:
            metadata = chunk.get("metadata", {})
            doc_id = metadata.get("doc_id")
            if doc_id:
                retrieved_ids.append(doc_id)
            else:
                # Fallback to chunk id if no doc_id in metadata
                retrieved_ids.append(chunk.get("id"))
        
        # Calculate metrics
        metrics = {}
        
        # NDCG@k (순위를 고려하므로 중복 포함)
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids):
            rel = ground_truth.get(doc_id, 0.0)
            dcg += (2 ** rel - 1) / np.log2(i + 2)  # i+2 because i is 0-indexed
        
        # Ideal DCG - k개 위치 전체에 대해 계산 (관련 문서를 상위에 배치, 나머지는 0)
        ideal_rels = sorted(ground_truth.values(), reverse=True)
        # k개 위치를 모두 채움 (부족하면 0으로)
        ideal_rels = ideal_rels[:k] + [0.0] * max(0, k - len(ideal_rels))
        idcg = sum((2 ** rel - 1) / np.log2(i + 2) for i, rel in enumerate(ideal_rels))
        
        metrics["ndcg_at_k"] = dcg / idcg if idcg > 0 else 0.0
        
        # MRR (Mean Reciprocal Rank) - 첫 번째 관련 문서의 순위
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in ground_truth and ground_truth[doc_id] > 0:
                metrics["mrr"] = 1.0 / (i + 1)
                break
        else:
            metrics["mrr"] = 0.0
        
        # Unique 문서만 추출 (중복 제거)
        # 순서를 유지하면서 중복 제거 (첫 등장만 유지)
        unique_retrieved_ids = []
        seen = set()
        for doc_id in retrieved_ids:
            if doc_id not in seen:
                unique_retrieved_ids.append(doc_id)
                seen.add(doc_id)
        
        # Debug logging for duplicate detection
        if len(retrieved_ids) != len(unique_retrieved_ids):
            duplicates = len(retrieved_ids) - len(unique_retrieved_ids)
            logger.debug(
                "duplicate_docs_detected",
                total_chunks=len(retrieved_ids),
                unique_docs=len(unique_retrieved_ids),
                duplicates=duplicates
            )
        
        # Precision@k - unique 문서 기준
        # Document-level precision: relevant unique docs / total unique docs retrieved
        unique_relevant_retrieved = sum(
            1 for doc_id in unique_retrieved_ids
            if doc_id in ground_truth and ground_truth[doc_id] > 0
        )
        num_unique_retrieved = len(unique_retrieved_ids)
        metrics["precision_at_k"] = (
            unique_relevant_retrieved / num_unique_retrieved 
            if num_unique_retrieved > 0 else 0.0
        )
        
        # Recall@k - unique 문서 기준
        total_relevant = sum(1 for rel in ground_truth.values() if rel > 0)
        metrics["recall_at_k"] = (
            unique_relevant_retrieved / total_relevant if total_relevant > 0 else 0.0
        )
        
        # Hit Rate - unique 문서 기준
        metrics["hit_rate"] = 1.0 if unique_relevant_retrieved > 0 else 0.0
        
        # MAP (Mean Average Precision) - unique 문서 기준
        avg_precision = 0.0
        num_relevant_seen = 0
        for i, doc_id in enumerate(unique_retrieved_ids):
            if doc_id in ground_truth and ground_truth[doc_id] > 0:
                num_relevant_seen += 1
                precision_at_i = num_relevant_seen / (i + 1)
                avg_precision += precision_at_i
        
        metrics["map_score"] = (
            avg_precision / total_relevant if total_relevant > 0 else 0.0
        )
        
        return metrics

    def _aggregate_metrics(self, all_metrics: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Aggregate metrics across all queries.
        
        Args:
            all_metrics: List of metric dicts for each query
            
        Returns:
            Aggregated metrics
        """
        if not all_metrics:
            return {}
        
        num_queries = len(all_metrics)
        
        aggregated = {
            "ndcg_at_k": sum(m["ndcg_at_k"] for m in all_metrics) / num_queries,
            "mrr": sum(m["mrr"] for m in all_metrics) / num_queries,
            "precision_at_k": sum(m["precision_at_k"] for m in all_metrics) / num_queries,
            "recall_at_k": sum(m["recall_at_k"] for m in all_metrics) / num_queries,
            "hit_rate": sum(m["hit_rate"] for m in all_metrics) / num_queries,
            "map_score": sum(m["map_score"] for m in all_metrics) / num_queries,
            "avg_retrieval_time": 0.0,  # TODO: Track
            "total_time": 0.0,  # TODO: Track
            "avg_chunk_size": 0.0,  # TODO: Track
        }
        
        return aggregated

    def get_evaluation(self, evaluation_id: int) -> Optional[Evaluation]:
        """Get evaluation by ID."""
        return self.db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()

    def list_evaluations(
        self,
        pipeline_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Evaluation]:
        """
        List evaluations with optional filters.
        
        Args:
            pipeline_id: Optional pipeline ID filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of evaluations
        """
        query = self.db.query(Evaluation)
        
        # Filter by pipeline_id if provided (checks if pipeline_id is in the array)
        if pipeline_id is not None:
            # For PostgreSQL, use array contains
            from sqlalchemy import func, cast
            from sqlalchemy.dialects.postgresql import ARRAY, INTEGER
            query = query.filter(
                func.array_position(
                    cast(Evaluation.pipeline_ids, ARRAY(INTEGER)),
                    pipeline_id
                ).isnot(None)
            )
        
        return query.order_by(Evaluation.created_at.desc()).offset(skip).limit(limit).all()

    def compare_pipelines(
        self,
        pipeline_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Compare multiple TEST pipelines by running evaluation.
        
        This creates a new evaluation with all the specified pipelines.
        
        Args:
            pipeline_ids: List of TEST pipeline IDs to compare
            
        Returns:
            Comparison results with metrics for each pipeline
        """
        # Validate and get pipelines
        pipelines = self.db.query(Pipeline).filter(Pipeline.id.in_(pipeline_ids)).all()
        if len(pipelines) != len(pipeline_ids):
            found_ids = [p.id for p in pipelines]
            missing = set(pipeline_ids) - set(found_ids)
            raise ValueError(f"Pipelines not found: {missing}")
        
        # Check for existing completed evaluation with these exact pipelines
        existing_evaluation = (
            self.db.query(Evaluation)
            .filter(
                Evaluation.status == "completed",
                Evaluation.pipeline_ids == pipeline_ids
            )
            .order_by(Evaluation.created_at.desc())
            .first()
        )
        
        if existing_evaluation:
            logger.info(
                "using_existing_evaluation",
                evaluation_id=existing_evaluation.id,
                pipeline_ids=pipeline_ids
            )
            evaluation = existing_evaluation
        else:
            # Run new evaluation
            logger.info(
                "running_new_evaluation_for_comparison",
                pipeline_ids=pipeline_ids
            )
            pipeline_names = ", ".join([p.name for p in pipelines])
            evaluation = self.evaluate_pipelines(
                pipeline_ids=pipeline_ids,
                name=f"Comparison: {pipeline_names}",
                description="Automatic comparison evaluation"
            )
        
        # Build comparison response
        results = []
        for result in evaluation.results:
            if result.pipeline_id:
                pipeline = self.db.query(Pipeline).filter(Pipeline.id == result.pipeline_id).first()
                results.append({
                    "pipeline_id": result.pipeline_id,
                    "pipeline_name": pipeline.name if pipeline else "Unknown",
                    "evaluation_id": evaluation.id,
                    "metrics": {
                        "ndcg_at_k": result.ndcg_at_k,
                        "mrr": result.mrr,
                        "precision_at_k": result.precision_at_k,
                        "recall_at_k": result.recall_at_k,
                        "hit_rate": result.hit_rate,
                        "map_score": result.map_score,
                    },
                    "performance": {
                        "retrieval_time": result.retrieval_time,
                        "total_time": result.total_time,
                    }
                })
        
        # Find best pipeline by NDCG
        best_pipeline_id = None
        best_metric = "ndcg_at_k"
        if results:
            best_result = max(results, key=lambda r: r["metrics"][best_metric])
            best_pipeline_id = best_result["pipeline_id"]
        
        return {
            "evaluation_id": evaluation.id,
            "evaluation_name": evaluation.name,
            "pipeline_count": len(results),
            "metrics": results,
            "best_pipeline_id": best_pipeline_id,
            "best_metric": best_metric,
        }

    def cancel_evaluation(self, evaluation_id: int) -> bool:
        """
        Cancel a running evaluation.
        
        Returns:
            True if cancelled, False if not found or not running
        """
        evaluation = self.get_evaluation(evaluation_id)
        if not evaluation or evaluation.status != "running":
            return False
        
        evaluation.status = "cancelled"
        evaluation.completed_at = datetime.utcnow()
        evaluation.error_message = "Cancelled by user"
        self.db.commit()
        
        logger.info("evaluation_cancelled", evaluation_id=evaluation_id)
        
        return True

    def delete_evaluation(self, evaluation_id: int) -> bool:
        """
        Delete an evaluation.
        
        Returns:
            True if deleted, False if not found
        """
        evaluation = self.get_evaluation(evaluation_id)
        if not evaluation:
            return False
        
        self.db.delete(evaluation)
        self.db.commit()
        
        logger.info("evaluation_deleted", evaluation_id=evaluation_id)
        
        return True

