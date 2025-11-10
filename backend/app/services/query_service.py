"""Query Service for RAG search and answer generation."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import structlog

from app.models.rag import RAGConfiguration
from app.models.pipeline import Pipeline, PipelineType
from app.models.evaluation_query import EvaluationQuery
from app.services.rag_factory import RAGFactory
from app.services.qdrant_service import QdrantService
from app.core.config import settings

logger = structlog.get_logger(__name__)


class QueryResult:
    """Result of a query search."""
    
    def __init__(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        search_time: float,
        rerank_time: Optional[float] = None,
        comparison: Optional[Dict[str, Any]] = None,
        pipeline_type: str = "normal",
    ):
        """
        Initialize QueryResult.
        
        Args:
            query: Original query text
            chunks: List of retrieved chunks with metadata
            search_time: Time taken for vector search (seconds)
            rerank_time: Time taken for reranking (seconds)
            comparison: Comparison with golden chunks (test pipelines only)
            pipeline_type: Pipeline type (normal or test)
        """
        self.query = query
        self.chunks = chunks
        self.search_time = search_time
        self.rerank_time = rerank_time
        self.total_time = search_time + (rerank_time or 0)
        self.comparison = comparison
        self.pipeline_type = pipeline_type


class QueryService:
    """Service for querying RAG configurations."""

    def __init__(self, db: Session, qdrant_service: QdrantService):
        """
        Initialize QueryService.
        
        Args:
            db: Database session
            qdrant_service: Qdrant service instance
        """
        self.db = db
        self.qdrant_service = qdrant_service

    def search(
        self,
        pipeline_id: int,
        query: str,
        top_k: int = 5,
    ) -> QueryResult:
        """
        Search for relevant chunks using a pipeline (RAG + DataSources).
        
        Steps:
        1. Load Pipeline to get RAG configuration and datasource IDs
        2. Create embedder and reranker from RAG config
        3. Embed query
        4. Search Qdrant (retrieve top_k * rerank_multiplier for reranking)
        5. Rerank results (top_k * rerank_multiplier → top_k)
        
        Args:
            pipeline_id: Pipeline ID (includes RAG + DataSources)
            query: Query text
            top_k: Number of final results to return
            
        Returns:
            QueryResult with retrieved chunks and timing info
            
        Raises:
            ValueError: If Pipeline not found
        """
        import time
        
        # Load Pipeline
        pipeline = self.db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        
        # Extract RAG and datasource IDs from pipeline
        rag = pipeline.rag
        datasource_ids = [ds.id for ds in pipeline.datasources]
        
        logger.info(
            "query_started",
            pipeline_id=pipeline_id,
            rag_id=rag.id,
            datasource_count=len(datasource_ids),
            query=query[:100],
            top_k=top_k
        )
        
        # Create embedder and reranker
        embedder = RAGFactory.create_embedder(
            rag.embedding_module,
            rag.embedding_params
        )
        reranker = RAGFactory.create_reranker(
            rag.reranking_module,
            rag.reranking_params
        )
        
        # Embed query (prefer embed_query if available, fallback to embed_texts)
        query_dense: list[float]
        query_sparse: dict | None = None
        if hasattr(embedder, "embed_query"):
            q = embedder.embed_query(query)
            # Expected dict keys: 'dense', optionally 'sparse'
            query_dense = q.get("dense") if isinstance(q, dict) else q  # type: ignore
            query_sparse = q.get("sparse") if isinstance(q, dict) else None  # type: ignore
        else:
            q = embedder.embed_texts([query])
            query_dense = q.get("dense")[0]
            query_sparse = None
        
        # Search Qdrant (retrieve more for reranking)
        # Use configurable multiplier (default: 3x)
        # This allows reranker to have more candidates to choose from
        search_limit = top_k * settings.rerank_multiplier if rag.reranking_module != "none" else top_k
        
        search_start = time.time()
        # Build filter conditions: 파이프라인 ID로 필터링
        # 이렇게 하면 해당 파이프라인에 속한 벡터만 검색됩니다
        filter_conditions = {"pipeline_id": pipeline_id}

        search_results = self.qdrant_service.search(
            collection_name=rag.collection_name,
            query_vector=query_dense,
            top_k=search_limit,
            filter_conditions=filter_conditions,
            query_sparse_vector=query_sparse,  # Hybrid search with sparse vector if available
        )
        search_time = time.time() - search_start
        
        logger.info(
            "vector_search_completed",
            pipeline_id=pipeline_id,
            rag_id=rag.id,
            num_results=len(search_results),
            search_time=search_time
        )
        
        # Prepare chunks for reranking
        chunks = []
        for result in search_results:
            payload = result.get("payload", {})
            chunks.append({
                "id": result.get("id"),
                "content": payload.get("content", ""),
                "score": result.get("score"),
                "datasource_id": payload.get("datasource_id"),
                "chunk_index": payload.get("chunk_index"),
                "metadata": payload.get("metadata", {}),
            })
        
        # Rerank if needed
        rerank_time = None
        if rag.reranking_module != "none" and chunks:
            rerank_start = time.time()
            
            # Prepare for reranking using RetrievedDocument schema
            from app.reranking.rerankers.base_reranker import RetrievedDocument
            docs = [
                RetrievedDocument(
                    id=c["id"],
                    content=c["content"],
                    score=float(c.get("score") or 0.0),
                    metadata=c.get("metadata"),
                )
                for c in chunks
            ]
            
            # Log top 10 chunks BEFORE reranking for detailed analysis
            before_top10_info = []
            for i, c in enumerate(chunks[:10]):
                doc_id = c.get("metadata", {}).get("doc_id", "N/A")
                before_top10_info.append({
                    "rank": i + 1,
                    "chunk_id": c["id"],
                    "doc_id": doc_id,
                    "vector_score": c.get("score"),
                    "content_preview": c["content"][:100],
                })
            
            reranked_docs = reranker.rerank(query, docs, top_k=top_k)
            
            # Map back to chunks preserving the same dict structure
            # IMPORTANT: Update score with rerank score!
            id_to_chunk = {c["id"]: c for c in chunks}
            chunks = []
            for d in reranked_docs:
                if d.id in id_to_chunk:
                    chunk = id_to_chunk[d.id].copy()  # Copy to avoid mutation
                    chunk["score"] = d.score  # Update with rerank score!
                    chunks.append(chunk)
            
            # Log top 10 chunks AFTER reranking for detailed analysis
            after_top10_info = []
            for i, c in enumerate(chunks[:10]):
                doc_id = c.get("metadata", {}).get("doc_id", "N/A")
                after_top10_info.append({
                    "rank": i + 1,
                    "chunk_id": c["id"],
                    "doc_id": doc_id,
                    "rerank_score": c.get("score"),  # This is now rerank score
                    "content_preview": c["content"][:100],
                })
            
            rerank_time = time.time() - rerank_start
            
            # Extract doc_ids for comparison
            before_doc_ids = [info["doc_id"] for info in before_top10_info]
            after_doc_ids = [info["doc_id"] for info in after_top10_info]
            
            logger.info(
                "reranking_detailed_comparison",
                pipeline_id=pipeline_id,
                rag_id=rag.id,
                reranking_module=rag.reranking_module,
                query=query[:100],
                num_candidates=len(docs),
                num_results=len(chunks),
                rerank_time=rerank_time,
                before_doc_ids=before_doc_ids,
                after_doc_ids=after_doc_ids,
                docs_changed=(before_doc_ids != after_doc_ids),
                before_top10=before_top10_info,
                after_top10=after_top10_info,
            )
        else:
            # No reranking, just take top_k
            chunks = chunks[:top_k]
        
        # If test pipeline, compare with golden chunks
        comparison = None
        if pipeline.pipeline_type == PipelineType.TEST and pipeline.dataset:
            comparison = self._compare_with_golden_chunks(
                pipeline=pipeline,
                query_text=query,
                retrieved_chunks=chunks,
                top_k=top_k
            )
        
        result = QueryResult(
            query=query,
            chunks=chunks,
            search_time=search_time,
            rerank_time=rerank_time,
            comparison=comparison,
            pipeline_type=pipeline.pipeline_type.value,
        )
        
        logger.info(
            "query_completed",
            pipeline_id=pipeline_id,
            rag_id=rag.id,
            total_time=result.total_time,
            num_chunks=len(chunks),
            has_comparison=comparison is not None
        )
        
        return result

    def answer(
        self,
        pipeline_id: int,
        query: str,
        top_k: int = 5,
        system_prompt: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate an answer using retrieved chunks and LLM.
        
        Steps:
        1. Search for relevant chunks using pipeline
        2. Format context from chunks
        3. Create generator from llm_config
        4. Call LLM with context and query
        5. Return answer with sources
        
        Args:
            pipeline_id: Pipeline ID (includes RAG + DataSources)
            query: Query text
            top_k: Number of chunks to retrieve
            system_prompt: Custom system prompt (overrides default)
            llm_config: LLM configuration dict with keys:
                - type: 'claude' or 'vllm'
                - model_name: str
                - api_key: Optional[str] (for Claude)
                - endpoint: Optional[str] (for vLLM)
                - parameters: Optional[dict] (temperature, max_tokens, top_p)
            
        Returns:
            Dict with keys:
                - query: str
                - answer: str
                - sources: List[Dict]
                - tokens_used: int
                - total_time: float
                - search_time: float
                - llm_time: float
            
        Raises:
            ValueError: If Pipeline not found or llm_config invalid
        """
        import time
        from app.services.generation.base import GenerationConfig, format_context
        from app.services.generation.factory import GeneratorFactory
        
        if not llm_config:
            raise ValueError("llm_config is required for answer generation")
        
        # Step 1: Search for relevant chunks
        search_start = time.time()
        search_result = self.search(
            pipeline_id=pipeline_id,
            query=query,
            top_k=top_k,
        )
        search_time = time.time() - search_start
        
        # Step 2: Format context from chunks
        context = format_context(search_result.chunks)
        
        # Step 3: Create generator from config
        generator = GeneratorFactory.create(
            model_type=llm_config.get("type"),
            model_name=llm_config.get("model_name"),
            api_key=llm_config.get("api_key"),
            endpoint=llm_config.get("endpoint"),
        )
        
        # Step 4: Prepare generation config
        params = llm_config.get("parameters", {})
        gen_config = GenerationConfig(
            temperature=params.get("temperature", 0.7),
            max_tokens=params.get("max_tokens", 1000),
            top_p=params.get("top_p", 0.9),
        )
        
        # Step 5: Generate answer
        gen_result = generator.generate(
            query=query,
            context=context,
            config=gen_config,
            system_prompt=system_prompt,
        )
        
        # Step 6: Return complete result
        return {
            "query": query,
            "answer": gen_result.answer,
            "sources": search_result.chunks,
            "tokens_used": gen_result.tokens_used,
            "total_time": search_time + gen_result.generation_time,
            "search_time": search_time,
            "llm_time": gen_result.generation_time,
        }

    def batch_search(
        self,
        pipeline_id: int,
        queries: List[str],
        top_k: int = 5,
    ) -> List[QueryResult]:
        """
        Batch search for multiple queries using a pipeline.
        
        Args:
            pipeline_id: Pipeline ID (includes RAG + DataSources)
            queries: List of query texts
            top_k: Number of results per query
            
        Returns:
            List of QueryResult objects
        """
        results = []
        for query in queries:
            try:
                result = self.search(
                    pipeline_id=pipeline_id,
                    query=query,
                    top_k=top_k,
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "batch_search_query_failed",
                    pipeline_id=pipeline_id,
                    query=query[:100],
                    error=str(e)
                )
                # Add empty result
                results.append(QueryResult(
                    query=query,
                    chunks=[],
                    search_time=0.0,
                ))
        
        return results

    def _compare_with_golden_chunks(
        self,
        pipeline: Pipeline,
        query_text: str,
        retrieved_chunks: List[Dict[str, Any]],
        top_k: int
    ) -> Optional[Dict[str, Any]]:
        """
        Test Pipeline의 검색 결과를 정답 청크와 비교
        
        Args:
            pipeline: Test Pipeline 객체
            query_text: 쿼리 텍스트
            retrieved_chunks: 검색된 청크들
            top_k: Top K
            
        Returns:
            비교 결과 딕셔너리 (precision, recall, hit_rate 등)
        """
        if not pipeline.dataset:
            return None
        
        dataset = pipeline.dataset
        
        # Find matching query in dataset
        matching_query = None
        for q in dataset.queries:
            if q.query.strip().lower() == query_text.strip().lower():
                matching_query = q
                break
        
        if not matching_query:
            logger.warning(
                "query_not_found_in_dataset",
                query=query_text[:100],
                dataset_id=dataset.id
            )
            return None
        
        # Get golden doc_ids
        golden_doc_ids = set(matching_query.relevant_doc_ids or [])
        if not golden_doc_ids:
            logger.warning(
                "no_golden_docs_for_query",
                query_id=matching_query.id,
                query=query_text[:100]
            )
            return None
        
        # Extract retrieved doc_ids from chunks
        # Chunk metadata should contain "doc_id" from EvaluationDocument
        retrieved_doc_ids = set()
        for chunk in retrieved_chunks:
            metadata = chunk.get("metadata", {})
            doc_id = metadata.get("doc_id")
            if doc_id:
                retrieved_doc_ids.add(doc_id)
        
        # Calculate metrics
        true_positives = len(golden_doc_ids & retrieved_doc_ids)
        
        # Precision@K: 검색된 K개 중 정답 비율
        precision_at_k = true_positives / len(retrieved_doc_ids) if retrieved_doc_ids else 0.0
        
        # Recall@K: 전체 정답 중 검색된 비율
        recall_at_k = true_positives / len(golden_doc_ids) if golden_doc_ids else 0.0
        
        # Hit Rate: 하나라도 정답을 찾았는지
        hit_rate = 1.0 if true_positives > 0 else 0.0
        
        comparison = {
            "query_id": matching_query.id,
            "query_text": query_text,
            "golden_doc_ids": list(golden_doc_ids),
            "retrieved_doc_ids": list(retrieved_doc_ids),
            "true_positives": true_positives,
            "precision_at_k": precision_at_k,
            "recall_at_k": recall_at_k,
            "hit_rate": hit_rate,
        }
        
        logger.info(
            "query_comparison_completed",
            query_id=matching_query.id,
            precision=precision_at_k,
            recall=recall_at_k,
            hit_rate=hit_rate,
            golden_count=len(golden_doc_ids),
            retrieved_count=len(retrieved_doc_ids)
        )
        
        # Mark chunks as golden or not
        for chunk in retrieved_chunks:
            metadata = chunk.get("metadata", {})
            doc_id = metadata.get("doc_id")
            chunk["is_golden"] = doc_id in golden_doc_ids if doc_id else False
        
        return comparison

