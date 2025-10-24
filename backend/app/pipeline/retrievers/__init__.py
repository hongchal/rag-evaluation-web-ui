"""Retriever implementations."""

from app.pipeline.retrievers.base import BaseRetriever


def create_retriever(name: str = "base", **kwargs):
    """
    Factory function to create retriever instances.

    Args:
        name: Type of retriever ("base")
        **kwargs: Additional arguments for the retriever

    Returns:
        Retriever instance
    """
    if name == "base":
        return BaseRetriever(**kwargs)
    else:
        raise ValueError(f"Unknown retriever: {name}")


__all__ = ["BaseRetriever", "create_retriever"]

