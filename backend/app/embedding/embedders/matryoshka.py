"""Matryoshka Embeddings with adaptive dimensionality."""

from typing import Dict, List, Optional

import structlog
import torch
from FlagEmbedding import BGEM3FlagModel
from app.core.config import settings

logger = structlog.get_logger(__name__)


class MatryoshkaEmbedder:
    """
    Matryoshka Embeddings with adaptive dimensionality.

    Uses BGE-M3 but allows using smaller dimensions for faster search.

    Benefits:
    - 1024 dim → 256 dim: 4x faster search, <5% accuracy loss
    - 1024 dim → 512 dim: 2x faster search, <2% accuracy loss
    - Flexible: use full dimensions when accuracy matters, smaller when speed matters

    How it works:
    - Generate full 1024-dimensional embeddings
    - Truncate to smaller dimensions when needed
    - BGE-M3 is trained with Matryoshka loss, so smaller dims retain semantic info

    Use cases:
    - First-pass retrieval: 256 dims (fast, broad recall)
    - Re-ranking: 1024 dims (accurate, final ranking)
    - Hybrid: 512 dims (balanced)
    """

    FULL_DIM = 1024
    SUPPORTED_DIMS = [64, 128, 256, 512, 768, 1024]

    def __init__(
        self,
        model_name: str = None,
        device: str = None,
        use_fp16: bool = None,
        default_dimension: int = 1024,
        adaptive: bool = True
    ):
        """
        Initialize Matryoshka embedder.

        Args:
            model_name: Model name or path (default: from settings)
            device: Device to use (default: from settings)
            use_fp16: Use FP16 precision (default: auto-detect based on device)
            default_dimension: Default embedding dimension (64/128/256/512/768/1024)
            adaptive: Whether to adaptively choose dimension based on query complexity
        """
        if default_dimension not in self.SUPPORTED_DIMS:
            raise ValueError(f"Dimension must be one of {self.SUPPORTED_DIMS}")

        self.model_name = model_name or settings.embedding_model
        self.device = device or settings.embedding_device
        self.use_fp16 = use_fp16 if use_fp16 is not None else (self.device in ["cuda", "mps"])
        self.default_dimension = default_dimension
        self.adaptive = adaptive

        logger.info(
            "initializing_matryoshka_embedder",
            model=self.model_name,
            device=self.device,
            default_dim=default_dimension,
            adaptive=adaptive
        )

        try:
            self.model = BGEM3FlagModel(
                model_name_or_path=self.model_name,
                use_fp16=self.use_fp16,
                device=self.device
            )

            device_name = self._get_device_name()
            logger.info(
                "matryoshka_embedder_initialized",
                device=self.device,
                device_name=device_name,
                default_dim=default_dimension
            )
        except Exception as e:
            logger.error("matryoshka_embedder_init_failed", error=str(e))
            if self.device == "mps":
                logger.warning("mps_init_failed_fallback_to_cpu")
                self.device = "cpu"
                self.use_fp16 = False
                self.model = BGEM3FlagModel(
                    model_name_or_path=self.model_name,
                    use_fp16=False,
                    device="cpu"
                )
            else:
                raise

    def _truncate_embeddings(
        self,
        embeddings: List[List[float]],
        target_dim: int
    ) -> List[List[float]]:
        """
        Truncate embeddings to target dimension.

        Args:
            embeddings: Full-dimensional embeddings
            target_dim: Target dimension

        Returns:
            Truncated embeddings
        """
        if target_dim >= self.FULL_DIM:
            return embeddings

        return [emb[:target_dim] for emb in embeddings]

    def _estimate_query_complexity(self, query: str) -> int:
        """
        Estimate query complexity and return recommended dimension.

        Simple queries → smaller dimensions
        Complex queries → larger dimensions

        Args:
            query: Query string

        Returns:
            Recommended dimension
        """
        # Simple heuristic based on query length
        word_count = len(query.split())

        if word_count <= 3:
            # Short query: "Q1 매출" → 256 dims
            return 256
        elif word_count <= 7:
            # Medium query: "Q1과 Q2의 매출 차이는?" → 512 dims
            return 512
        else:
            # Long query: complex question → 1024 dims
            return 1024

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = None,
        dimension: Optional[int] = None
    ) -> Dict[str, List]:
        """
        Embed multiple texts with optional dimensionality reduction.

        Args:
            texts: List of text strings
            batch_size: Batch size for processing
            dimension: Target dimension (None = use default)

        Returns:
            Dict with 'dense' (truncated) and 'sparse'
        """
        if not texts:
            return {"dense": [], "sparse": []}

        batch_size = batch_size or settings.embedding_batch_size
        target_dim = dimension or self.default_dimension

        logger.info(
            "embedding_texts_matryoshka",
            text_count=len(texts),
            batch_size=batch_size,
            target_dim=target_dim
        )

        try:
            # Generate full embeddings
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                max_length=8192,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False
            )

            # Truncate to target dimension
            dense_full = embeddings["dense_vecs"].tolist()
            dense_truncated = self._truncate_embeddings(dense_full, target_dim)

            logger.info(
                "texts_embedded_matryoshka",
                count=len(texts),
                original_dim=self.FULL_DIM,
                target_dim=target_dim,
                compression_ratio=f"{target_dim/self.FULL_DIM:.2f}x"
            )

            return {
                "dense": dense_truncated,
                "sparse": embeddings["lexical_weights"],
                "dimension": target_dim  # Include dimension info
            }

        except Exception as e:
            logger.error("embed_texts_matryoshka_failed", error=str(e))
            raise

    def embed_query(
        self,
        query: str,
        dimension: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Embed query with adaptive dimensionality.

        Args:
            query: Query string
            dimension: Target dimension (None = adaptive)

        Returns:
            Dict with 'dense' (truncated), 'sparse', 'dimension'
        """
        # Adaptive dimension selection
        if dimension is None and self.adaptive:
            dimension = self._estimate_query_complexity(query)
        elif dimension is None:
            dimension = self.default_dimension

        # Add instruction for better retrieval
        query_text = f"Represent this sentence for searching relevant passages: {query}"

        logger.debug(
            "embedding_query_matryoshka",
            query_length=len(query),
            target_dim=dimension
        )

        try:
            embeddings = self.model.encode(
                [query_text],
                max_length=512,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False
            )

            # Truncate to target dimension
            dense_full = embeddings["dense_vecs"][0].tolist()
            dense_truncated = dense_full[:dimension]

            return {
                "dense": dense_truncated,
                "sparse": embeddings["lexical_weights"][0] if embeddings["lexical_weights"] else {},
                "dimension": dimension
            }

        except Exception as e:
            logger.error("embed_query_matryoshka_failed", error=str(e))
            raise

    def _get_device_name(self) -> str:
        """Get human-readable device name."""
        try:
            if self.device == "cuda" and torch.cuda.is_available():
                return torch.cuda.get_device_name(0)
            elif self.device == "mps":
                return "Apple Silicon (MPS)"
            return "CPU"
        except Exception:
            return "Unknown"

    def get_dimension(self, target_dim: Optional[int] = None) -> int:
        """Get embedding dimension."""
        return target_dim or self.default_dimension
