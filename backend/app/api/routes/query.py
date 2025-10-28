"""Query API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import structlog

from app.core.dependencies import get_db, get_qdrant_service
from app.services.query_service import QueryService
from app.services.qdrant_service import QdrantService
from app.schemas.query import (
    SearchRequest,
    SearchResponse,
    AnswerRequest,
    AnswerResponse,
    RetrievedChunk,
    QueryComparison,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/query", tags=["query"])


def get_query_service(
    db: Session = Depends(get_db),
    qdrant_service: QdrantService = Depends(get_qdrant_service)
) -> QueryService:
    """Dependency to get QueryService instance."""
    return QueryService(db, qdrant_service)


@router.post("/search", response_model=SearchResponse)
def search(
    search_request: SearchRequest,
    query_service: QueryService = Depends(get_query_service),
):
    """
    Perform vector search with optional reranking using a pipeline.
    
    Steps:
    1. Load pipeline (RAG + DataSources or Dataset)
    2. Embed query
    3. Search Qdrant
    4. Rerank results (if configured in RAG)
    5. For test pipelines: Compare with golden chunks
    6. Return top_k results
    
    **Test Pipeline Queries:**
    When querying a test pipeline, the response includes a `comparison` field
    showing how retrieved chunks compare to golden (ground truth) chunks:
    - Precision@K: Ratio of correct chunks in top-k results
    - Recall@K: Ratio of golden chunks that were retrieved
    - Hit Rate: Whether any golden chunk was found
    """
    try:
        result = query_service.search(
            pipeline_id=search_request.pipeline_id,
            query=search_request.query,
            top_k=search_request.top_k,
        )
        
        # Build comparison if available (test pipelines only)
        comparison = None
        if result.comparison:
            comparison = QueryComparison(**result.comparison)
        
        return SearchResponse(
            query=result.query,
            pipeline_id=search_request.pipeline_id,
            pipeline_type=result.pipeline_type,
            results=[
                RetrievedChunk(
                    chunk_id=str(chunk["id"]),
                    datasource_id=chunk.get("datasource_id", 0),
                    content=chunk["content"],
                    score=chunk["score"],
                    metadata=chunk.get("metadata"),
                    is_golden=chunk.get("is_golden"),
                )
                for chunk in result.chunks
            ],
            total=len(result.chunks),
            retrieval_time=result.total_time,
            comparison=comparison,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("search_failed", error=str(e), query=search_request.query[:100])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/answer", response_model=AnswerResponse)
def answer(
    answer_request: AnswerRequest,
    query_service: QueryService = Depends(get_query_service),
):
    """
    Perform search and generate answer using LLM with a pipeline.
    
    Steps:
    1. Load pipeline (RAG + DataSources)
    2. Search for relevant chunks
    3. Format context
    4. Generate answer with LLM (Claude or vLLM)
    5. Return answer with sources
    
    The llm_config specifies which model to use and its parameters:
    - type: 'claude' or 'vllm'
    - model_name: Model identifier
    - api_key: For Claude authentication
    - endpoint: For vLLM HTTP server
    - parameters: temperature, max_tokens, top_p
    """
    try:
        # Convert Pydantic model to dict for query_service
        llm_config_dict = answer_request.llm_config.dict()
        
        result = query_service.answer(
            pipeline_id=answer_request.pipeline_id,
            query=answer_request.query,
            top_k=answer_request.top_k,
            system_prompt=answer_request.system_prompt,
            llm_config=llm_config_dict,
        )
        
        return AnswerResponse(
            query=result["query"],
            answer=result["answer"],
            sources=[
                RetrievedChunk(
                    chunk_id=str(chunk["id"]),
                    datasource_id=chunk.get("datasource_id", 0),
                    content=chunk["content"],
                    score=chunk["score"],
                    metadata=chunk.get("metadata"),
                )
                for chunk in result["sources"]
            ],
            tokens_used=result.get("tokens_used", 0),
            generation_time=result["total_time"],
            retrieval_time=result["search_time"],
            llm_time=result.get("llm_time", 0.0),
        )
        
    except ValueError as e:
        logger.warning("answer_validation_error", error=str(e), query=answer_request.query[:100])
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotImplementedError as e:
        logger.warning("answer_not_implemented", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e)
        )
    except Exception as e:
        logger.error("answer_failed", error=str(e), query=answer_request.query[:100])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer generation failed: {str(e)}"
        )

