"""Configuration settings for the application."""

from pathlib import Path
from typing import Optional

import torch
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/rag_evaluation",
        description="PostgreSQL database URL",
    )

    # Qdrant
    qdrant_url: str = Field(
        default="http://localhost:6333", description="Qdrant server URL"
    )
    qdrant_api_key: Optional[str] = Field(
        default=None, description="Qdrant API key (optional)"
    )

    # Embedding
    embedding_model: str = Field(
        default="BAAI/bge-m3", description="HuggingFace embedding model name"
    )
    embedding_device: str = Field(
        default="auto", description="Device for embedding (auto/cuda/mps/cpu)"
    )
    embedding_batch_size: int = Field(
        default=32, description="Batch size for embedding generation"
    )
    embedding_dimension: int = Field(
        default=1024, description="Embedding vector dimension"
    )

    # Chunking
    chunk_size: int = Field(
        default=512, description="Default chunk size for text splitting"
    )
    chunk_overlap: int = Field(
        default=50, description="Default chunk overlap"
    )

    # File Storage
    upload_dir: str = Field(default="./uploads", description="Directory for uploads")
    max_file_size_mb: int = Field(default=50, description="Max file size in MB")

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    cors_origins: str = Field(
        default="http://localhost:5174,http://localhost:3000",
        description="Comma-separated CORS origins",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # AI Services
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key for Claude"
    )

    @field_validator("embedding_device", mode="before")
    @classmethod
    def auto_detect_device(cls, v):
        """Auto-detect best available device for embedding."""
        if v and v != "auto":
            # Validate requested device
            if v == "cuda" and not torch.cuda.is_available():
                print(
                    "⚠️  CUDA requested but not available, falling back to auto-detect"
                )
                v = "auto"
            elif v == "mps" and not torch.backends.mps.is_available():
                print("⚠️  MPS requested but not available, falling back to auto-detect")
                v = "auto"

        # Auto-detect if "auto" or device not available
        if not v or v == "auto":
            if torch.cuda.is_available():
                detected = "cuda"
            elif torch.backends.mps.is_available():
                detected = "mps"
            else:
                detected = "cpu"
            print(f"🔍 Auto-detected embedding device: {detected}")
            return detected

        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def upload_path(self) -> Path:
        """Get upload directory as Path."""
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent.parent / ".env"),  # 프로젝트 루트/.env
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
