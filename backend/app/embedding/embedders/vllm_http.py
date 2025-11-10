"""vLLM HTTP Embedder for external embedding models."""

from typing import Dict, List
import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)


class VLLMHTTPEmbedder:
    """
    vLLM HTTP Embedder for external embedding models (e.g., Qwen 8B).

    Features:
    - HTTP-based embedding via vLLM server
    - Configurable endpoint and model
    - Batch processing support
    - Compatible with OpenAI embeddings API format
    """

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str = "Qwen/Qwen2.5-Coder-Instruct-8B",
        embedding_dim: int = 4096,
        timeout: float = 120.0,
    ):
        """
        Initialize vLLM HTTP embedder.

        Args:
            base_url: vLLM server base URL (defaults to settings.vllm_embedding_url)
                     빈 문자열('')도 None으로 처리하여 환경변수 기본값 사용
            model_name: Model name/identifier
            embedding_dim: Embedding dimension
            timeout: HTTP request timeout in seconds
        """
        # Use config default if not provided or empty string
        if not base_url:  # None or empty string
            base_url = settings.vllm_embedding_url
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.timeout = timeout
        self.endpoint = f"{self.base_url}/v1/embeddings"

        logger.info(
            "initializing_vllm_http_embedder",
            base_url=self.base_url,
            model=self.model_name,
            dimension=self.embedding_dim,
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
                    logger.info("vllm_server_connected", models=response.json())
                except httpx.HTTPError:
                    # If models endpoint doesn't exist, try a simple embedding
                    logger.warning("models_endpoint_unavailable_trying_embedding_test")
                    test_embedding = self.embed_texts(["test"])
                    if test_embedding:
                        logger.info("vllm_server_connected_via_test_embedding")
        except Exception as e:
            logger.error("vllm_server_connection_failed", error=str(e))
            raise ConnectionError(
                f"Failed to connect to vLLM server at {self.base_url}: {e}"
            )

    def embed_texts(self, texts: List[str], batch_size: int = 16) -> Dict[str, List]:
        """
        Embed multiple texts via HTTP.

        Args:
            texts: List of text strings
            batch_size: Batch size for processing

        Returns:
            Dict with 'dense' embeddings: List[List[float]]
        """
        if not texts:
            return {"dense": [], "sparse": []}

        logger.info(
            "embedding_texts_via_vllm",
            text_count=len(texts),
            batch_size=batch_size,
        )

        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)

        logger.info("texts_embedded_via_vllm", count=len(all_embeddings))

        return {
            "dense": all_embeddings,
            "sparse": {},  # vLLM doesn't provide sparse embeddings (empty dict)
        }

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of texts via HTTP request with retry logic.

        Args:
            texts: Batch of texts to embed

        Returns:
            List of embedding vectors
        """
        import time

        max_retries = 5
        retry_delay = 3.0  # seconds

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    # OpenAI-compatible embeddings API format
                    payload = {
                        "model": self.model_name,
                        "input": texts,
                        "encoding_format": "float",
                    }

                    response = client.post(self.endpoint, json=payload)
                    response.raise_for_status()

                    result = response.json()
                    
                    # Log the actual response structure for debugging
                    logger.info(
                        "vllm_response_received",
                        response_keys=list(result.keys()) if isinstance(result, dict) else type(result).__name__,
                        response_sample=str(result)[:500]  # First 500 chars
                    )

                    # Extract embeddings from response
                    # Support multiple response formats
                    embeddings = None
                    
                    # Format 1: OpenAI format {"data": [{"index": 0, "embedding": [...]}, ...]}
                    if "data" in result and isinstance(result["data"], list):
                        data_items = result["data"]
                        
                        # Check if items have index and embedding
                        if data_items and isinstance(data_items[0], dict) and "embedding" in data_items[0]:
                            # Validate indices
                            expected_indices = set(range(len(texts)))
                            actual_indices = {item.get("index", -1) for item in data_items}

                            if expected_indices != actual_indices:
                                logger.error(
                                    "invalid_embedding_indices",
                                    expected=expected_indices,
                                    actual=actual_indices,
                                )
                                raise ValueError(
                                    f"Missing or invalid indices in response: "
                                    f"expected {len(texts)} items with indices {expected_indices}, "
                                    f"got {actual_indices}"
                                )

                            # Sort by index to ensure correct order
                            sorted_items = sorted(data_items, key=lambda x: x["index"])
                            embeddings = [item["embedding"] for item in sorted_items]
                        else:
                            # Data is directly a list of embeddings
                            embeddings = data_items
                    
                    # Format 2: Direct embeddings list {"embeddings": [[...], ...]}
                    elif "embeddings" in result and isinstance(result["embeddings"], list):
                        embeddings = result["embeddings"]
                    
                    # Format 3: Direct array response [[...], ...]
                    elif isinstance(result, list):
                        embeddings = result
                    
                    # If still no embeddings found, raise error
                    if embeddings is None:
                        logger.error(
                            "unsupported_response_format",
                            available_keys=list(result.keys()) if isinstance(result, dict) else None,
                            response_type=type(result).__name__
                        )
                        raise ValueError(
                            f"Unsupported response format. Available keys: "
                            f"{list(result.keys()) if isinstance(result, dict) else 'N/A'}"
                        )

                    # Add delay to avoid overwhelming the server
                    time.sleep(0.5)

                    return embeddings

            except httpx.HTTPError as e:
                status_code = (
                    getattr(e.response, "status_code", None)
                    if hasattr(e, "response")
                    else None
                )

                # Retry on 404, 502, 503, 504 errors
                if attempt < max_retries - 1 and status_code in [404, 502, 503, 504]:
                    logger.warning(
                        "vllm_embedding_request_failed_retrying",
                        error=str(e),
                        status=status_code,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(
                        "vllm_embedding_request_failed",
                        error=str(e),
                        status=status_code,
                    )
                    raise
            except Exception as e:
                logger.error("vllm_embedding_failed", error=str(e))
                raise

    def embed_query(self, query: str, enhanced: bool = False):
        """
        Embed a single query.

        Args:
            query: Query text
            enhanced: Whether to enhance query (not used for HTTP embedder)

        Returns:
            Dict with 'dense' embedding vector and empty 'sparse'
        """
        if enhanced:
            # Simple query enhancement
            query = f"Query: {query}"

        result = self.embed_texts([query])
        return {"dense": result["dense"][0], "sparse": {}}  # Empty dict, not list

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self.embedding_dim

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"VLLMHTTPEmbedder(model={self.model_name}, "
            f"dimension={self.embedding_dim}, "
            f"endpoint={self.endpoint})"
        )
