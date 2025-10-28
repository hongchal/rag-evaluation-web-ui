"""Generation service package for LLM-based answer generation."""

from app.services.generation.base import (
    AbstractGenerator,
    GenerationConfig,
    GenerationResult,
    format_context,
)
from app.services.generation.factory import GeneratorFactory
from app.services.generation.claude import ClaudeGenerator, CLAUDE_MODELS, DEFAULT_SYSTEM_PROMPT, get_rag_prompt
from app.services.generation.vllm_http import VLLMHttpGenerator

__all__ = [
    "AbstractGenerator",
    "GenerationConfig",
    "GenerationResult",
    "format_context",
    "GeneratorFactory",
    "ClaudeGenerator",
    "VLLMHttpGenerator",
    "CLAUDE_MODELS",
    "DEFAULT_SYSTEM_PROMPT",
    "get_rag_prompt",
]

