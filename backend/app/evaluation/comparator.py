"""Strategy comparator for evaluating multiple chunking/embedding combinations."""

import asyncio
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional, List

import pandas as pd
import structlog

from .dataset import EvaluationDataset
from .evaluator import EvaluationConfig, EvaluationResult, RAGEvaluator

logger = structlog.get_logger(__name__)


def _serialize_strategy(strategy: "StrategyConfig") -> dict:
    """Serialize a strategy config for multiprocessing."""
    chunker = strategy.chunker
    embedder = strategy.embedder

    # Extract chunker info
    chunker_class = chunker.__class__.__name__
    chunker_params = {}
    if hasattr(chunker, "chunk_size"):
        chunker_params["chunk_size"] = chunker.chunk_size
    if hasattr(chunker, "chunk_overlap"):
        chunker_params["chunk_overlap"] = chunker.chunk_overlap
    if hasattr(chunker, "similarity_threshold"):
        chunker_params["similarity_threshold"] = chunker.similarity_threshold
    if hasattr(chunker, "min_chunk_tokens"):
        chunker_params["min_chunk_tokens"] = chunker.min_chunk_tokens
    if hasattr(chunker, "max_chunk_tokens"):
        chunker_params["max_chunk_tokens"] = chunker.max_chunk_tokens
    if hasattr(chunker, "sentences_per_group"):
        chunker_params["sentences_per_group"] = chunker.sentences_per_group
    if hasattr(chunker, "breakpoint_percentile"):
        chunker_params["breakpoint_percentile"] = chunker.breakpoint_percentile
    if hasattr(chunker, "buffer_size"):
        chunker_params["buffer_size"] = chunker.buffer_size

    # Extract chunker's embedder (for mixed mode)
    chunker_embedder_class = None
    chunker_embedder_params = {}
    if hasattr(chunker, "embedder") and chunker.embedder is not None:
        chunker_embedder_class = chunker.embedder.__class__.__name__
        if hasattr(chunker.embedder, "default_dimension"):
            chunker_embedder_params["default_dimension"] = (
                chunker.embedder.default_dimension
            )
        if hasattr(chunker.embedder, "base_url"):
            chunker_embedder_params["base_url"] = chunker.embedder.base_url
        if hasattr(chunker.embedder, "model_name"):
            chunker_embedder_params["model_name"] = chunker.embedder.model_name
        if hasattr(chunker.embedder, "embedding_dim"):
            chunker_embedder_params["embedding_dim"] = chunker.embedder.embedding_dim

    # Extract retrieval embedder info
    embedder_class = embedder.__class__.__name__
    embedder_params = {}
    if hasattr(embedder, "default_dimension"):
        embedder_params["default_dimension"] = embedder.default_dimension
    if hasattr(embedder, "base_url"):
        embedder_params["base_url"] = embedder.base_url
    if hasattr(embedder, "model_name"):
        embedder_params["model_name"] = embedder.model_name
    if hasattr(embedder, "embedding_dim"):
        embedder_params["embedding_dim"] = embedder.embedding_dim

    return {
        "name": strategy.name,
        "chunker_class": chunker_class,
        "chunker_params": chunker_params,
        "chunker_embedder_class": chunker_embedder_class,
        "chunker_embedder_params": chunker_embedder_params,
        "embedder_class": embedder_class,
        "embedder_params": embedder_params,
    }


