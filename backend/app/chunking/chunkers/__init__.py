"""Text chunker implementations."""

from app.chunking.chunkers.base_chunker import BaseChunker
from app.chunking.chunkers.recursive import RecursiveChunker


def create_chunker(name: str = "recursive", **kwargs):
    """
    Factory function to create chunker instances.

    Args:
        name: Type of chunker ("recursive", "hierarchical", "semantic")
        **kwargs: Additional arguments for the chunker

    Returns:
        Chunker instance
    """
    if name == "recursive":
        return RecursiveChunker(**kwargs)
    elif name == "hierarchical":
        from app.chunking.chunkers.hierarchical import HierarchicalChunker
        return HierarchicalChunker(**kwargs)
    elif name == "semantic":
        from app.chunking.chunkers.semantic import SemanticChunker
        return SemanticChunker(**kwargs)
    else:
        raise ValueError(f"Unknown chunker: {name}")


__all__ = [
    "BaseChunker",
    "RecursiveChunker",
    "create_chunker",
]

