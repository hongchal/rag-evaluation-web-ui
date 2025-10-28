"""
vLLM HTTP-based text generation implementation.
"""
import time
import requests
from typing import Optional, Dict, Any
from structlog import get_logger

from .base import AbstractGenerator, GenerationConfig, GenerationResult
from .claude import get_rag_prompt, DEFAULT_SYSTEM_PROMPT

logger = get_logger(__name__)


class VLLMHttpGenerator(AbstractGenerator):
    """
    Text generator using vLLM HTTP endpoint.
    Supports OpenAI-compatible API format.
    """
    
    def __init__(
        self,
        endpoint: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        timeout: int = 300,
    ):
        """
        Initialize vLLM HTTP generator.
        
        Args:
            endpoint: vLLM HTTP endpoint URL
            model_name: Model name
            system_prompt: Optional system prompt
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint.rstrip('/')
        self.model_name = model_name
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.timeout = timeout
        
        logger.info(
            "vllm_http_generator_initialized",
            endpoint=self.endpoint,
            model=model_name,
            has_custom_prompt=system_prompt is not None,
        )
    
    def generate(
        self,
        query: str,
        context: str,
        config: Optional[GenerationConfig] = None,
        system_prompt: Optional[str] = None,
    ) -> GenerationResult:
        """
        Generate answer using vLLM HTTP endpoint.
        
        Args:
            query: User question
            context: Retrieved context
            config: Generation configuration
            
        Returns:
            GenerationResult with answer and metadata
        """
        if config is None:
            config = GenerationConfig()
        
        start_time = time.time()
        
        try:
            # Build user prompt
            user_prompt = get_rag_prompt(query, context)
            
            # Use custom system prompt if provided, otherwise use default
            final_system_prompt = system_prompt if system_prompt else self.system_prompt
            
            logger.info(
                "vllm_http_request",
                endpoint=self.endpoint,
                model=self.model_name,
                query_length=len(query),
                context_length=len(context),
                temperature=config.temperature,
                custom_prompt=bool(system_prompt),
            )
            
            # Prepare request payload (OpenAI-compatible format)
            payload: Dict[str, Any] = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": final_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
            }
            
            if config.stop_sequences:
                payload["stop"] = config.stop_sequences
            
            # Make HTTP request
            response = requests.post(
                f"{self.endpoint}/v1/chat/completions",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract answer
            if "choices" not in data or len(data["choices"]) == 0:
                raise ValueError("No response choices returned from vLLM")
            
            answer = data["choices"][0]["message"]["content"]
            
            # Extract token usage
            usage = data.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            generation_time = time.time() - start_time
            
            logger.info(
                "vllm_http_success",
                endpoint=self.endpoint,
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                generation_time=generation_time,
            )
            
            return GenerationResult(
                answer=answer,
                tokens_used=total_tokens,
                generation_time=generation_time,
                model_name=self.model_name,
            )
            
        except requests.exceptions.Timeout:
            logger.error(
                "vllm_http_timeout",
                endpoint=self.endpoint,
                timeout=self.timeout,
            )
            raise ValueError(f"vLLM request timed out after {self.timeout}s")
        
        except requests.exceptions.RequestException as e:
            logger.error(
                "vllm_http_error",
                error=str(e),
                endpoint=self.endpoint,
            )
            raise ValueError(f"vLLM HTTP error: {str(e)}") from e
        
        except Exception as e:
            logger.error(
                "vllm_generation_error",
                error=str(e),
                endpoint=self.endpoint,
            )
            raise RuntimeError(f"Failed to generate answer: {str(e)}") from e
    
    def is_available(self) -> bool:
        """
        Check if vLLM endpoint is available.
        
        Returns:
            True if endpoint is reachable and responding
        """
        try:
            # Try to connect to the endpoint with a simple health check
            response = requests.get(
                f"{self.endpoint}/health",
                timeout=5,
            )
            return response.ok
        except Exception as e:
            logger.warning("vllm_availability_check_failed", error=str(e), endpoint=self.endpoint)
            # If health check fails, try models endpoint
            try:
                response = requests.get(
                    f"{self.endpoint}/v1/models",
                    timeout=5,
                )
                return response.ok
            except:
                return False
    
    def get_system_prompt(self) -> str:
        """Get the current system prompt."""
        return self.system_prompt
    
    def set_system_prompt(self, prompt: str) -> None:
        """Update the system prompt."""
        self.system_prompt = prompt
        logger.info("vllm_system_prompt_updated", prompt_length=len(prompt))

