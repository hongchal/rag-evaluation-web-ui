"""Embedder implementations."""

from app.embedding.embedders.bge_m3 import BGEM3Embedder


def create_embedder(name: str = "bge-m3", **kwargs):
    """
    Factory function to create embedder instances.

    Args:
        name: Type of embedder ("bge-m3", "matryoshka")
        **kwargs: Additional arguments for the embedder

    Returns:
        Embedder instance
    """
    if name == "bge-m3":
        return BGEM3Embedder(**kwargs)
    elif name == "matryoshka":
        from app.embedding.embedders.matryoshka import MatryoshkaEmbedder
        return MatryoshkaEmbedder(**kwargs)
    else:
        raise ValueError(f"Unknown embedder: {name}")


__all__ = ["BGEM3Embedder", "create_embedder"]

