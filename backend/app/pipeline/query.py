"""Query Pipeline for RAG question answering."""

import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from app.embedding.embedders import create_embedder
from app.embedding.vector_stores import create_vector_store
from app.pipeline.generators import create_generator
from app.pipeline.retrievers import create_retriever
from app.config import settings
from app.models.query import Query, QueryResult, Source

logger = structlog.get_logger(__name__)


class QueryPipeline:
    """
    Query pipeline: Retrieve → Generate Answer.

    Flow:
    1. Retrieve relevant chunks from vector store
    2. Build context from retrieved chunks
    3. Generate answer using LLM

    Usage:
        pipeline = QueryPipeline()
        result = pipeline.query("What is the Q1 goal?", top_k=5)
        print(result.answer)
        print(result.sources)
    """

    def __init__(
        self,
        embedder_name: str = "bge-m3",
        vector_store_name: str = "qdrant",
        retriever_name: str = "base",
        generator_name: str = "claude"
    ):
        """
        Initialize query pipeline.

        Args:
            embedder_name: Embedder type ('bge-m3')
            vector_store_name: Vector store type ('qdrant')
            retriever_name: Retriever type ('base', 'hyde', 'reranker')
            generator_name: Generator type ('claude')
        """
        logger.info(
            "initializing_query_pipeline",
            embedder=embedder_name,
            vector_store=vector_store_name,
            retriever=retriever_name,
            generator=generator_name
        )

        self.embedder = create_embedder(embedder_name)
        self.vector_store = create_vector_store(vector_store_name)
        self.retriever = create_retriever(
            retriever_name,
            embedder=self.embedder,
            vector_store=self.vector_store
        )
        self.generator = create_generator(generator_name)

        logger.info("query_pipeline_initialized")

    def query(
        self,
        question: str,
        user_id: str = "system",
        top_k: Optional[int] = None,
        datasource_id: Optional[str] = None,
        datasource_ids: Optional[list] = None
    ) -> QueryResult:
        """
        Execute RAG query.

        Args:
            question: User question
            user_id: User ID for tracking
            top_k: Number of chunks to retrieve (default: from settings)
            datasource_id: Filter by datasource ID

        Returns:
            QueryResult with answer and sources
        """
        if not question.strip():
            raise ValueError("Question cannot be empty")

        top_k = top_k or settings.top_k

        logger.info(
            "executing_query",
            question_length=len(question),
            top_k=top_k,
            datasource_id=datasource_id
        )

        start_time = datetime.utcnow()

        try:
            # 1. Retrieve relevant chunks (backup style: simple retrieval)
            retrieval_start = datetime.utcnow()
            if datasource_ids and len(datasource_ids) > 0:
                search_results = self.retriever.retrieve(
                    query=question,
                    top_k=top_k or settings.top_k,
                    datasource_ids=datasource_ids
                )
            else:
                search_results = self.retriever.retrieve(
                    query=question,
                    top_k=top_k or settings.top_k,
                    datasource_id=datasource_id
                )
            retrieval_duration = (datetime.utcnow() - retrieval_start).total_seconds()

            if not search_results:
                logger.warning("no_results_found", question=question[:100])
                query_obj = Query(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    question=question,
                    answer="I couldn't find any relevant information to answer your question.",
                    sources=[],
                    top_k=top_k or settings.top_k,
                    datasource_id=datasource_id or (datasource_ids[0] if datasource_ids else None),
                    retrieval_latency_ms=int(retrieval_duration * 1000),
                    created_at=datetime.utcnow()
                )
                return QueryResult(
                    query=query_obj,
                    answer=query_obj.answer,
                    sources=[]
                )

            # 2. Convert to sources
            sources = [result.to_source() for result in search_results]

            # 3. Generate answer (generator will build context from sources and return grouped sources)
            generation_start = datetime.utcnow()
            answer, grouped_sources = self.generator.generate(
                question=question,
                sources=sources
            )
            generation_duration = (datetime.utcnow() - generation_start).total_seconds()

            # 5. Create Query object with grouped sources (document-level)
            total_duration = (datetime.utcnow() - start_time).total_seconds()

            query_obj = Query(
                id=str(uuid.uuid4()),
                user_id=user_id,
                question=question,
                answer=answer,
                sources=grouped_sources,  # Use grouped sources instead of raw chunk sources
                model=settings.llm_model,
                latency_ms=int(total_duration * 1000),
                retrieval_latency_ms=int(retrieval_duration * 1000),
                llm_latency_ms=int(generation_duration * 1000),
                top_k=top_k or settings.top_k,
                datasource_id=datasource_id,
                created_at=datetime.utcnow()
            )

            logger.info(
                "query_completed",
                retrieval_ms=int(retrieval_duration * 1000),
                generation_ms=int(generation_duration * 1000),
                total_ms=int(total_duration * 1000),
                chunk_count=len(sources),
                grouped_source_count=len(grouped_sources)
            )

            return QueryResult(
                query=query_obj,
                answer=answer,
                sources=grouped_sources  # Return grouped sources (document-level)
            )

        except Exception as e:
            logger.error("query_failed", error=str(e))
            raise

    def query_stream(
        self,
        question: str,
        user_id: str = "system",
        top_k: Optional[int] = None,
        datasource_id: Optional[str] = None,
        datasource_ids: Optional[list] = None
    ):
        """
        Execute RAG query with streaming.

        Args:
            question: User question
            user_id: User ID for tracking
            top_k: Number of chunks to retrieve (default: from settings)
            datasource_id: Filter by datasource ID
            datasource_ids: Filter by multiple datasource IDs

        Yields:
            Dict with 'type' and 'data':
            - {"type": "sources", "data": [grouped_sources]}
            - {"type": "chunk", "data": "text chunk"}
            - {"type": "complete", "data": QueryResult}
        """
        if not question.strip():
            raise ValueError("Question cannot be empty")

        top_k = top_k or settings.top_k

        logger.info(
            "executing_query_stream",
            question_length=len(question),
            top_k=top_k,
            datasource_id=datasource_id
        )

        start_time = datetime.utcnow()

        try:
            # 1. Retrieve relevant chunks
            retrieval_start = datetime.utcnow()
            if datasource_ids and len(datasource_ids) > 0:
                search_results = self.retriever.retrieve(
                    query=question,
                    top_k=top_k or settings.top_k,
                    datasource_ids=datasource_ids
                )
            else:
                search_results = self.retriever.retrieve(
                    query=question,
                    top_k=top_k or settings.top_k,
                    datasource_id=datasource_id
                )
            retrieval_duration = (datetime.utcnow() - retrieval_start).total_seconds()

            if not search_results:
                logger.warning("no_results_found", question=question[:100])
                query_obj = Query(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    question=question,
                    answer="I couldn't find any relevant information to answer your question.",
                    sources=[],
                    top_k=top_k or settings.top_k,
                    datasource_id=datasource_id or (datasource_ids[0] if datasource_ids else None),
                    retrieval_latency_ms=int(retrieval_duration * 1000),
                    created_at=datetime.utcnow()
                )
                yield {
                    "type": "sources",
                    "data": []
                }
                yield {
                    "type": "chunk",
                    "data": query_obj.answer
                }
                yield {
                    "type": "complete",
                    "data": QueryResult(query=query_obj, answer=query_obj.answer, sources=[])
                }
                return

            # 2. Convert to sources
            sources = [result.to_source() for result in search_results]

            # Build context to get grouped sources
            from app.pipeline.generators.claude import ClaudeGenerator
            temp_generator = ClaudeGenerator()
            _, grouped_sources = temp_generator._build_context_from_sources(sources)

            # 3. Yield sources first
            yield {
                "type": "sources",
                "data": grouped_sources
            }

            # 4. Stream answer generation
            generation_start = datetime.utcnow()
            answer_parts = []

            for chunk in self.generator.generate_stream(
                question=question,
                sources=sources
            ):
                answer_parts.append(chunk)
                yield {
                    "type": "chunk",
                    "data": chunk
                }

            generation_duration = (datetime.utcnow() - generation_start).total_seconds()
            full_answer = "".join(answer_parts)

            # 5. Create Query object
            total_duration = (datetime.utcnow() - start_time).total_seconds()

            query_obj = Query(
                id=str(uuid.uuid4()),
                user_id=user_id,
                question=question,
                answer=full_answer,
                sources=grouped_sources,
                model=settings.llm_model,
                latency_ms=int(total_duration * 1000),
                retrieval_latency_ms=int(retrieval_duration * 1000),
                llm_latency_ms=int(generation_duration * 1000),
                top_k=top_k or settings.top_k,
                datasource_id=datasource_id,
                created_at=datetime.utcnow()
            )

            logger.info(
                "query_stream_completed",
                retrieval_ms=int(retrieval_duration * 1000),
                generation_ms=int(generation_duration * 1000),
                total_ms=int(total_duration * 1000),
                chunk_count=len(sources),
                grouped_source_count=len(grouped_sources)
            )

            yield {
                "type": "complete",
                "data": QueryResult(query=query_obj, answer=full_answer, sources=grouped_sources)
            }

        except Exception as e:
            logger.error("query_stream_failed", error=str(e))
            raise

