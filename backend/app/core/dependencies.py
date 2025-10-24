"""Dependency injection for FastAPI."""

from functools import lru_cache
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.qdrant_service import QdrantService


def get_db() -> Session:
    """
    Get database session.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@lru_cache()
def get_qdrant_service() -> QdrantService:
    """
    Get singleton QdrantService instance.
    
    Returns:
        QdrantService instance
    """
    return QdrantService()

