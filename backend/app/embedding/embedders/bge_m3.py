"""BGE-M3 Embedder for hybrid search."""

from typing import Dict, List

import structlog
import torch
from FlagEmbedding import BGEM3FlagModel
from app.core.config import settings

logger = structlog.get_logger(__name__)


class BGEM3Embedder:
    """
    BGE-M3 Embedder with Hybrid Search (Dense + Sparse vectors).

    Features:
    - 1024-dimensional dense vectors
    - Sparse vectors for keyword matching
    - GPU acceleration
    - Batch processing
    """

    EMBEDDING_DIM = 1024

    def __init__(
        self,
        model_name: str = None,
        device: str = None,
        use_fp16: bool = None,
        batch_size: int = None
    ):
        """Initialize BGE-M3 model.
        
        Args:
            model_name: Model name or path (default: from settings)
            device: Device to use (default: from settings)
            use_fp16: Use FP16 precision (default: auto-detect based on device)
            batch_size: Batch size for embedding (default: auto-detect)
        """
        self.model_name = model_name or settings.embedding_model
        self.device = device or settings.embedding_device
        self.use_fp16 = use_fp16 if use_fp16 is not None else (self.device in ["cuda", "mps"])

        # Auto-detect optimal batch size based on device
        self.optimal_batch_size = batch_size or self._get_optimal_batch_size()

        logger.info(
            "initializing_bge_m3_embedder",
            model=self.model_name,
            device=self.device,
            fp16=self.use_fp16,
            optimal_batch_size=self.optimal_batch_size
        )

        try:
            self.model = BGEM3FlagModel(
                model_name_or_path=self.model_name,
                use_fp16=self.use_fp16,
                device=self.device
            )
            
            # Log device info after initialization
            device_name = self._get_device_name()
            device_memory = self._get_device_memory()
            logger.info(
                "bge_m3_embedder_initialized",
                device=self.device,
                device_name=device_name,
                available_memory=device_memory
            )
        except Exception as e:
            logger.error("bge_m3_init_failed", error=str(e))
            # Fallback to CPU if MPS fails
            if self.device == "mps":
                logger.warning("mps_init_failed_fallback_to_cpu")
                self.device = "cpu"
                self.use_fp16 = False
                self.model = BGEM3FlagModel(
                    model_name_or_path=self.model_name,
                    use_fp16=False,
                    device="cpu"
                )
                logger.info("bge_m3_embedder_initialized_on_cpu")
            else:
                raise

    def embed_texts(self, texts: List[str], batch_size: int = None) -> Dict[str, List]:
        """
        Embed multiple texts with Hybrid Search (Dense + Sparse).

        Args:
            texts: List of text strings
            batch_size: Batch size for processing (default: auto-detected optimal size)

        Returns:
            Dict with 'dense' (List[List[float]]) and 'sparse' (List[Dict])
        """
        if not texts:
            return {"dense": [], "sparse": []}

        # Use optimal batch size if not specified
        batch_size = batch_size or self.optimal_batch_size
        logger.info("embedding_texts", text_count=len(texts), batch_size=batch_size)

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                max_length=8192,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False
            )

            # Convert lexical_weights to Qdrant sparse vector format
            sparse_vectors = []
            for lexical_weight in embeddings["lexical_weights"]:
                if lexical_weight:  # Check if not empty
                    indices = list(lexical_weight.keys())
                    values = list(lexical_weight.values())
                    sparse_vectors.append({
                        "indices": indices,
                        "values": values
                    })
                else:
                    sparse_vectors.append({"indices": [], "values": []})

            return {
                "dense": embeddings["dense_vecs"].tolist(),
                "sparse": sparse_vectors
            }
        except Exception as e:
            logger.error("embed_texts_failed", text_count=len(texts), error=str(e))
            raise

    def embed_chunks(self, chunks: List, batch_size: int = 32) -> Dict[str, List]:
        """
        Generate Hybrid embeddings for multiple BaseChunks.

        Args:
            chunks: List of BaseChunk objects
            batch_size: Batch size for processing

        Returns:
            Dict with 'dense' and 'sparse' keys
        """
        if not chunks:
            logger.warning("embed_chunks_called_with_empty_list")
            return {"dense": [], "sparse": []}

        logger.info("embedding_chunks", chunk_count=len(chunks), batch_size=batch_size)

        # Extract texts from chunks
        texts = [chunk.content for chunk in chunks]

        # Generate Hybrid embeddings
        embeddings = self.embed_texts(texts, batch_size=batch_size)

        logger.info("chunks_embedded", chunk_count=len(chunks), embedding_count=len(embeddings["dense"]))

        return embeddings

    def embed_query(self, query: str, enhance: bool = True) -> Dict[str, any]:
        """
        Embed a search query with instruction prefix.

        Args:
            query: Query string
            enhance: Whether to enhance query with instruction (default: True)

        Returns:
            Dict with 'dense' (List[float]) and 'sparse' (Dict)
        """
        # Add instruction for better retrieval
        if enhance:
            # Enhanced instruction for better semantic matching
            query_text = f"Search query: {query}\nFind documents that answer this question or contain relevant information."
        else:
            query_text = query

        logger.debug("embedding_query", query_length=len(query), enhanced=enhance)

        try:
            embeddings = self.model.encode(
                [query_text],
                max_length=512,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False
            )

            # Convert lexical_weights to Qdrant sparse vector format
            sparse_vector = {}
            if embeddings["lexical_weights"] and embeddings["lexical_weights"][0]:
                lexical_weight = embeddings["lexical_weights"][0]
                sparse_vector = {
                    "indices": list(lexical_weight.keys()),
                    "values": list(lexical_weight.values())
                }

            return {
                "dense": embeddings["dense_vecs"][0].tolist(),
                "sparse": sparse_vector
            }
        except Exception as e:
            logger.error("embed_query_failed", query=query[:100], error=str(e))
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

    def _get_device_memory(self) -> str:
        """Get available device memory."""
        try:
            if self.device == "cuda" and torch.cuda.is_available():
                total = torch.cuda.get_device_properties(0).total_memory / 1e9
                return f"{total:.1f}GB"
            elif self.device == "mps":
                return "Shared System Memory"
            return "System RAM"
        except Exception:
            return "Unknown"

    def _get_optimal_batch_size(self) -> int:
        """
        Auto-detect optimal batch size based on device.

        Returns:
            Optimal batch size for the current device
        """
        try:
            if self.device == "cuda" and torch.cuda.is_available():
                # CUDA: scale based on GPU memory
                total_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                if total_memory_gb >= 40:  # A100, H100
                    return 256
                elif total_memory_gb >= 24:  # RTX 3090, 4090
                    return 128
                elif total_memory_gb >= 12:  # RTX 3060, 4060
                    return 64
                else:
                    return 32
            elif self.device == "mps":
                # Apple Silicon: moderate batch size
                return 64
            else:
                # CPU: smaller batch size to avoid memory issues
                return 16
        except Exception:
            # Fallback to settings default
            return settings.embedding_batch_size

    def get_dimension(self) -> int:
        """Get embedding dimension (1024)."""
        return self.EMBEDDING_DIM

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension (alias for compatibility)."""
        return self.EMBEDDING_DIM