def _run_evaluation_in_process(
    strategy_dict: dict,
    dataset_data: dict,
    eval_config_dict: dict,
) -> dict:
    """
    Run evaluation in a separate process.

    This function is designed to be pickled and run in a subprocess.
    All parameters must be serializable (no complex objects).

    Args:
        strategy_dict: Serialized strategy config
        dataset_data: Dataset as dict (from save format)
        eval_config_dict: Eval config as dict

    Returns:
        Serialized EvaluationResult
    """
    # Disable tokenizers parallelism warning/error in subprocess
    import os

    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # Import inside process to avoid pickling issues
    from app.chunking.chunkers.hierarchical import HierarchicalChunker
    from app.chunking.chunkers.recursive import RecursiveChunker
    from app.chunking.chunkers.semantic import SemanticChunker
    from app.chunking.chunkers.semantic_langchain import SemanticLangChainChunker
    from app.chunking.chunkers.semantic_llamaindex import SemanticLlamaIndexChunker
    from app.embedding.embedders.bge_m3 import BGEM3Embedder
    from app.embedding.embedders.matryoshka import MatryoshkaEmbedder
    from app.embedding.embedders.vllm_http import VLLMHTTPEmbedder
    from app.embedding.embedders.jina_late_chunking import JinaLocalLateChunkingEmbedder
    from app.embedding.vector_stores.qdrant import QdrantStore
    from app.evaluation.dataset import (
        EvaluationDataset,
        EvaluationDocument,
        EvaluationQuery,
    )
    from app.evaluation.evaluator import EvaluationConfig, RAGEvaluator

    # Reconstruct dataset
    documents = [
        EvaluationDocument(
            doc_id=doc["doc_id"],
            content=doc["content"],
            title=doc.get("title"),
            metadata=doc.get("metadata", {}),
        )
        for doc in dataset_data["documents"]
    ]

    queries = [
        EvaluationQuery(
            query=q["query"],
            relevant_doc_ids=q["relevant_doc_ids"],
            expected_answer=q.get("expected_answer"),
            context=q.get("context"),
            difficulty=q.get("difficulty", "medium"),
            query_type=q.get("query_type", "factual"),
            metadata=q.get("metadata", {}),
        )
        for q in dataset_data["queries"]
    ]

    dataset = EvaluationDataset(
        name=dataset_data["name"],
        documents=documents,
        queries=queries,
        description=dataset_data.get("description", ""),
        metadata=dataset_data.get("metadata", {}),
    )

    eval_config = EvaluationConfig(**eval_config_dict)
    vector_store = QdrantStore()

    # Reconstruct chunker's embedder first (for mixed mode)
    chunker_embedder = None
    chunker_embedder_class = strategy_dict.get("chunker_embedder_class")
    if chunker_embedder_class:
        chunker_embedder_params = strategy_dict.get("chunker_embedder_params", {})
        if chunker_embedder_class == "BGEM3Embedder":
            chunker_embedder = BGEM3Embedder()
        elif chunker_embedder_class == "MatryoshkaEmbedder":
            chunker_embedder = MatryoshkaEmbedder(**chunker_embedder_params)
        elif chunker_embedder_class == "VLLMHTTPEmbedder":
            chunker_embedder = VLLMHTTPEmbedder(**chunker_embedder_params)
        elif chunker_embedder_class == "JinaLocalLateChunkingEmbedder":
            chunker_embedder = JinaLocalLateChunkingEmbedder()
        else:
            raise ValueError(
                f"Unknown chunker embedder class: {chunker_embedder_class}"
            )

    # Reconstruct chunker (use chunker_embedder if available, else default to BGEM3)
    chunker_class = strategy_dict["chunker_class"]
    chunker_params = strategy_dict["chunker_params"]
    if chunker_class == "RecursiveChunker":
        chunker = RecursiveChunker(**chunker_params)
    elif chunker_class == "HierarchicalChunker":
        chunker = HierarchicalChunker(**chunker_params)
    elif chunker_class == "SemanticChunker":
        embedder_for_chunker = chunker_embedder if chunker_embedder else BGEM3Embedder()
        chunker = SemanticChunker(embedder=embedder_for_chunker, **chunker_params)
    elif chunker_class == "SemanticLangChainChunker":
        embedder_for_chunker = chunker_embedder if chunker_embedder else BGEM3Embedder()
        chunker = SemanticLangChainChunker(
            embedder=embedder_for_chunker, **chunker_params
        )
    elif chunker_class == "SemanticLlamaIndexChunker":
        embedder_for_chunker = chunker_embedder if chunker_embedder else BGEM3Embedder()
        chunker = SemanticLlamaIndexChunker(
            embedder=embedder_for_chunker, **chunker_params
        )
    else:
        raise ValueError(f"Unknown chunker class: {chunker_class}")

    # Reconstruct retrieval embedder
    embedder_class = strategy_dict["embedder_class"]
    embedder_params = strategy_dict["embedder_params"]
    if embedder_class == "BGEM3Embedder":
        embedder = BGEM3Embedder()
    elif embedder_class == "MatryoshkaEmbedder":
        embedder = MatryoshkaEmbedder(**embedder_params)
    elif embedder_class == "VLLMHTTPEmbedder":
        embedder = VLLMHTTPEmbedder(**embedder_params)
    elif embedder_class == "JinaLocalLateChunkingEmbedder":
        embedder = JinaLocalLateChunkingEmbedder()
    else:
        raise ValueError(f"Unknown embedder class: {embedder_class}")

    # Run evaluation with strategy_name for unique collection naming
    evaluator = RAGEvaluator(
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
        config=eval_config,
        strategy_name=strategy_dict["name"],
    )

    # Use asyncio.run to execute async function in process
    try:
        result = asyncio.run(
            evaluator.evaluate(dataset, strategy_name=strategy_dict["name"])
        )

        # Serialize result (without query_results to save memory)
        return {
            "success": True,
            "strategy_name": result.strategy_name,
            "dataset_name": result.dataset_name,
            "metrics": {
                "retrieval": asdict(result.metrics.retrieval),
                "efficiency": asdict(result.metrics.efficiency),
                "rag": asdict(result.metrics.rag) if result.metrics.rag else None,
            },
            "config": asdict(result.config),
            "metadata": result.metadata,
        }
    except Exception as e:
        # Return error as serializable dict
        import traceback

        return {
            "success": False,
            "strategy_name": strategy_dict["name"],
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }


