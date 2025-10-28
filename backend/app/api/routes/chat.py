"""API routes for chat session management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import structlog

from app.core.dependencies import get_db
from app.models.chat_session import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatSessionListResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new chat session with optional initial messages.
    """
    logger.info(
        "create_chat_session",
        title=session_data.title,
        pipeline_id=session_data.pipeline_id,
        model_type=session_data.model_type,
        message_count=len(session_data.messages),
    )
    
    # Create session
    db_session = ChatSession(
        title=session_data.title,
        pipeline_id=session_data.pipeline_id,
        model_type=session_data.model_type,
        model_name=session_data.model_name,
        llm_config=session_data.llm_config,
    )
    
    # Add messages
    for msg_data in session_data.messages:
        db_message = ChatMessage(
            role=msg_data.role,
            content=msg_data.content,
            sources=msg_data.sources,
            tokens_used=msg_data.tokens_used,
            generation_time=msg_data.generation_time,
        )
        db_session.messages.append(db_message)
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    logger.info("chat_session_created", session_id=db_session.id)
    
    return db_session


@router.get("/sessions", response_model=List[ChatSessionListResponse])
def list_sessions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    List all chat sessions with summary information.
    """
    logger.info("list_chat_sessions", skip=skip, limit=limit)
    
    sessions = (
        db.query(
            ChatSession,
            func.count(ChatMessage.id).label("message_count")
        )
        .outerjoin(ChatMessage)
        .group_by(ChatSession.id)
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    result = []
    for session, message_count in sessions:
        result.append(
            ChatSessionListResponse(
                id=session.id,
                title=session.title,
                pipeline_id=session.pipeline_id,
                model_type=session.model_type,
                model_name=session.model_name,
                message_count=message_count,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
        )
    
    return result


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific chat session with all messages.
    """
    logger.info("get_chat_session", session_id=session_id)
    
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )
    
    return session


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
def update_session(
    session_id: int,
    session_update: ChatSessionUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a chat session (title and/or add new messages).
    """
    logger.info("update_chat_session", session_id=session_id)
    
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )
    
    # Update title if provided
    if session_update.title:
        session.title = session_update.title
    
    # Add new messages if provided
    if session_update.messages:
        for msg_data in session_update.messages:
            db_message = ChatMessage(
                session_id=session_id,
                role=msg_data.role,
                content=msg_data.content,
                sources=msg_data.sources,
                tokens_used=msg_data.tokens_used,
                generation_time=msg_data.generation_time,
            )
            db.add(db_message)
    
    db.commit()
    db.refresh(session)
    
    logger.info("chat_session_updated", session_id=session_id)
    
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a chat session and all its messages.
    """
    logger.info("delete_chat_session", session_id=session_id)
    
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )
    
    db.delete(session)
    db.commit()
    
    logger.info("chat_session_deleted", session_id=session_id)
    
    return None

