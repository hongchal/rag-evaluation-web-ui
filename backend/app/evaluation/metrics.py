"""Metrics for evaluating RAG pipeline performance."""

import time
from dataclasses import dataclass
from typing import Any, Optional, List

import numpy as np


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality."""

    ndcg_at_k: float
    mrr: float
    precision_at_k: float
    recall_at_k: float
    hit_rate: float
    map_score: float  # Mean Average Precision


@dataclass
class EfficiencyMetrics:
    """Metrics for efficiency."""

    indexing_time: float  # seconds
    query_latency: float  # seconds
    memory_usage: float  # MB
    num_chunks: int
    avg_chunk_size: float  # tokens
    total_tokens: int


@dataclass
class RAGMetrics:
    """Metrics for end-to-end RAG quality (using RAGAS)."""

    context_relevance: float
    answer_relevance: float
    faithfulness: float
    context_recall: float
    context_precision: float


@dataclass
class ComprehensiveMetrics:
    """Complete evaluation metrics."""

    retrieval: RetrievalMetrics
    efficiency: EfficiencyMetrics
    rag: Optional[RAGMetrics] = None  # Optional, requires LLM


class EvaluationMetrics:
    """Calculator for various evaluation metrics."""

    @staticmethod
    def calculate_ndcg_at_k(relevance_scores: List[float], k: Optional[int] = None) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain at K.

        Args:
            relevance_scores: List of relevance scores (0-1 or binary) in ranked order
            k: Number of top results to consider (None = all)

        Returns:
            NDCG@K score (0-1)
        """
        if not relevance_scores:
            return 0.0

        if k is not None:
            relevance_scores = relevance_scores[:k]

        def dcg(scores: List[float]) -> float:
            """Calculate DCG."""
            return sum(score / np.log2(i + 2) for i, score in enumerate(scores))

        # Actual DCG
        actual_dcg = dcg(relevance_scores)

        # Ideal DCG (sorted in descending order)
        ideal_dcg = dcg(sorted(relevance_scores, reverse=True))

        return actual_dcg / ideal_dcg if ideal_dcg > 0 else 0.0

    @staticmethod
    def calculate_mrr(relevance_scores: List[float], threshold: float = 0.5) -> float:
        """
        Calculate Mean Reciprocal Rank.

        Args:
            relevance_scores: List of relevance scores in ranked order
            threshold: Minimum score to consider relevant

        Returns:
            MRR score (0-1)
        """
        for i, score in enumerate(relevance_scores):
            if score >= threshold:
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    def calculate_precision_at_k(
        relevance_scores: List[float], k: int, threshold: float = 0.5
    ) -> float:
        """
        Calculate Precision@K.

        Args:
            relevance_scores: List of relevance scores in ranked order
            k: Number of top results to consider
            threshold: Minimum score to consider relevant

        Returns:
            Precision@K score (0-1)
        """
        if not relevance_scores or k == 0:
            return 0.0

        top_k = relevance_scores[:k]
        relevant = sum(1 for score in top_k if score >= threshold)
        return relevant / k

    @staticmethod
    def calculate_recall_at_k(
        relevance_scores: List[float],
        total_relevant: int,
        k: int,
        threshold: float = 0.5,
    ) -> float:
        """
        Calculate Recall@K.

        Args:
            relevance_scores: List of relevance scores in ranked order
            total_relevant: Total number of relevant documents
            k: Number of top results to consider
            threshold: Minimum score to consider relevant

        Returns:
            Recall@K score (0-1)
        """
        if total_relevant == 0:
            return 0.0

        top_k = relevance_scores[:k]
        relevant_found = sum(1 for score in top_k if score >= threshold)
        return relevant_found / total_relevant

    @staticmethod
    def calculate_hit_rate(relevance_scores: List[float], threshold: float = 0.5) -> float:
        """
        Calculate Hit Rate (whether any relevant document was retrieved).

        Args:
            relevance_scores: List of relevance scores
            threshold: Minimum score to consider relevant

        Returns:
            1.0 if any hit, 0.0 otherwise
        """
        return 1.0 if any(score >= threshold for score in relevance_scores) else 0.0

    @staticmethod
    def calculate_map(
        all_relevance_scores: List[List[float]], threshold: float = 0.5
    ) -> float:
        """
        Calculate Mean Average Precision across multiple queries.

        Args:
            all_relevance_scores: List of relevance score lists (one per query)
            threshold: Minimum score to consider relevant

        Returns:
            MAP score (0-1)
        """
        if not all_relevance_scores:
            return 0.0

        average_precisions = []
        for relevance_scores in all_relevance_scores:
            precisions = []
            relevant_count = 0

            for i, score in enumerate(relevance_scores):
                if score >= threshold:
                    relevant_count += 1
                    precision_at_i = relevant_count / (i + 1)
                    precisions.append(precision_at_i)

            if precisions:
                average_precisions.append(sum(precisions) / len(precisions))
            else:
                average_precisions.append(0.0)

        return sum(average_precisions) / len(average_precisions)

    @staticmethod
    def create_retrieval_metrics(
        relevance_scores: List[float],
        total_relevant: int,
        k: int = 10,
        threshold: float = 0.5,
    ) -> RetrievalMetrics:
        """
        Create RetrievalMetrics from relevance scores.

        Args:
            relevance_scores: List of relevance scores in ranked order
            total_relevant: Total number of relevant documents
            k: Number of top results to consider
            threshold: Minimum score to consider relevant

        Returns:
            RetrievalMetrics object
        """
        return RetrievalMetrics(
            ndcg_at_k=EvaluationMetrics.calculate_ndcg_at_k(relevance_scores, k),
            mrr=EvaluationMetrics.calculate_mrr(relevance_scores, threshold),
            precision_at_k=EvaluationMetrics.calculate_precision_at_k(
                relevance_scores, k, threshold
            ),
            recall_at_k=EvaluationMetrics.calculate_recall_at_k(
                relevance_scores, total_relevant, k, threshold
            ),
            hit_rate=EvaluationMetrics.calculate_hit_rate(relevance_scores, threshold),
            map_score=EvaluationMetrics.calculate_map([relevance_scores], threshold),
        )


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.elapsed: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        if self.start_time is not None:
            self.elapsed = time.perf_counter() - self.start_time

    def get_elapsed(self) -> float:
        """Get elapsed time in seconds."""
        return self.elapsed
