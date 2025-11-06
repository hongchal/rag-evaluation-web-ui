"""Embedder implementations."""

from app.embedding.embedders.bge_m3 import BGEM3Embedder
from app.embedding.embedders.matryoshka import MatryoshkaEmbedder
from app.embedding.embedders.vllm_http import VLLMHTTPEmbedder
from app.embedding.embedders.jina_late_chunking import JinaLocalLateChunkingEmbedder


def create_embedder(name: str = "bge-m3", **kwargs):
    """
    Factory function to create embedder instances.

    Args:
        name: Type of embedder ("bge-m3", "matryoshka", "vllm-http", "jina-late-chunking")
        **kwargs: Additional arguments for the embedder

    Returns:
        Embedder instance
    """
    if name == "bge-m3":
        return BGEM3Embedder(**kwargs)
    elif name == "matryoshka":
        return MatryoshkaEmbedder(**kwargs)
    elif name == "vllm-http":
        return VLLMHTTPEmbedder(**kwargs)
    elif name == "jina-late-chunking":
        return JinaLocalLateChunkingEmbedder(**kwargs)
    else:
        raise ValueError(f"Unknown embedder: {name}")


__all__ = [
    "BGEM3Embedder",
    "MatryoshkaEmbedder", 
    "VLLMHTTPEmbedder",
    "JinaLocalLateChunkingEmbedder",
    "create_embedder"
]

