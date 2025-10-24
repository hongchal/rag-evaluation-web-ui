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
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/query", tags=["query"])


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
    Perform vector search with optional reranking.
    
    Steps:
    1. Embed query
    2. Search Qdrant
    3. Rerank results (if configured)
    4. Return top_k results
    """
    try:
        result = query_service.search(
            rag_id=search_request.rag_id,
            query=search_request.query,
            datasource_ids=search_request.datasource_ids,
            top_k=search_request.top_k,
        )
        
        return SearchResponse(
            query=result.query,
            chunks=[
                {
                    "id": chunk["id"],
                    "content": chunk["content"],
                    "score": chunk["score"],
                    "datasource_id": chunk["datasource_id"],
                    "chunk_index": chunk["chunk_index"],
                    "metadata": chunk["metadata"],
                }
                for chunk in result.chunks
            ],
            search_time=result.search_time,
            rerank_time=result.rerank_time,
            total_time=result.total_time,
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
    Perform search and generate answer using LLM.
    
    Steps:
    1. Search for relevant chunks
    2. Format context
    3. Generate answer with LLM
    4. Return answer with sources
    """
    try:
        result = query_service.answer(
            rag_id=answer_request.rag_id,
            query=answer_request.query,
            datasource_ids=answer_request.datasource_ids,
            top_k=answer_request.top_k,
            llm_endpoint=answer_request.llm_endpoint,
        )
        
        return AnswerResponse(
            query=result["query"],
            answer=result["answer"],
            sources=[
                {
                    "id": chunk["id"],
                    "content": chunk["content"],
                    "score": chunk["score"],
                    "datasource_id": chunk["datasource_id"],
                    "chunk_index": chunk["chunk_index"],
                    "metadata": chunk["metadata"],
                }
                for chunk in result["sources"]
            ],
            search_time=result["search_time"],
            rerank_time=result["rerank_time"],
            total_time=result["total_time"],
        )
        
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("answer_failed", error=str(e), query=answer_request.query[:100])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer generation failed: {str(e)}"
        )

