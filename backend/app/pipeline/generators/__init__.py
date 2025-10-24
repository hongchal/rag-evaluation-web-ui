"""Generator implementations."""

from app.pipeline.generators.claude import ClaudeGenerator


def create_generator(name: str = "claude", **kwargs):
    """
    Factory function to create generator instances.

    Args:
        name: Type of generator ("claude")
        **kwargs: Additional arguments for the generator

    Returns:
        Generator instance
    """
    if name == "claude":
        return ClaudeGenerator(**kwargs)
    else:
        raise ValueError(f"Unknown generator: {name}")


__all__ = ["ClaudeGenerator", "create_generator"]

