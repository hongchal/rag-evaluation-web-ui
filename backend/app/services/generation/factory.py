"""Factory for creating text generation models."""

from typing import Optional
import structlog

from app.services.generation.base import AbstractGenerator

logger = structlog.get_logger(__name__)


class GeneratorFactory:
    """Factory for creating generation models."""
    
    @staticmethod
    def create(
        model_type: str,
        model_name: str,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> AbstractGenerator:
        """
        Create a generator instance based on model type.
        
        Args:
            model_type: Type of model ('claude' or 'vllm')
            model_name: Name of the model
            api_key: API key (for Claude)
            endpoint: Endpoint URL (for vLLM)
            
        Returns:
            AbstractGenerator instance
            
        Raises:
            ValueError: If model_type is unknown or required parameters are missing
        """
        if not model_type:
            raise ValueError("model_type is required")
        
        model_type = model_type.lower()
        
        if model_type == "claude":
            from app.services.generation.claude import ClaudeGenerator
            
            if not api_key:
                raise ValueError("api_key is required for Claude")
            
            logger.info("creating_claude_generator", model_name=model_name)
            return ClaudeGenerator(api_key=api_key, model_name=model_name)
        
        elif model_type == "vllm":
            from app.services.generation.vllm_http import VLLMHttpGenerator
            
            if not endpoint:
                raise ValueError("endpoint is required for vLLM")
            
            logger.info("creating_vllm_generator", model_name=model_name, endpoint=endpoint)
            return VLLMHttpGenerator(endpoint=endpoint, model_name=model_name)
        
        else:
            raise ValueError(
                f"Unknown model_type: {model_type}. "
                f"Supported types: 'claude', 'vllm'"
            )