@dataclass
class StrategyConfig:
    """Configuration for a chunking/embedding strategy."""

    name: str
    chunker: Any
    embedder: Any
    description: str = ""


@dataclass
class ComparisonResult:
    """Result of comparing multiple strategies."""

    dataset_name: str
    results: List[EvaluationResult]
    comparison_table: pd.DataFrame
    winner: str  # Name of best performing strategy


class StrategyComparator:
    """
    Compare multiple chunking/embedding strategies.

    Runs evaluation on multiple strategies and provides comparison analysis.
    """

    def __init__(
        self,
        vector_store: Any,
        eval_config: Optional[EvaluationConfig] = None,
    ):
        """
        Initialize comparator.

        Args:
            vector_store: Vector store instance
            eval_config: Evaluation configuration
        """
        self.vector_store = vector_store
        self.eval_config = eval_config or EvaluationConfig()

    async def compare_strategies(
        self,
        strategies: List[StrategyConfig],
        dataset: EvaluationDataset,
        parallel: bool = False,
        max_parallel: int = 3,
    ) -> ComparisonResult:
        """
        Compare multiple strategies on a dataset.

        Args:
            strategies: List of strategies to compare
            dataset: Evaluation dataset
            parallel: Whether to run strategies in parallel (default: False for safety)
            max_parallel: Maximum number of parallel evaluations (default: 3)

        Returns:
            ComparisonResult with analysis
        """
        logger.info(
            "comparing_strategies",
            num_strategies=len(strategies),
            dataset=dataset.name,
            parallel=parallel,
        )

        if parallel:
            # Parallel execution with limited concurrency
            results = await self._evaluate_strategies_parallel(
                strategies, dataset, max_parallel
            )
        else:
            # Sequential execution (original behavior)
            results = await self._evaluate_strategies_sequential(strategies, dataset)

        # Create comparison table
        comparison_table = self._create_comparison_table(results)

        # Determine winner (best NDCG@K)
        winner = max(results, key=lambda r: r.metrics.retrieval.ndcg_at_k)

        logger.info(
            "comparison_completed",
            winner=winner.strategy_name,
            ndcg=winner.metrics.retrieval.ndcg_at_k,
        )

        return ComparisonResult(
            dataset_name=dataset.name,
            results=results,
            comparison_table=comparison_table,
            winner=winner.strategy_name,
        )

    async def _evaluate_strategies_sequential(
        self,
        strategies: List[StrategyConfig],
        dataset: EvaluationDataset,
    ) -> List[EvaluationResult]:
        """Sequential evaluation (original behavior)."""
        results = []

        for strategy in strategies:
            logger.info("evaluating_strategy", strategy=strategy.name)

            # Create evaluator for this strategy with strategy_name for unique collection
            evaluator = RAGEvaluator(
                chunker=strategy.chunker,
                embedder=strategy.embedder,
                vector_store=self.vector_store,
                config=self.eval_config,
                strategy_name=strategy.name,
            )

            # Run evaluation
            result = await evaluator.evaluate(dataset, strategy_name=strategy.name)
            results.append(result)

        return results

    async def _evaluate_strategies_parallel(
        self,
        strategies: List[StrategyConfig],
        dataset: EvaluationDataset,
        max_parallel: int,
    ) -> List[EvaluationResult]:
        """
        Parallel evaluation using ProcessPoolExecutor for true parallelism.

        This method uses separate processes to bypass Python's GIL and achieve
        true parallel execution of CPU-bound chunking and embedding operations.
        """
        from app.evaluation.metrics import (
            ComprehensiveMetrics,
            EfficiencyMetrics,
            RetrievalMetrics,
            RAGMetrics,
        )

        logger.info(
            "starting_parallel_evaluation",
            total_strategies=len(strategies),
            max_parallel=max_parallel,
        )

        # Serialize strategies and dataset for multiprocessing
        strategy_dicts = [_serialize_strategy(s) for s in strategies]

        # Serialize dataset
        dataset_data = {
            "name": dataset.name,
            "description": dataset.description,
            "documents": [
                {
                    "doc_id": doc.doc_id,
                    "content": doc.content,
                    "title": doc.title,
                    "metadata": doc.metadata,
                }
                for doc in dataset.documents
            ],
            "queries": [
                {
                    "query": q.query,
                    "relevant_doc_ids": q.relevant_doc_ids,
                    "expected_answer": q.expected_answer,
                    "context": q.context,
                    "difficulty": q.difficulty,
                    "query_type": q.query_type,
                    "metadata": q.metadata,
                }
                for q in dataset.queries
            ],
            "metadata": dataset.metadata,
        }

        # Serialize eval config
        eval_config_dict = {
            "top_k": self.eval_config.top_k,
            "relevance_threshold": self.eval_config.relevance_threshold,
            "use_ragas": self.eval_config.use_ragas,
            "cleanup_after": self.eval_config.cleanup_after,
        }

        # Run evaluations in parallel processes
        # Use 'spawn' method to avoid fork issues with Rust tokenizers
        import multiprocessing

        ctx = multiprocessing.get_context("spawn")

        loop = asyncio.get_event_loop()

        with ProcessPoolExecutor(max_workers=max_parallel, mp_context=ctx) as executor:
            # Submit all tasks
            futures = [
                loop.run_in_executor(
                    executor,
                    _run_evaluation_in_process,
                    strategy_dict,
                    dataset_data,
                    eval_config_dict,
                )
                for strategy_dict in strategy_dicts
            ]

            # Wait for all results
            serialized_results = await asyncio.gather(*futures)

        # Reconstruct EvaluationResult objects from serialized data
        results = []
        failed_strategies = []

        for result_dict in serialized_results:
            # Check if evaluation was successful
            if not result_dict.get("success", True):
                strategy_name = result_dict.get("strategy_name", "Unknown")
                error_msg = result_dict.get("error", "Unknown error")
                error_type = result_dict.get("error_type", "Unknown")

                logger.error(
                    "strategy_evaluation_failed",
                    strategy=strategy_name,
                    error=error_msg,
                    error_type=error_type,
                )
                logger.error("error_traceback", traceback=result_dict.get("traceback"))

                failed_strategies.append(
                    {
                        "strategy": strategy_name,
                        "error": error_msg,
                        "error_type": error_type,
                    }
                )
                continue

            # Reconstruct metrics
            retrieval_metrics = RetrievalMetrics(**result_dict["metrics"]["retrieval"])
            efficiency_metrics = EfficiencyMetrics(
                **result_dict["metrics"]["efficiency"]
            )
            rag_metrics = (
                RAGMetrics(**result_dict["metrics"]["rag"])
                if result_dict["metrics"]["rag"]
                else None
            )

            comprehensive_metrics = ComprehensiveMetrics(
                retrieval=retrieval_metrics,
                efficiency=efficiency_metrics,
                rag=rag_metrics,
            )

            # Create EvaluationResult (without query_results)
            result = EvaluationResult(
                strategy_name=result_dict["strategy_name"],
                dataset_name=result_dict["dataset_name"],
                metrics=comprehensive_metrics,
                query_results=[],  # Not serialized to save memory
                config=EvaluationConfig(**result_dict["config"]),
                metadata=result_dict["metadata"],
            )
            results.append(result)

        logger.info("parallel_evaluation_completed", num_results=len(results))

        # Check if all evaluations failed
        if len(results) == 0:
            logger.error(
                "all_evaluations_failed",
                total_strategies=len(strategies),
                failed_count=len(serialized_results),
            )
            raise ValueError(
                f"All {len(strategies)} parallel evaluations failed. "
                "Check error logs above for details."
            )

        # Warn if some evaluations failed
        if len(results) < len(strategies):
            failed_count = len(strategies) - len(results)
            logger.warning(
                "some_evaluations_failed",
                total=len(strategies),
                successful=len(results),
                failed=failed_count,
                failed_strategies=[f["strategy"] for f in failed_strategies],
            )
            print(
                f"\n⚠️  Warning: {failed_count} out of {len(strategies)} strategies failed"
            )
            print(f"✓ Successfully evaluated {len(results)} strategies")

            if failed_strategies:
                print(f"\n❌ Failed strategies:")
                for failed in failed_strategies:
                    print(f"   - {failed['strategy']}: {failed['error_type']}")

            print(f"\nCheck logs for full failure details\n")

        return results

    def _create_comparison_table(self, results: List[EvaluationResult]) -> pd.DataFrame:
        """
        Create comparison table from results.

        Args:
            results: List of evaluation results

        Returns:
            DataFrame with comparison metrics
        """
        rows = []

        for result in results:
            retrieval = result.metrics.retrieval
            efficiency = result.metrics.efficiency
            rag_metrics = result.metrics.rag

            row = {
                "Strategy": result.strategy_name,
                # Retrieval metrics
                "NDCG@K": f"{retrieval.ndcg_at_k:.4f}",
                "MRR": f"{retrieval.mrr:.4f}",
                "Precision@K": f"{retrieval.precision_at_k:.4f}",
                "Recall@K": f"{retrieval.recall_at_k:.4f}",
                "Hit Rate": f"{retrieval.hit_rate:.4f}",
                "MAP": f"{retrieval.map_score:.4f}",
                # Efficiency metrics
                "Indexing Time (s)": f"{efficiency.indexing_time:.2f}",
                "Query Latency (ms)": f"{efficiency.query_latency * 1000:.2f}",
                "Num Chunks": efficiency.num_chunks,
                "Avg Chunk Size": f"{efficiency.avg_chunk_size:.1f}",
                "Memory (MB)": f"{efficiency.memory_usage:.2f}",
            }

            # Add RAGAS metrics if available
            if rag_metrics:
                row.update(
                    {
                        "Context Relevance": f"{rag_metrics.context_relevance:.4f}",
                        "Answer Relevance": f"{rag_metrics.answer_relevance:.4f}",
                        "Faithfulness": f"{rag_metrics.faithfulness:.4f}",
                        "Context Precision": f"{rag_metrics.context_precision:.4f}",
                        "Context Recall": f"{rag_metrics.context_recall:.4f}",
                    }
                )

            rows.append(row)

        return pd.DataFrame(rows)

    def save_comparison(self, comparison: ComparisonResult, output_dir: Path) -> None:
        """
        Save comparison results to disk.

        Args:
            comparison: Comparison result
            output_dir: Output directory
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save comparison table as CSV
        csv_path = output_dir / "comparison_table.csv"
        comparison.comparison_table.to_csv(csv_path, index=False)
        logger.info("saved_comparison_table", path=csv_path)

        # Save detailed results as JSON
        json_path = output_dir / "detailed_results.json"
        detailed = {
            "dataset_name": comparison.dataset_name,
            "winner": comparison.winner,
            "results": [
                {
                    "strategy_name": r.strategy_name,
                    "metrics": {
                        "retrieval": asdict(r.metrics.retrieval),
                        "efficiency": asdict(r.metrics.efficiency),
                        "rag": asdict(r.metrics.rag) if r.metrics.rag else None,
                    },
                    "metadata": r.metadata,
                }
                for r in comparison.results
            ],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(detailed, f, indent=2)
        logger.info("saved_detailed_results", path=json_path)

        # Save summary report
        report_path = output_dir / "comparison_report.md"
        self._save_report(comparison, report_path)
        logger.info("saved_comparison_report", path=report_path)

    def _save_report(self, comparison: ComparisonResult, report_path: Path) -> None:
        """
        Generate and save comparison report in Markdown.

        Args:
            comparison: Comparison result
            report_path: Path to save report
        """
        report_lines = [
            f"# RAG Strategy Comparison Report",
            f"",
            f"**Dataset:** {comparison.dataset_name}",
            f"**Winner:** {comparison.winner}",
            f"",
            f"## Comparison Table",
            f"",
            "```",
            comparison.comparison_table.to_string(index=False),
            "```",
            f"",
            f"## Detailed Analysis",
            f"",
        ]

        # Add detailed analysis for each strategy
        for result in comparison.results:
            strategy_lines = [
                f"### {result.strategy_name}",
                f"",
                f"**Chunker:** {result.metadata['chunker']}",
                f"**Embedder:** {result.metadata['embedder']}",
                f"",
                f"**Retrieval Quality:**",
                f"- NDCG@K: {result.metrics.retrieval.ndcg_at_k:.4f}",
                f"- MRR: {result.metrics.retrieval.mrr:.4f}",
                f"- Precision@K: {result.metrics.retrieval.precision_at_k:.4f}",
                f"- Recall@K: {result.metrics.retrieval.recall_at_k:.4f}",
                f"- Hit Rate: {result.metrics.retrieval.hit_rate:.4f}",
                f"- MAP: {result.metrics.retrieval.map_score:.4f}",
                f"",
            ]

            # Add RAGAS metrics if available
            if result.metrics.rag:
                rag = result.metrics.rag
                strategy_lines.extend(
                    [
                        f"**RAGAS Metrics (End-to-End RAG Quality):**",
                        f"- Context Relevance: {rag.context_relevance:.4f}",
                        f"- Answer Relevance: {rag.answer_relevance:.4f}",
                        f"- Faithfulness: {rag.faithfulness:.4f}",
                        f"- Context Precision: {rag.context_precision:.4f}",
                        f"- Context Recall: {rag.context_recall:.4f}",
                        f"",
                    ]
                )

            strategy_lines.extend(
                [
                    f"**Efficiency:**",
                    f"- Indexing Time: {result.metrics.efficiency.indexing_time:.2f}s",
                    f"- Query Latency: {result.metrics.efficiency.query_latency * 1000:.2f}ms",
                    f"- Number of Chunks: {result.metrics.efficiency.num_chunks}",
                    f"- Avg Chunk Size: {result.metrics.efficiency.avg_chunk_size:.1f} tokens",
                    f"- Memory Usage: {result.metrics.efficiency.memory_usage:.2f} MB",
                    f"",
                ]
            )

            report_lines.extend(strategy_lines)

        # Add recommendations
        report_lines.extend(
            [
                f"## Recommendations",
                f"",
                self._generate_recommendations(comparison),
            ]
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

    def _generate_recommendations(self, comparison: ComparisonResult) -> str:
        """
        Generate recommendations based on comparison results.

        Args:
            comparison: Comparison result

        Returns:
            Recommendations text
        """
        winner = next(
            r for r in comparison.results if r.strategy_name == comparison.winner
        )

        recommendations = [
            f"**Best Overall Strategy:** {comparison.winner}",
            f"",
            f"This strategy achieved the highest NDCG@K score of {winner.metrics.retrieval.ndcg_at_k:.4f}, "
            f"indicating superior retrieval quality.",
            f"",
        ]

        # Find fastest strategy
        fastest = min(
            comparison.results, key=lambda r: r.metrics.efficiency.indexing_time
        )
        if fastest.strategy_name != comparison.winner:
            recommendations.append(
                f"**Fastest Strategy:** {fastest.strategy_name} "
                f"({fastest.metrics.efficiency.indexing_time:.2f}s indexing time)"
            )
            recommendations.append("")

        # Find most memory efficient
        most_efficient = min(
            comparison.results, key=lambda r: r.metrics.efficiency.memory_usage
        )
        if most_efficient.strategy_name not in [
            comparison.winner,
            fastest.strategy_name,
        ]:
            recommendations.append(
                f"**Most Memory Efficient:** {most_efficient.strategy_name} "
                f"({most_efficient.metrics.efficiency.memory_usage:.2f} MB)"
            )
            recommendations.append("")

        # Quality vs Speed tradeoff
        recommendations.extend(
            [
                "**Tradeoff Analysis:**",
                "",
                "- If retrieval quality is paramount, use the best overall strategy.",
                "- If speed is critical, consider the fastest strategy if the quality difference is acceptable.",
                "- For resource-constrained environments, the most memory-efficient strategy may be preferred.",
            ]
        )

        return "\n".join(recommendations)

    def print_comparison(self, comparison: ComparisonResult) -> None:
        """
        Print comparison results to console.

        Args:
            comparison: Comparison result
        """
        print(f"\n{'='*80}")
        print(f"RAG Strategy Comparison - Dataset: {comparison.dataset_name}")
        print(f"{'='*80}\n")

        print(comparison.comparison_table.to_string(index=False))

        print(f"\n{'='*80}")
        print(f"WINNER: {comparison.winner}")
        print(f"{'='*80}\n")
