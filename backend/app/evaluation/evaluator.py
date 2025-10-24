"""Main evaluator for RAG pipeline performance."""

import asyncio
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, List, Dict

import structlog




from .dataset import EvaluationDataset, EvaluationQuery
from .metrics import (
    ComprehensiveMetrics,
    EfficiencyMetrics,
    EvaluationMetrics,
    PerformanceTimer,
    RAGMetrics,
    RetrievalMetrics,
)

logger = structlog.get_logger(__name__)


@dataclass
class EvaluationConfig:
    """Configuration for evaluation."""

    top_k: int = 10
    relevance_threshold: float = 0.5
    use_ragas: bool = False  # Whether to compute RAGAS metrics (requires LLM)
    cleanup_after: bool = True  # Clean up vector store after evaluation


@dataclass
class QueryResult:
    """Result for a single query evaluation."""

    query: str
    retrieved_chunk_ids: List[str]
    retrieved_doc_ids: List[str]
    relevance_scores: List[float]
    retrieval_time: float
    ground_truth_doc_ids: List[str]


@dataclass
class EvaluationResult:
    """Complete evaluation result for a strategy."""

    strategy_name: str
    dataset_name: str
    metrics: ComprehensiveMetrics
    query_results: List[QueryResult]
    config: EvaluationConfig
    metadata: Dict[str, Any]


