"""Data Source Model"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class SourceType(str, enum.Enum):
    """데이터 소스 타입"""
    FILE = "file"
    URL = "url"
    DATABASE = "database"
    API = "api"


class SourceStatus(str, enum.Enum):
    """데이터 소스 상태"""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class DataSource(Base):
    """데이터 소스 모델"""

    __tablename__ = "datasources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    source_type = Column(SQLEnum(SourceType), nullable=False, index=True)
    source_uri = Column(Text, nullable=False)  # 파일 경로, URL 등

    # File metadata
    file_size = Column(BigInteger, nullable=True)  # bytes
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256

    # Status
    status = Column(SQLEnum(SourceStatus), default=SourceStatus.PENDING, nullable=False, index=True)

    # Additional metadata (JSON)
    source_metadata = Column(Text, nullable=True)  # JSON string

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    syncs = relationship("DataSourceSync", back_populates="datasource", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DataSource(id={self.id}, name='{self.name}', type='{self.source_type}')>"

