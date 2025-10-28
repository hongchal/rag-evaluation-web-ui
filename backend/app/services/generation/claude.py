"""
Claude-based text generation implementation.
"""
import time
from typing import Optional
import anthropic
from structlog import get_logger

from .base import AbstractGenerator, GenerationConfig, GenerationResult

logger = get_logger(__name__)

# Available Claude models (최신 업데이트: 2025년 10월 28일)
# 출처: Anthropic 공식 모델 비교 문서
CLAUDE_MODELS = [
    # Claude 4.x 시리즈 (최신 - 2025)
    {
        "id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet 4.5",
        "description": "🚀 가장 똑똑한 모델 - 복잡한 에이전트 및 코딩 작업에 최적 ($3/MTok input, $15/MTok output)",
        "context_window": 200000,
        "max_output": 8096,
    },
    {
        "id": "claude-haiku-4-5-20251001",
        "name": "Claude Haiku 4.5",
        "description": "⚡ 가장 빠른 모델 - 준최고 수준 지능과 속도 ($1/MTok input, $5/MTok output)",
        "context_window": 200000,
        "max_output": 8096,
    },
    {
        "id": "claude-opus-4-1-20250805",
        "name": "Claude Opus 4.1",
        "description": "🎯 특화 모델 - 전문적 추론 작업에 최적 ($15/MTok input, $75/MTok output)",
        "context_window": 200000,
        "max_output": 8096,
    },
    # Claude 3.5 시리즈 (이전 세대)
    {
        "id": "claude-3-5-sonnet-20241022",
        "name": "Claude 3.5 Sonnet (Oct 2024)",
        "description": "이전 세대 Sonnet 모델",
        "context_window": 200000,
        "max_output": 8096,
    },
    {
        "id": "claude-3-5-haiku-20241022",
        "name": "Claude 3.5 Haiku (Oct 2024)",
        "description": "이전 세대 Haiku 모델",
        "context_window": 200000,
        "max_output": 8096,
    },
    {
        "id": "claude-3-5-sonnet-20240620",
        "name": "Claude 3.5 Sonnet (Jun 2024)",
        "description": "초기 3.5 버전",
        "context_window": 200000,
        "max_output": 8096,
    },
    # Claude 3 시리즈 (레거시)
    {
        "id": "claude-3-opus-20240229",
        "name": "Claude 3 Opus (Feb 2024)",
        "description": "3세대 최고 성능 모델",
        "context_window": 200000,
        "max_output": 4096,
    },
    {
        "id": "claude-3-sonnet-20240229",
        "name": "Claude 3 Sonnet (Feb 2024)",
        "description": "3세대 균형잡힌 모델",
        "context_window": 200000,
        "max_output": 4096,
    },
    {
        "id": "claude-3-haiku-20240307",
        "name": "Claude 3 Haiku (Mar 2024)",
        "description": "3세대 고속 모델",
        "context_window": 200000,
        "max_output": 4096,
    },
]

# Default system prompt for RAG
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant specialized in answering questions based on provided context.

Your task is to:
1. Carefully read and analyze the provided context documents
2. Answer the user's question based ONLY on the information in the context
3. If the context doesn't contain enough information to answer the question, clearly state that
4. Cite relevant parts of the context when appropriate
5. Be concise but comprehensive in your answers

Important guidelines:
- DO NOT make up information that isn't in the context
- If you're uncertain, acknowledge it
- Focus on accuracy over completeness
- Use clear and professional language"""


def get_rag_prompt(query: str, context: str) -> str:
    """
    Generate the user prompt for RAG-based question answering.
    
    Args:
        query: User's question
        context: Retrieved context documents
        
    Returns:
        Formatted prompt string
    """
    return f"""Context Documents:
{context}

---

Question: {query}

Please provide a detailed answer based on the context above."""


class ClaudeGenerator(AbstractGenerator):
    """
    Text generator using Claude API.
    """
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-5-sonnet-20241022",
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize Claude generator.
        
        Args:
            api_key: Anthropic API key
            model_name: Claude model name
            system_prompt: Optional system prompt (uses default if not provided)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = model_name
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        
        logger.info(
            "claude_generator_initialized",
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
        Generate answer using Claude API.
        
        Args:
            query: User question
            context: Retrieved context
            config: Generation configuration
            system_prompt: Custom system prompt (overrides default)
            
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
                "claude_api_request",
                model=self.model_name,
                query_length=len(query),
                context_length=len(context),
                temperature=config.temperature,
                custom_prompt=bool(system_prompt),
            )
            
            # Call Claude API
            # Note: Claude 4.x models don't support both temperature and top_p simultaneously
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                # top_p is not supported with temperature in Claude 4.x
                system=final_system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
            )
            
            # Extract answer
            answer = message.content[0].text
            
            # Calculate tokens
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            generation_time = time.time() - start_time
            
            logger.info(
                "claude_api_success",
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
            
        except anthropic.APIError as e:
            logger.error(
                "claude_api_error",
                error=str(e),
                model=self.model_name,
            )
            raise ValueError(f"Claude API error: {str(e)}") from e
        
        except Exception as e:
            logger.error(
                "claude_generation_error",
                error=str(e),
                model=self.model_name,
            )
            raise RuntimeError(f"Failed to generate answer: {str(e)}") from e
    
    def is_available(self) -> bool:
        """
        Check if Claude API is available.
        
        Returns:
            True if API key is valid and Claude API is reachable
        """
        try:
            # Simple check - try to create a message with minimal tokens
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}],
            )
            return True
        except Exception as e:
            logger.warning("claude_availability_check_failed", error=str(e))
            return False
    
    def get_system_prompt(self) -> str:
        """Get the current system prompt."""
        return self.system_prompt
    
    def set_system_prompt(self, prompt: str) -> None:
        """Update the system prompt."""
        self.system_prompt = prompt
        logger.info("claude_system_prompt_updated", prompt_length=len(prompt))

