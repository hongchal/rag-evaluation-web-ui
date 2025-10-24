"""Evaluation Service for RAG performance testing."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import structlog
import json
import time
import traceback

from app.models.rag import RAGConfiguration
from app.models.evaluation import Evaluation, EvaluationResult
from app.models.evaluation_dataset import EvaluationDataset
from app.services.rag_factory import RAGFactory
from app.services.query_service import QueryService
from app.services.qdrant_service import QdrantService

logger = structlog.get_logger(__name__)


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

    def evaluate_rag(
        self,
        rag_id: int,
        dataset_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation:
        """
        Evaluate a RAG configuration on a dataset.
        
        Steps:
        1. Load RAG configuration and dataset
        2. Create evaluation record
        3. For each query in dataset:
           - Search using QueryService
           - Calculate metrics (NDCG, MRR, etc.)
        4. Aggregate metrics and save results
        
        Args:
            rag_id: RAG configuration ID
            dataset_id: Evaluation dataset ID
            name: Optional evaluation name
            description: Optional description
            
        Returns:
            Evaluation record with results
            
        Raises:
            ValueError: If RAG or dataset not found
        """
        # Load RAG and dataset
        rag = self.db.query(RAGConfiguration).filter(RAGConfiguration.id == rag_id).first()
        if not rag:
            raise ValueError(f"RAG configuration {rag_id} not found")
        
        dataset = self.db.query(EvaluationDataset).filter(EvaluationDataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Evaluation dataset {dataset_id} not found")
        
        # Generate name if not provided
        if not name:
            name = f"Evaluation: {rag.name} on {dataset.name}"
        
        # Create evaluation record
        evaluation = Evaluation(
            name=name,
            description=description,
            rag_id=rag_id,
            dataset_id=dataset_id,
            status="pending",
            progress=0.0,
        )
        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)
        
        return self._run_evaluation(evaluation)

    def _run_evaluation(self, evaluation: Evaluation) -> Evaluation:
        """
        Internal method to run evaluation.
        
        Args:
            evaluation: Evaluation record to run
            
        Returns:
            Updated Evaluation record
        """
        # Load RAG and dataset
        rag = self.db.query(RAGConfiguration).filter(
            RAGConfiguration.id == evaluation.rag_id
        ).first()
        if not rag:
            raise ValueError(f"RAG configuration {evaluation.rag_id} not found")
        
        dataset = self.db.query(EvaluationDataset).filter(
            EvaluationDataset.id == evaluation.dataset_id
        ).first()
        if not dataset:
            raise ValueError(f"Evaluation dataset {evaluation.dataset_id} not found")
        
        logger.info(
            "evaluation_started",
            evaluation_id=evaluation.id,
            rag_id=evaluation.rag_id,
            dataset_id=evaluation.dataset_id
        )
        
        # Start evaluation
        evaluation.status = "running"
        evaluation.started_at = datetime.utcnow()
        evaluation.current_step = "Loading dataset"
        self.db.commit()
        
        try:
            # Load dataset queries
            with open(dataset.dataset_uri, 'r', encoding='utf-8') as f:
                dataset_data = json.load(f)
            
            queries = dataset_data.get("queries", [])
            corpus = dataset_data.get("corpus", {})
            qrels = dataset_data.get("qrels", {})
            
            if not queries:
                raise ValueError(f"No queries found in dataset {dataset.name}")
            
            num_queries = len(queries)
            logger.info(
                "dataset_loaded",
                evaluation_id=evaluation.id,
                num_queries=num_queries
            )
            
            evaluation.current_step = f"Evaluating {num_queries} queries"
            self.db.commit()
            
            # Evaluate each query
            all_metrics = []
            query_results = []
            
            for i, query_data in enumerate(queries):
                query_id = query_data.get("id", str(i))
                query_text = query_data.get("text", query_data.get("query", ""))
                
                if not query_text:
                    logger.warning("empty_query", evaluation_id=evaluation.id, query_id=query_id)
                    continue
                
                # Get ground truth
                ground_truth = qrels.get(query_id, {})
                
                # Search
                try:
                    search_result = self.query_service.search(
                        rag_id=rag_id,
                        query=query_text,
                        top_k=10,  # Retrieve top 10 for metrics
                    )
                    
                    # Calculate metrics for this query
                    metrics = self._calculate_query_metrics(
                        search_result.chunks,
                        ground_truth,
                        k=10
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
                        query_id=query_id,
                        error=str(e)
                    )
                
                # Update progress
                progress = ((i + 1) / num_queries) * 100
                evaluation.progress = progress
                self.db.commit()
            
            # Aggregate metrics
            if not all_metrics:
                raise ValueError("No queries were successfully evaluated")
            
            aggregated_metrics = self._aggregate_metrics(all_metrics)
            
            logger.info(
                "evaluation_completed",
                evaluation_id=evaluation.id,
                metrics=aggregated_metrics
            )
            
            # Create evaluation result
            result = EvaluationResult(
                evaluation_id=evaluation.id,
                ndcg_at_k=aggregated_metrics["ndcg_at_k"],
                mrr=aggregated_metrics["mrr"],
                precision_at_k=aggregated_metrics["precision_at_k"],
                recall_at_k=aggregated_metrics["recall_at_k"],
                hit_rate=aggregated_metrics["hit_rate"],
                map_score=aggregated_metrics["map_score"],
                chunking_time=0.0,  # TODO: Track separately
                embedding_time=0.0,  # TODO: Track separately
                retrieval_time=aggregated_metrics["avg_retrieval_time"],
                total_time=aggregated_metrics["total_time"],
                num_chunks=len(corpus),
                avg_chunk_size=aggregated_metrics.get("avg_chunk_size", 0.0),
                query_results=query_results,
                metadata={
                    "num_queries_evaluated": len(all_metrics),
                    "dataset_name": dataset.name,
                    "rag_name": rag.name,
                },
            )
            self.db.add(result)
            
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
        # Extract retrieved doc IDs
        retrieved_ids = [chunk["id"] for chunk in retrieved_chunks[:k]]
        
        # Calculate metrics
        metrics = {}
        
        # NDCG@k
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids):
            rel = ground_truth.get(str(doc_id), 0.0)
            dcg += (2 ** rel - 1) / (i + 2)  # i+2 because i is 0-indexed
        
        # Ideal DCG
        ideal_rels = sorted(ground_truth.values(), reverse=True)[:k]
        idcg = sum((2 ** rel - 1) / (i + 2) for i, rel in enumerate(ideal_rels))
        
        metrics["ndcg_at_k"] = dcg / idcg if idcg > 0 else 0.0
        
        # MRR (Mean Reciprocal Rank)
        for i, doc_id in enumerate(retrieved_ids):
            if str(doc_id) in ground_truth and ground_truth[str(doc_id)] > 0:
                metrics["mrr"] = 1.0 / (i + 1)
                break
        else:
            metrics["mrr"] = 0.0
        
        # Precision@k
        relevant_retrieved = sum(
            1 for doc_id in retrieved_ids
            if str(doc_id) in ground_truth and ground_truth[str(doc_id)] > 0
        )
        metrics["precision_at_k"] = relevant_retrieved / k if k > 0 else 0.0
        
        # Recall@k
        total_relevant = sum(1 for rel in ground_truth.values() if rel > 0)
        metrics["recall_at_k"] = (
            relevant_retrieved / total_relevant if total_relevant > 0 else 0.0
        )
        
        # Hit Rate
        metrics["hit_rate"] = 1.0 if relevant_retrieved > 0 else 0.0
        
        # MAP (Mean Average Precision)
        avg_precision = 0.0
        num_relevant_seen = 0
        for i, doc_id in enumerate(retrieved_ids):
            if str(doc_id) in ground_truth and ground_truth[str(doc_id)] > 0:
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
        rag_id: Optional[int] = None,
        dataset_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Evaluation]:
        """
        List evaluations with optional filters.
        
        Args:
            rag_id: Optional RAG ID filter
            dataset_id: Optional dataset ID filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of evaluations
        """
        query = self.db.query(Evaluation)
        
        if rag_id is not None:
            query = query.filter(Evaluation.rag_id == rag_id)
        
        if dataset_id is not None:
            query = query.filter(Evaluation.dataset_id == dataset_id)
        
        return query.offset(skip).limit(limit).all()

    def compare_rags(
        self,
        rag_ids: List[int],
        dataset_id: int
    ) -> Dict[str, Any]:
        """
        Compare multiple RAG configurations on the same dataset.
        
        Args:
            rag_ids: List of RAG configuration IDs to compare
            dataset_id: Evaluation dataset ID
            
        Returns:
            Comparison results with metrics for each RAG
        """
        results = []
        
        for rag_id in rag_ids:
            # Find existing evaluation or create new one
            evaluation = (
                self.db.query(Evaluation)
                .filter(
                    Evaluation.rag_id == rag_id,
                    Evaluation.dataset_id == dataset_id,
                    Evaluation.status == "completed"
                )
                .first()
            )
            
            if not evaluation:
                # Run evaluation
                logger.info(
                    "running_evaluation_for_comparison",
                    rag_id=rag_id,
                    dataset_id=dataset_id
                )
                evaluation = self.evaluate_rag(rag_id, dataset_id)
            
            # Get results
            if evaluation.results:
                result = evaluation.results[0]
                results.append({
                    "rag_id": rag_id,
                    "rag_name": evaluation.rag.name,
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
        
        return {
            "dataset_id": dataset_id,
            "num_rags": len(results),
            "results": results,
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

