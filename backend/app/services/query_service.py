"""Query Service for RAG search and answer generation."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import structlog

from app.models.rag import RAGConfiguration
from app.services.rag_factory import RAGFactory
from app.services.qdrant_service import QdrantService

logger = structlog.get_logger(__name__)


class QueryResult:
    """Result of a query search."""
    
    def __init__(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        search_time: float,
        rerank_time: Optional[float] = None,
    ):
        """
        Initialize QueryResult.
        
        Args:
            query: Original query text
            chunks: List of retrieved chunks with metadata
            search_time: Time taken for vector search (seconds)
            rerank_time: Time taken for reranking (seconds)
        """
        self.query = query
        self.chunks = chunks
        self.search_time = search_time
        self.rerank_time = rerank_time
        self.total_time = search_time + (rerank_time or 0)


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
        rag_id: int,
        query: str,
        datasource_ids: Optional[List[int]] = None,
        top_k: int = 5,
    ) -> QueryResult:
        """
        Search for relevant chunks using RAG configuration.
        
        Steps:
        1. Load RAG configuration and create embedder, reranker
        2. Embed query
        3. Search Qdrant (retrieve top_k * 4 for reranking)
        4. Rerank results (top_k * 4 → top_k)
        
        Args:
            rag_id: RAG configuration ID
            query: Query text
            datasource_ids: Optional list of data source IDs to filter
            top_k: Number of final results to return
            
        Returns:
            QueryResult with retrieved chunks and timing info
            
        Raises:
            ValueError: If RAG not found
        """
        import time
        
        # Load RAG configuration
        rag = self.db.query(RAGConfiguration).filter(RAGConfiguration.id == rag_id).first()
        if not rag:
            raise ValueError(f"RAG configuration {rag_id} not found")
        
        logger.info(
            "query_started",
            rag_id=rag_id,
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
        
        # Embed query
        query_embedding = embedder.embed([query])[0]
        
        # Search Qdrant (retrieve more for reranking)
        search_limit = top_k * 4 if rag.reranking_module != "none" else top_k
        
        search_start = time.time()
        search_results = self.qdrant_service.search(
            collection_name=rag.collection_name,
            query_vector=query_embedding,
            limit=search_limit,
            datasource_ids=datasource_ids,
        )
        search_time = time.time() - search_start
        
        logger.info(
            "vector_search_completed",
            rag_id=rag_id,
            num_results=len(search_results),
            search_time=search_time
        )
        
        # Prepare chunks for reranking
        chunks = []
        for result in search_results:
            chunks.append({
                "id": result.id,
                "content": result.payload.get("content", ""),
                "score": result.score,
                "datasource_id": result.payload.get("datasource_id"),
                "chunk_index": result.payload.get("chunk_index"),
                "metadata": result.payload.get("metadata", {}),
            })
        
        # Rerank if needed
        rerank_time = None
        if rag.reranking_module != "none" and chunks:
            rerank_start = time.time()
            
            # Prepare for reranking
            chunk_texts = [c["content"] for c in chunks]
            reranked_indices = reranker.rerank(query, chunk_texts, top_k=top_k)
            
            # Reorder chunks
            reranked_chunks = [chunks[i] for i in reranked_indices]
            chunks = reranked_chunks
            
            rerank_time = time.time() - rerank_start
            
            logger.info(
                "reranking_completed",
                rag_id=rag_id,
                num_results=len(chunks),
                rerank_time=rerank_time
            )
        else:
            # No reranking, just take top_k
            chunks = chunks[:top_k]
        
        result = QueryResult(
            query=query,
            chunks=chunks,
            search_time=search_time,
            rerank_time=rerank_time,
        )
        
        logger.info(
            "query_completed",
            rag_id=rag_id,
            total_time=result.total_time,
            num_chunks=len(chunks)
        )
        
        return result

    def answer(
        self,
        rag_id: int,
        query: str,
        datasource_ids: Optional[List[int]] = None,
        top_k: int = 5,
        llm_endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate an answer using retrieved chunks and LLM.
        
        Steps:
        1. Search for relevant chunks
        2. Format context from chunks
        3. Call LLM with context and query
        4. Return answer with sources
        
        Args:
            rag_id: RAG configuration ID
            query: Query text
            datasource_ids: Optional list of data source IDs to filter
            top_k: Number of chunks to retrieve
            llm_endpoint: Optional LLM endpoint URL
            
        Returns:
            Dict with answer, sources, and timing info
            
        Raises:
            ValueError: If RAG not found
            NotImplementedError: If LLM integration not available
        """
        # First, search for relevant chunks
        search_result = self.search(
            rag_id=rag_id,
            query=query,
            datasource_ids=datasource_ids,
            top_k=top_k,
        )
        
        # Format context
        context_parts = []
        for i, chunk in enumerate(search_result.chunks, 1):
            context_parts.append(f"[{i}] {chunk['content']}")
        
        context = "\n\n".join(context_parts)
        
        # TODO: Integrate with LLM
        # For now, return a placeholder
        if llm_endpoint:
            # Future: Call LLM endpoint with context and query
            raise NotImplementedError("LLM integration not yet implemented")
        
        return {
            "query": query,
            "answer": "LLM integration not yet implemented. Please use search() for now.",
            "sources": search_result.chunks,
            "context": context,
            "search_time": search_result.search_time,
            "rerank_time": search_result.rerank_time,
            "total_time": search_result.total_time,
        }

    def batch_search(
        self,
        rag_id: int,
        queries: List[str],
        datasource_ids: Optional[List[int]] = None,
        top_k: int = 5,
    ) -> List[QueryResult]:
        """
        Batch search for multiple queries.
        
        Args:
            rag_id: RAG configuration ID
            queries: List of query texts
            datasource_ids: Optional list of data source IDs to filter
            top_k: Number of results per query
            
        Returns:
            List of QueryResult objects
        """
        results = []
        for query in queries:
            try:
                result = self.search(
                    rag_id=rag_id,
                    query=query,
                    datasource_ids=datasource_ids,
                    top_k=top_k,
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "batch_search_query_failed",
                    rag_id=rag_id,
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

