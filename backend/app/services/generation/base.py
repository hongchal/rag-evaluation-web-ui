"""Base classes and utilities for text generation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 0.9
    stop_sequences: Optional[List[str]] = None


@dataclass
class GenerationResult:
    """Result of text generation."""
    answer: str
    tokens_used: int
    generation_time: float
    model_name: str


class AbstractGenerator(ABC):
    """Abstract base class for text generation models."""
    
    @abstractmethod
    def generate(
        self,
        query: str,
        context: str,
        config: Optional[GenerationConfig] = None,
        system_prompt: Optional[str] = None,
    ) -> GenerationResult:
        """
        Generate answer based on query and context.
        
        Args:
            query: User question
            context: Retrieved chunks formatted as context
            config: Generation parameters (uses defaults if None)
            system_prompt: Custom system prompt (overrides default)
            
        Returns:
            GenerationResult with answer and metadata
            
        Raises:
            ValueError: If inputs are invalid
            Exception: If generation fails
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the generator is available.
        
        Returns:
            True if generator can be used (API key valid, server reachable, etc.)
        """
        pass


# Prompt formatting utilities

DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided context.

Instructions:
- Answer the question using ONLY the information from the provided context
- If the context doesn't contain enough information to answer, say "I cannot find enough information in the provided documents to answer this question."
- Cite the source document numbers when you use information from them (e.g., "According to Document 1...")
- Be concise but complete in your answers
- Use Korean if the question is in Korean, English if in English
"""


def format_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Format retrieved chunks as context for LLM.
    
    Args:
        chunks: List of chunk dictionaries with 'content' key
        
    Returns:
        Formatted context string
    """
    if not chunks:
        return ""
    
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Document {i}]")
        context_parts.append(chunk.get("content", ""))
        context_parts.append("")  # blank line
    
    return "\n".join(context_parts)


def format_prompt(query: str, context: str) -> str:
    """
    Format complete prompt with context and query.
    
    Args:
        query: User question
        context: Formatted context from chunks
        
    Returns:
        Complete prompt string
    """
    user_prompt = f"""Context:
{context}

Question: {query}

Answer:"""
    
    return user_prompt


def estimate_tokens(text: str) -> int:
    """
    Rough estimation of token count.
    
    Args:
        text: Text to estimate
        
    Returns:
        Estimated token count (rough approximation)
    """
    # Rough estimation: ~4 characters per token on average
    return len(text) // 4

