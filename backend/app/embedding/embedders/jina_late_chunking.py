"""Jina v3 Embedder with Late Chunking support.

This embedder implements the Late Chunking technique where:
1. Entire document is embedded in a single forward pass
2. Token-level embeddings are extracted
3. Each chunk's embedding is computed by pooling its token embeddings

This approach is ~10x faster than embedding each chunk separately.

References:
- Jina AI Late Chunking: https://jina.ai/news/late-chunking-in-long-context-embedding-models/
- Model: jinaai/jina-embeddings-v3
"""

from typing import Dict, List, Optional, Tuple
import structlog
import torch
from transformers import AutoModel, AutoTokenizer
import numpy as np

from app.core.config import settings

logger = structlog.get_logger(__name__)


class JinaLocalLateChunkingEmbedder:
    """
    Jina v3 Embedder with Late Chunking optimization.
    
    Features:
    - 1024-dimensional dense vectors
    - Up to 8192 token context window
    - Late Chunking: 10x faster than traditional chunking
    - GPU/MPS/CPU support
    """
    
    EMBEDDING_DIM = 1024
    MAX_LENGTH = 8192
    
    def __init__(
        self,
        model_name: str = "jinaai/jina-embeddings-v3",
        device: str = None,
        use_fp16: bool = None,
        batch_size: int = None,
        trust_remote_code: bool = True
    ):
        """
        Initialize Jina v3 embedder.
        
        Args:
            model_name: Model name or path (default: jinaai/jina-embeddings-v3)
            device: Device to use (default: auto-detect)
            use_fp16: Use FP16 precision (default: auto-detect)
            batch_size: Batch size for embedding (default: auto-detect)
            trust_remote_code: Trust remote code for model loading
        """
        self.model_name = model_name
        self.device = device or self._auto_detect_device()
        self.use_fp16 = use_fp16 if use_fp16 is not None else (self.device in ["cuda", "mps"])
        self.trust_remote_code = trust_remote_code
        
        # Auto-detect optimal batch size
        self.optimal_batch_size = batch_size or self._get_optimal_batch_size()
        
        logger.info(
            "initializing_jina_late_chunking_embedder",
            model=self.model_name,
            device=self.device,
            fp16=self.use_fp16,
            optimal_batch_size=self.optimal_batch_size
        )
        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=self.trust_remote_code
            )
            
            # Load model
            self.model = AutoModel.from_pretrained(
                self.model_name,
                trust_remote_code=self.trust_remote_code,
                torch_dtype=torch.float16 if self.use_fp16 else torch.float32
            )
            
            # Move to device
            self.model = self.model.to(self.device)
            self.model.eval()
            
            logger.info(
                "jina_late_chunking_embedder_initialized",
                device=self.device,
                device_name=self._get_device_name(),
                available_memory=self._get_device_memory()
            )
            
        except Exception as e:
            logger.error("jina_embedder_init_failed", error=str(e))
            # Fallback to CPU if GPU initialization fails
            if self.device in ["cuda", "mps"]:
                logger.warning(f"{self.device}_init_failed_fallback_to_cpu")
                self.device = "cpu"
                self.use_fp16 = False
                
                self.model = AutoModel.from_pretrained(
                    self.model_name,
                    trust_remote_code=self.trust_remote_code,
                    torch_dtype=torch.float32
                )
                self.model = self.model.to("cpu")
                self.model.eval()
                
                logger.info("jina_embedder_initialized_on_cpu")
            else:
                raise
    
    def embed_texts(self, texts: List[str], batch_size: int = None) -> Dict[str, List]:
        """
        Embed multiple texts (traditional approach).
        
        Args:
            texts: List of text strings
            batch_size: Batch size for processing
            
        Returns:
            Dict with 'dense' embeddings and empty 'sparse' (for compatibility)
        """
        if not texts:
            return {"dense": [], "sparse": []}
        
        batch_size = batch_size or self.optimal_batch_size
        logger.info("embedding_texts", text_count=len(texts), batch_size=batch_size)
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._encode_batch(batch)
            all_embeddings.extend(batch_embeddings)
        
        logger.info("texts_embedded", count=len(all_embeddings))
        
        return {
            "dense": all_embeddings,
            "sparse": []  # Jina v3 doesn't provide sparse vectors
        }
    
    def embed_document_with_late_chunking(
        self,
        document_text: str,
        chunks: List[str]
    ) -> List[List[float]]:
        """
        Late Chunking: Embed entire document once, then extract chunk embeddings.
        
        This is ~10x faster than embedding each chunk separately.
        
        Args:
            document_text: Full document text
            chunks: List of chunk texts (must be substrings of document_text)
            
        Returns:
            List of embeddings for each chunk
        """
        if not chunks:
            return []
        
        logger.info(
            "late_chunking_embedding",
            document_length=len(document_text),
            chunk_count=len(chunks)
        )
        
        # Tokenize entire document
        inputs = self.tokenizer(
            document_text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.MAX_LENGTH,
            return_offsets_mapping=True  # To map tokens back to text positions
        )
        
        # Move to device
        input_ids = inputs["input_ids"].to(self.device)
        attention_mask = inputs["attention_mask"].to(self.device)
        offset_mapping = inputs["offset_mapping"][0].cpu().numpy()
        
        # Get token-level embeddings (single forward pass)
        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True
            )
            # Use last hidden state
            token_embeddings = outputs.last_hidden_state[0]  # [seq_len, hidden_dim]
        
        # Find chunk boundaries in token space and compute chunk embeddings
        chunk_embeddings = []
        
        for chunk_text in chunks:
            # Find chunk position in document
            chunk_start = document_text.find(chunk_text)
            if chunk_start == -1:
                logger.warning(
                    "chunk_not_found_in_document",
                    chunk_preview=chunk_text[:100]
                )
                # Fallback: embed chunk separately
                fallback_emb = self._encode_batch([chunk_text])[0]
                chunk_embeddings.append(fallback_emb)
                continue
            
            chunk_end = chunk_start + len(chunk_text)
            
            # Find tokens that overlap with this chunk
            token_indices = []
            for token_idx, (start, end) in enumerate(offset_mapping):
                # Token overlaps with chunk if there's any intersection
                if start < chunk_end and end > chunk_start:
                    token_indices.append(token_idx)
            
            if not token_indices:
                logger.warning("no_tokens_found_for_chunk", chunk_preview=chunk_text[:100])
                # Fallback: embed chunk separately
                fallback_emb = self._encode_batch([chunk_text])[0]
                chunk_embeddings.append(fallback_emb)
                continue
            
            # Pool token embeddings for this chunk (mean pooling)
            chunk_token_embeddings = token_embeddings[token_indices]  # [chunk_tokens, hidden_dim]
            chunk_embedding = chunk_token_embeddings.mean(dim=0)  # [hidden_dim]
            
            # Normalize
            chunk_embedding = chunk_embedding / chunk_embedding.norm()
            
            chunk_embeddings.append(chunk_embedding.cpu().tolist())
        
        logger.info(
            "late_chunking_completed",
            chunk_count=len(chunk_embeddings)
        )
        
        return chunk_embeddings
    
    def _encode_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Encode a batch of texts (internal method).
        
        Args:
            texts: Batch of texts
            
        Returns:
            List of embeddings
        """
        # Tokenize
        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.MAX_LENGTH
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Encode
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Mean pooling
            embeddings = self._mean_pooling(
                outputs.last_hidden_state,
                inputs["attention_mask"]
            )
            # Normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        
        return embeddings.cpu().tolist()
    
    def _mean_pooling(self, token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """
        Mean pooling with attention mask.
        
        Args:
            token_embeddings: [batch_size, seq_len, hidden_dim]
            attention_mask: [batch_size, seq_len]
            
        Returns:
            Pooled embeddings: [batch_size, hidden_dim]
        """
        # Expand attention mask to match embeddings dimension
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        
        # Sum embeddings (only for non-masked tokens)
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
        
        # Count non-masked tokens
        sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
        
        # Average
        return sum_embeddings / sum_mask
    
    def embed_chunks(self, chunks: List, batch_size: int = None) -> Dict[str, List]:
        """
        Embed multiple BaseChunk objects.
        
        Args:
            chunks: List of BaseChunk objects
            batch_size: Batch size for processing
            
        Returns:
            Dict with 'dense' and 'sparse' keys
        """
        if not chunks:
            return {"dense": [], "sparse": []}
        
        logger.info("embedding_chunks", chunk_count=len(chunks))
        
        # Extract texts from chunks
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings
        return self.embed_texts(texts, batch_size=batch_size)
    
    def embed_query(self, query: str, enhanced: bool = True) -> Dict[str, any]:
        """
        Embed a search query.
        
        Args:
            query: Query string
            enhanced: Whether to enhance query with instruction
            
        Returns:
            Dict with 'dense' embedding and empty 'sparse'
        """
        # Optionally enhance query
        if enhanced:
            query_text = f"Search query: {query}"
        else:
            query_text = query
        
        logger.debug("embedding_query", query_length=len(query), enhanced=enhanced)
        
        result = self.embed_texts([query_text])
        
        return {
            "dense": result["dense"][0],
            "sparse": {}  # Empty dict for compatibility
        }
    
    def _auto_detect_device(self) -> str:
        """Auto-detect best available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
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
        """Auto-detect optimal batch size based on device."""
        try:
            if self.device == "cuda" and torch.cuda.is_available():
                total_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                if total_memory_gb >= 40:
                    return 128
                elif total_memory_gb >= 24:
                    return 64
                elif total_memory_gb >= 12:
                    return 32
                else:
                    return 16
            elif self.device == "mps":
                return 32
            else:
                return 8
        except Exception:
            return 16
    
    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self.EMBEDDING_DIM
    
    def get_dimension(self) -> int:
        """Get embedding dimension (1024)."""
        return self.EMBEDDING_DIM
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension (alias for compatibility)."""
        return self.EMBEDDING_DIM
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"JinaLocalLateChunkingEmbedder("
            f"model={self.model_name}, "
            f"device={self.device}, "
            f"dimension={self.EMBEDDING_DIM})"
        )

