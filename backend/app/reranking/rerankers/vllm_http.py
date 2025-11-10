"""vLLM HTTP Reranker for external reranking models."""

from __future__ import annotations

from typing import List
import httpx
import structlog

from .base_reranker import BaseReranker, RetrievedDocument
from app.core.config import settings

logger = structlog.get_logger(__name__)


class VLLMHTTPReranker(BaseReranker):
    """
    vLLM HTTP Reranker for external reranking models.
    
    Features:
    - HTTP-based reranking via vLLM server
    - Configurable endpoint and model
    - Batch processing support
    - Compatible with reranking API format
    
    Use cases:
    - Large reranking models that don't fit in memory
    - Distributed reranking across multiple servers
    - Using specialized reranking models (e.g., Qwen, LLaMA-based)
    """

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        """
        Initialize vLLM HTTP reranker.

        Args:
            base_url: vLLM server base URL (defaults to settings.vllm_reranking_url)
                     빈 문자열('')도 None으로 처리하여 환경변수 기본값 사용
            model_name: Model name/identifier
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retries on failure
        """
        # Use config default if not provided or empty string
        if not base_url:  # None or empty string
            base_url = settings.vllm_reranking_url
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.endpoint = f"{self.base_url}/v1/rerank"

        logger.info(
            "initializing_vllm_http_reranker",
            base_url=self.base_url,
            model=self.model_name,
            endpoint=self.endpoint,
        )

        # Test connection
        self._test_connection()

    def _test_connection(self):
        """Test connection to vLLM server."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                # Try to get models list or health check
                try:
                    response = client.get(f"{self.base_url}/v1/models")
                    response.raise_for_status()
                    logger.info("vllm_reranker_server_connected", models=response.json())
                except httpx.HTTPError:
                    logger.warning("models_endpoint_unavailable_for_reranker")
        except Exception as e:
            logger.warning(
                "vllm_reranker_server_connection_test_failed",
                error=str(e),
                note="Will retry on actual rerank request"
            )

    def rerank(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: int | None = None,
    ) -> List[RetrievedDocument]:
        """
        Rerank documents using vLLM HTTP endpoint.

        Args:
            query: Query string
            documents: List of documents to rerank
            top_k: Number of top documents to return (None = all)

        Returns:
            Reranked documents with updated scores
        """
        if not documents:
            return documents

        logger.info(
            "reranking_via_vllm",
            query_length=len(query),
            document_count=len(documents),
            top_k=top_k,
        )

        # Prepare request
        doc_texts = [doc.content for doc in documents]
        
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    # API format (similar to Cohere/Jina rerank API)
                    payload = {
                        "model": self.model_name,
                        "query": query,
                        "documents": doc_texts,
                        "top_n": top_k if top_k is not None else len(documents),
                        "return_documents": False,  # We already have the documents
                    }

                    response = client.post(self.endpoint, json=payload)
                    response.raise_for_status()

                    result = response.json()

                    # Parse response
                    # Expected format: {"results": [{"index": 0, "relevance_score": 0.95}, ...]}
                    if "results" in result:
                        results = result["results"]
                    elif "data" in result:
                        # Alternative format
                        results = result["data"]
                    else:
                        raise ValueError(f"Unexpected response format: {result.keys()}")

                    # Create reranked documents
                    reranked = []
                    for item in results:
                        idx = item.get("index")
                        score = item.get("relevance_score") or item.get("score", 0.0)
                        
                        if idx is None or idx >= len(documents):
                            logger.warning("invalid_rerank_index", index=idx, doc_count=len(documents))
                            continue
                        
                        original_doc = documents[idx]
                        reranked.append(
                            RetrievedDocument(
                                id=original_doc.id,
                                content=original_doc.content,
                                score=float(score),
                                metadata=original_doc.metadata,
                            )
                        )

                    logger.info(
                        "documents_reranked_via_vllm",
                        original_count=len(documents),
                        reranked_count=len(reranked),
                    )

                    return reranked

            except httpx.HTTPError as e:
                status_code = (
                    getattr(e.response, "status_code", None)
                    if hasattr(e, "response")
                    else None
                )

                if attempt < self.max_retries - 1 and status_code in [502, 503, 504]:
                    logger.warning(
                        "vllm_rerank_request_failed_retrying",
                        error=str(e),
                        status=status_code,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                    )
                    import time
                    time.sleep(2.0 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(
                        "vllm_rerank_request_failed",
                        error=str(e),
                        status=status_code,
                    )
                    raise

            except Exception as e:
                logger.error("vllm_rerank_failed", error=str(e))
                raise

        # If all retries failed
        logger.error("vllm_rerank_all_retries_failed")
        return documents  # Return original order as fallback

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"VLLMHTTPReranker(model={self.model_name}, "
            f"endpoint={self.endpoint})"
        )