class RAGEvaluator:
    """
    Evaluator for RAG pipeline components.

    Evaluates chunking and embedding strategies on retrieval quality and efficiency.
    """

    def __init__(
        self,
        chunker: Any,
        embedder: Any,
        vector_store: Any,
        config: Optional[EvaluationConfig] = None,
        strategy_name: Optional[str] = None,
    ):
        """
        Initialize evaluator.

        Args:
            chunker: Chunker instance to evaluate
            embedder: Embedder instance to evaluate
            vector_store: Vector store for retrieval
            config: Evaluation configuration
            strategy_name: Strategy name for unique collection naming (optional)
        """
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.config = config or EvaluationConfig()
        self._strategy_name = strategy_name

        # Create unique collection name for this evaluation
        self.collection_name = self._generate_collection_name()

    def _generate_collection_name(self) -> str:
        """
        Generate unique collection name for this evaluation.

        Uses strategy name if provided, otherwise falls back to chunker+embedder class names.
        For parallel execution, this ensures each strategy has a unique collection.
        """
        if self._strategy_name:
            # Use strategy name for true uniqueness (handles same class, different params)
            hash_str = self._strategy_name
        else:
            # Fallback: use class names + embedder-specific attributes
            chunker_name = self.chunker.__class__.__name__
            embedder_name = self.embedder.__class__.__name__

            # Add embedder-specific attributes to ensure uniqueness
            embedder_attrs = []
            if hasattr(self.embedder, "base_url"):
                embedder_attrs.append(str(self.embedder.base_url))
            if hasattr(self.embedder, "embedding_dim"):
                embedder_attrs.append(str(self.embedder.embedding_dim))
            elif hasattr(self.embedder, "default_dimension"):
                embedder_attrs.append(str(self.embedder.default_dimension))

            hash_str = f"{chunker_name}_{embedder_name}_{'_'.join(embedder_attrs)}"

        hash_suffix = hashlib.md5(hash_str.encode()).hexdigest()[:8]
        return f"eval_{hash_suffix}"

    async def evaluate(
        self, dataset: EvaluationDataset, strategy_name: Optional[str] = None
    ) -> EvaluationResult:
        """
        Run complete evaluation on a dataset.

        Args:
            dataset: Evaluation dataset
            strategy_name: Name for this strategy (auto-generated if None)

        Returns:
            EvaluationResult with all metrics
        """
        if strategy_name is None:
            strategy_name = (
                f"{self.chunker.__class__.__name__}+{self.embedder.__class__.__name__}"
            )

        logger.info(
            "starting_evaluation",
            strategy=strategy_name,
            dataset=dataset.name,
            num_docs=len(dataset.documents),
            num_queries=len(dataset.queries),
        )

        # Validate dataset
        errors = dataset.validate()
        if errors:
            raise ValueError(f"Dataset validation failed:\n" + "\n".join(errors))

        try:
            # 1. Index documents and measure efficiency
            efficiency_metrics = await self._index_documents(dataset)

            # 2. Run queries and measure retrieval quality
            query_results, avg_query_latency = await self._run_queries(dataset)

            # Update efficiency metrics with query latency
            efficiency_metrics.query_latency = avg_query_latency

            # 3. Calculate retrieval metrics
            retrieval_metrics = self._calculate_retrieval_metrics(query_results)

            # 4. Calculate RAGAS metrics if enabled
            rag_metrics = None
            if self.config.use_ragas:
                rag_metrics = await self._calculate_ragas_metrics(
                    query_results, dataset
                )

            # Combine all metrics
            comprehensive_metrics = ComprehensiveMetrics(
                retrieval=retrieval_metrics,
                efficiency=efficiency_metrics,
                rag=rag_metrics,
            )

            result = EvaluationResult(
                strategy_name=strategy_name,
                dataset_name=dataset.name,
                metrics=comprehensive_metrics,
                query_results=query_results,
                config=self.config,
                metadata={
                    "chunker": self.chunker.__class__.__name__,
                    "embedder": self.embedder.__class__.__name__,
                    "collection": self.collection_name,
                },
            )

            logger.info(
                "evaluation_completed",
                strategy=strategy_name,
                ndcg=retrieval_metrics.ndcg_at_k,
                mrr=retrieval_metrics.mrr,
                indexing_time=efficiency_metrics.indexing_time,
            )

            return result

        finally:
            # Cleanup if configured
            if self.config.cleanup_after:
                await self._cleanup()

    async def _index_documents(self, dataset: EvaluationDataset) -> EfficiencyMetrics:
        """
        Index all documents and measure efficiency.

        Args:
            dataset: Evaluation dataset

        Returns:
            EfficiencyMetrics
        """
        logger.info("indexing_documents", num_docs=len(dataset.documents))

        # Create collection with correct dimension
        if self.vector_store.collection_exists(self.collection_name):
            self.vector_store.delete_collection(self.collection_name)

        # Get dimension from embedder
        if hasattr(self.embedder, "default_dimension"):
            dimension = self.embedder.default_dimension
        elif hasattr(self.embedder, "dimension"):
            dimension = self.embedder.dimension
        else:
            # Default to 1024 for BGE-M3
            dimension = 1024

        self.vector_store.create_collection(
            dimension=dimension, collection_name=self.collection_name
        )

        all_chunks: List[BaseChunk] = []
        total_tokens = 0

        # Chunk all documents
        timer = PerformanceTimer()
        with timer:
            for eval_doc in dataset.documents:
                # Convert to BaseDocument
                from datetime import datetime

                notion_doc = BaseDocument(
                    id=eval_doc.doc_id,
                    datasource_id="eval_dataset",
                    source_type="notion",
                    title=eval_doc.title or eval_doc.doc_id,
                    content=eval_doc.content,
                    content_hash="",
                    url=f"https://eval.local/{eval_doc.doc_id}",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )

                # Chunk document
                chunks = self.chunker.chunk_document(notion_doc)
                all_chunks.extend(chunks)

                # Count tokens (approximate)
                total_tokens += len(eval_doc.content.split())

            # Embed chunks
            if all_chunks:
                # Check if embedder has embed_chunks method, otherwise use embed_texts
                if hasattr(self.embedder, "embed_chunks"):
                    embeddings = self.embedder.embed_chunks(all_chunks)
                else:
                    # For embedders like MatryoshkaEmbedder that only have embed_texts
                    chunk_texts = [chunk.content for chunk in all_chunks]
                    embeddings = self.embedder.embed_texts(chunk_texts)

                # Store in vector store
                self.vector_store.add_chunks(
                    all_chunks, embeddings, collection_name=self.collection_name
                )

        indexing_time = timer.get_elapsed()

        # Calculate memory usage (approximate)
        if all_chunks and embeddings and embeddings.get("dense"):
            embedding_dim = len(embeddings["dense"][0])
            # 4 bytes per float32 + metadata overhead
            memory_mb = (len(all_chunks) * embedding_dim * 4) / (1024 * 1024)
        else:
            memory_mb = 0.0

        avg_chunk_size = total_tokens / len(all_chunks) if all_chunks else 0.0

        logger.info(
            "indexing_completed",
            num_chunks=len(all_chunks),
            indexing_time=indexing_time,
            memory_mb=memory_mb,
        )

        return EfficiencyMetrics(
            indexing_time=indexing_time,
            query_latency=0.0,  # Will be updated later
            memory_usage=memory_mb,
            num_chunks=len(all_chunks),
            avg_chunk_size=avg_chunk_size,
            total_tokens=total_tokens,
        )

    async def _run_queries(
        self, dataset: EvaluationDataset
    ) -> tuple[List[QueryResult], float]:
        """
        Run all queries and collect results.

        Args:
            dataset: Evaluation dataset

        Returns:
            Tuple of (List of QueryResult, average query latency in seconds)
        """
        logger.info("running_queries", num_queries=len(dataset.queries))

        query_results = []
        total_query_time = 0.0

        for eval_query in dataset.queries:
            timer = PerformanceTimer()
            with timer:
                # Embed query with correct dimension
                if hasattr(self.embedder, "default_dimension"):
                    # Force use of default dimension for consistency
                    query_embedding = self.embedder.embed_query(
                        eval_query.query, dimension=self.embedder.default_dimension
                    )
                else:
                    query_embedding = self.embedder.embed_query(eval_query.query)

                # Search vector store
                results = self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=self.config.top_k,
                    collection_name=self.collection_name,
                )

            retrieval_time = timer.get_elapsed()
            total_query_time += retrieval_time

            # Extract chunk and document IDs
            retrieved_chunk_ids = [r.chunk_id for r in results]
            retrieved_doc_ids = [r.document_id for r in results]

            # Calculate relevance scores based on ground truth
            relevance_scores = self._calculate_relevance_scores(
                retrieved_doc_ids, eval_query.relevant_doc_ids
            )

            query_result = QueryResult(
                query=eval_query.query,
                retrieved_chunk_ids=retrieved_chunk_ids,
                retrieved_doc_ids=retrieved_doc_ids,
                relevance_scores=relevance_scores,
                retrieval_time=retrieval_time,
                ground_truth_doc_ids=eval_query.relevant_doc_ids,
            )

            query_results.append(query_result)

        # Calculate average query latency
        avg_query_latency = (
            total_query_time / len(query_results) if query_results else 0.0
        )

        return query_results, avg_query_latency

    def _calculate_relevance_scores(
        self, retrieved_doc_ids: List[str], ground_truth_doc_ids: List[str]
    ) -> List[float]:
        """
        Calculate binary relevance scores.

        Args:
            retrieved_doc_ids: Retrieved document IDs
            ground_truth_doc_ids: Ground truth relevant document IDs

        Returns:
            List of relevance scores (1.0 if relevant, 0.0 otherwise)
        """
        return [
            1.0 if doc_id in ground_truth_doc_ids else 0.0
            for doc_id in retrieved_doc_ids
        ]

    def _calculate_retrieval_metrics(
        self, query_results: List[QueryResult]
    ) -> RetrievalMetrics:
        """
        Aggregate retrieval metrics across all queries.

        Args:
            query_results: Results from all queries

        Returns:
            Aggregated RetrievalMetrics
        """
        all_ndcg = []
        all_mrr = []
        all_precision = []
        all_recall = []
        all_hit_rate = []
        all_relevance_scores = []

        for result in query_results:
            total_relevant = len(result.ground_truth_doc_ids)

            # Calculate metrics for this query
            ndcg = EvaluationMetrics.calculate_ndcg_at_k(
                result.relevance_scores, self.config.top_k
            )
            mrr = EvaluationMetrics.calculate_mrr(
                result.relevance_scores, self.config.relevance_threshold
            )
            precision = EvaluationMetrics.calculate_precision_at_k(
                result.relevance_scores,
                self.config.top_k,
                self.config.relevance_threshold,
            )
            recall = EvaluationMetrics.calculate_recall_at_k(
                result.relevance_scores,
                total_relevant,
                self.config.top_k,
                self.config.relevance_threshold,
            )
            hit_rate = EvaluationMetrics.calculate_hit_rate(
                result.relevance_scores, self.config.relevance_threshold
            )

            all_ndcg.append(ndcg)
            all_mrr.append(mrr)
            all_precision.append(precision)
            all_recall.append(recall)
            all_hit_rate.append(hit_rate)
            all_relevance_scores.append(result.relevance_scores)

        # Calculate MAP
        map_score = EvaluationMetrics.calculate_map(
            all_relevance_scores, self.config.relevance_threshold
        )

        # Average metrics
        return RetrievalMetrics(
            ndcg_at_k=sum(all_ndcg) / len(all_ndcg) if all_ndcg else 0.0,
            mrr=sum(all_mrr) / len(all_mrr) if all_mrr else 0.0,
            precision_at_k=(
                sum(all_precision) / len(all_precision) if all_precision else 0.0
            ),
            recall_at_k=sum(all_recall) / len(all_recall) if all_recall else 0.0,
            hit_rate=sum(all_hit_rate) / len(all_hit_rate) if all_hit_rate else 0.0,
            map_score=map_score,
        )

    async def _calculate_ragas_metrics(
        self, query_results: List[QueryResult], dataset: EvaluationDataset
    ) -> Optional[RAGMetrics]:
        """
        Calculate RAGAS metrics (requires LLM).

        Args:
            query_results: Results from all queries
            dataset: Evaluation dataset

        Returns:
            RAGMetrics or None if RAGAS is not available
        """
        try:
            from datasets import Dataset as HFDataset
            from ragas import evaluate

            # Configure RAGAS to use Claude (Anthropic) instead of OpenAI
            from langchain_anthropic import ChatAnthropic
            from ragas.llms import LangchainLLMWrapper
            from app.config import settings

            # Initialize Claude LLM for RAGAS (use same model as answer generation)
            # Increase max_tokens to avoid LLMDidNotFinishException
            claude_llm = ChatAnthropic(
                model=settings.llm_model,  # claude-sonnet-4-20250514
                temperature=0,
                max_tokens=4096,  # Increased from 1024 to handle longer evaluations
            )
            ragas_llm = LangchainLLMWrapper(claude_llm)

            logger.info(
                "ragas_llm_configured",
                model=settings.llm_model,
                provider="anthropic",
            )

            # Configure RAGAS embeddings (to avoid OpenAI default)
            # Use LangchainEmbeddingsWrapper for compatibility with RAGAS 0.3.6
            from langchain_community.embeddings import (
                HuggingFaceEmbeddings as LangchainHFEmbeddings,
            )
            from ragas.embeddings import LangchainEmbeddingsWrapper

            # Create Langchain embeddings first
            langchain_embeddings = LangchainHFEmbeddings(
                model_name="BAAI/bge-m3"  # Multilingual, high-quality model
            )

            # Wrap for RAGAS compatibility
            ragas_embeddings = LangchainEmbeddingsWrapper(langchain_embeddings)

            logger.info(
                "ragas_embeddings_configured",
                model="BAAI/bge-m3",
                provider="huggingface",
                wrapper="LangchainEmbeddingsWrapper",
            )

            # Import RAGAS metrics (using class names for newer versions)
            # Modern RAGAS uses class names (ContextRelevance) not functions
            try:
                from ragas.metrics import (
                    AnswerRelevancy,
                    ContextPrecision,
                    ContextRecall,
                    ContextRelevance,
                    Faithfulness,
                )

                # Instantiate metrics with Claude LLM AND HuggingFace embeddings
                # Note: Only AnswerRelevancy requires embeddings (for similarity calculation)
                answer_relevancy = AnswerRelevancy(
                    llm=ragas_llm, embeddings=ragas_embeddings
                )
                context_precision = ContextPrecision(llm=ragas_llm)
                context_recall = ContextRecall(llm=ragas_llm)
                context_relevance = ContextRelevance(llm=ragas_llm)
                faithfulness = Faithfulness(llm=ragas_llm)
                context_relevance_key = "context_relevance"
            except ImportError:
                # Fallback for older versions that use lowercase functions
                from ragas.metrics import (
                    answer_relevancy,
                    context_precision,
                    context_recall,
                    faithfulness,
                )

                context_relevance = None  # May not be available in old versions
                context_relevance_key = "context_relevancy"

            logger.info(
                "calculating_ragas_metrics",
                num_queries=len(query_results),
                ragas_version=context_relevance_key,
            )

            # Generate answers for each query using Claude
            from app.pipeline.generators.claude import ClaudeGenerator

            generator = ClaudeGenerator()

            # Prepare data for RAGAS evaluation
            ragas_data = {
                "question": [],
                "answer": [],
                "contexts": [],
                "ground_truth": [],
            }

            for i, query_result in enumerate(query_results):
                logger.info(
                    "generating_answer_for_ragas",
                    query_num=i + 1,
                    total=len(query_results),
                )

                # Get query from dataset
                eval_query = next(
                    q for q in dataset.queries if q.query == query_result.query
                )

                # Get retrieved contexts (chunk contents) - batch retrieval for efficiency
                chunk_ids = query_result.retrieved_chunk_ids
                if not chunk_ids:
                    logger.warning(
                        "no_chunk_ids_in_query_result", query=query_result.query
                    )
                    continue

                # Retrieve all chunks at once instead of one by one
                retrieved_chunks = self.vector_store.get_by_ids(
                    chunk_ids, collection_name=self.collection_name
                )

                # Build chunk_id -> content mapping to maintain order
                chunk_map = {
                    chunk.get("chunk_id"): chunk.get("content", "")
                    for chunk in retrieved_chunks
                    if chunk.get("content")
                }

                # Reconstruct contexts in original retrieval order
                contexts = [chunk_map[cid] for cid in chunk_ids if cid in chunk_map]

                if not contexts:
                    logger.warning("no_contexts_retrieved", query=query_result.query)
                    continue

                # Generate answer using Claude
                try:
                    # Build context string for generator
                    context_str = "\n\n".join(
                        f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)
                    )

                    answer, _ = generator.generate(
                        question=query_result.query, context=context_str
                    )

                    # Skip if no expected_answer (required for RAGAS)
                    if not eval_query.expected_answer:
                        logger.warning(
                            "skipping_query_for_ragas_no_ground_truth",
                            query=query_result.query,
                        )
                        continue

                    # Add to RAGAS dataset
                    ragas_data["question"].append(query_result.query)
                    ragas_data["answer"].append(answer)
                    ragas_data["contexts"].append(contexts)
                    ragas_data["ground_truth"].append(eval_query.expected_answer)

                except Exception as e:
                    logger.error(
                        "answer_generation_failed",
                        query=query_result.query,
                        error=str(e),
                    )
                    continue

            # Check if we have any valid data
            if not ragas_data["question"]:
                logger.warning("no_valid_data_for_ragas")
                return None

            # Check minimum sample requirement for RAGAS
            MIN_RAGAS_SAMPLES = 3
            num_samples = len(ragas_data["question"])
            if num_samples < MIN_RAGAS_SAMPLES:
                logger.warning(
                    "insufficient_ragas_samples",
                    samples=num_samples,
                    min_required=MIN_RAGAS_SAMPLES,
                    message=f"RAGAS requires at least {MIN_RAGAS_SAMPLES} samples for reliable evaluation. "
                    f"Got {num_samples}. Evaluation may be unreliable.",
                )
                # Still continue but warn the user

            # Create HuggingFace Dataset
            hf_dataset = HFDataset.from_dict(ragas_data)

            logger.info(
                "running_ragas_evaluation", num_samples=len(ragas_data["question"])
            )

            # Run RAGAS evaluation
            # Build metrics list (filter out None in case context_relevance isn't available)
            metrics_list = [
                m
                for m in [
                    context_relevance,
                    context_precision,
                    context_recall,
                    answer_relevancy,
                    faithfulness,
                ]
                if m is not None
            ]

            result = evaluate(
                hf_dataset,
                metrics=metrics_list,
            )

            logger.info("ragas_evaluation_completed", result=result)

            # Extract metrics from RAGAS result object
            # Convert to dict to handle different RAGAS versions
            try:
                # RAGAS returns a Result object, convert to dict
                if hasattr(result, "to_pandas"):
                    # RAGAS 0.2+ returns Result with to_pandas() method
                    result_dict = result.to_pandas().to_dict()
                    # Get mean values if available
                    if isinstance(next(iter(result_dict.values())), dict):
                        result_dict = {
                            k: list(v.values())[0] if v else 0.0
                            for k, v in result_dict.items()
                        }
                elif hasattr(result, "items"):
                    result_dict = dict(result)
                elif hasattr(result, "__dict__"):
                    result_dict = result.__dict__
                else:
                    # Try to convert using dict()
                    result_dict = dict(result)

                logger.info("ragas_result_dict", result_dict=result_dict)

                # Extract values with proper fallbacks (avoid or chains with 0.0)
                context_rel_value = 0.0
                if "nv_context_relevance" in result_dict:
                    context_rel_value = float(result_dict["nv_context_relevance"])
                elif context_relevance_key in result_dict:
                    context_rel_value = float(result_dict[context_relevance_key])

                answer_rel_value = (
                    float(result_dict.get("answer_relevancy", 0.0))
                    if "answer_relevancy" in result_dict
                    else 0.0
                )
                faithfulness_value = (
                    float(result_dict.get("faithfulness", 0.0))
                    if "faithfulness" in result_dict
                    else 0.0
                )
                context_recall_value = (
                    float(result_dict.get("context_recall", 0.0))
                    if "context_recall" in result_dict
                    else 0.0
                )
                context_precision_value = (
                    float(result_dict.get("context_precision", 0.0))
                    if "context_precision" in result_dict
                    else 0.0
                )
            except Exception as e:
                logger.error(
                    "ragas_metrics_extraction_failed",
                    error=str(e),
                    result_type=type(result).__name__,
                )
                # Set all to 0.0 on error
                context_rel_value = 0.0
                answer_rel_value = 0.0
                faithfulness_value = 0.0
                context_recall_value = 0.0
                context_precision_value = 0.0

            logger.info(
                "ragas_metrics_extracted",
                context_relevance=context_rel_value,
                answer_relevancy=answer_rel_value,
                faithfulness=faithfulness_value,
                context_recall=context_recall_value,
                context_precision=context_precision_value,
            )

            return RAGMetrics(
                context_relevance=context_rel_value,
                answer_relevance=answer_rel_value,
                faithfulness=faithfulness_value,
                context_recall=context_recall_value,
                context_precision=context_precision_value,
            )

        except ImportError as e:
            logger.warning("ragas_not_installed", error=str(e))
            return None
        except Exception as e:
            logger.error("ragas_calculation_failed", error=str(e))
            return None

    async def _cleanup(self) -> None:
        """Clean up evaluation resources."""
        logger.info("cleaning_up", collection=self.collection_name)
        try:
            if self.vector_store.collection_exists(self.collection_name):
                self.vector_store.delete_collection(self.collection_name)
        except Exception as e:
            logger.warning("cleanup_failed", error=str(e))
