"""
API routes for LLM model information.
"""
from fastapi import APIRouter
from typing import List, Dict, Any
import structlog

from app.services.generation.claude import CLAUDE_MODELS, DEFAULT_SYSTEM_PROMPT

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/claude")
def list_claude_models() -> Dict[str, Any]:
    """
    Get list of available Claude models.
    
    Returns:
        Dictionary with models list and metadata
    """
    logger.info("list_claude_models_requested")
    
    return {
        "models": CLAUDE_MODELS,
        "default_model": CLAUDE_MODELS[0]["id"],
        "total": len(CLAUDE_MODELS),
    }


@router.get("/prompt")
def get_system_prompt() -> Dict[str, str]:
    """
    Get the default RAG system prompt.
    
    Returns:
        Dictionary with system prompt
    """
    logger.info("get_system_prompt_requested")
    
    return {
        "prompt": DEFAULT_SYSTEM_PROMPT,
    }

