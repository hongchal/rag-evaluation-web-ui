"""RAG Configuration Schemas"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# Config schemas for each module
class ChunkingConfig(BaseModel):
    """청킹 모듈 설정"""
    module: str = Field(..., description="Chunking module name (recursive, hierarchical, semantic, late_chunking)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Module-specific parameters")


class EmbeddingConfig(BaseModel):
    """임베딩 모듈 설정"""
    module: str = Field(..., description="Embedding module name (bge_m3, matryoshka, vllm_http, jina_late_chunking)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Module-specific parameters")


class RerankingConfig(BaseModel):
    """리랭킹 모듈 설정"""
    module: str = Field(..., description="Reranking module name (cross_encoder, bm25, colbert, none)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Module-specific parameters")


# RAG CRUD schemas
class RAGBase(BaseModel):
    """RAG 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255, description="RAG configuration name")
    description: Optional[str] = Field(None, description="RAG configuration description")


class RAGCreate(RAGBase):
    """RAG 생성 요청"""
    chunking: ChunkingConfig = Field(..., description="Chunking configuration")
    embedding: EmbeddingConfig = Field(..., description="Embedding configuration")
    reranking: RerankingConfig = Field(..., description="Reranking configuration")

    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "name": "BGE-M3 + Recursive + CrossEncoder",
                "description": "Standard RAG configuration with BGE-M3 embeddings",
                "chunking": {
                    "module": "recursive",
                    "params": {
                        "chunk_size": 512,
                        "chunk_overlap": 50
                    }
                },
                "embedding": {
                    "module": "bge_m3",
                    "params": {
                        "model_name": "BAAI/bge-m3",
                        "use_fp16": True,
                        "batch_size": 32
                    }
                },
                "reranking": {
                    "module": "cross_encoder",
                    "params": {
                        "model_name": "BAAI/bge-reranker-v2-m3",
                        "device": "cuda"
                    }
                }
            },
            {
                "name": "Custom Embedding Model",
                "description": "Using different embedding and reranking models",
                "chunking": {
                    "module": "semantic",
                    "params": {
                        "breakpoint_threshold_type": "percentile",
                        "breakpoint_threshold_amount": 95
                    }
                },
                "embedding": {
                    "module": "bge_m3",
                    "params": {
                        "model_name": "BAAI/bge-large-en-v1.5",
                        "use_fp16": False
                    }
                },
                "reranking": {
                    "module": "cross_encoder",
                    "params": {
                        "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
                    }
                }
            },
            {
                "name": "No Reranking",
                "description": "RAG without reranking step",
                "chunking": {
                    "module": "recursive",
                    "params": {
                        "chunk_size": 1024,
                        "chunk_overlap": 100
                    }
                },
                "embedding": {
                    "module": "bge_m3",
                    "params": {}
                },
                "reranking": {
                    "module": "none",
                    "params": {}
                }
            },
            {
                "name": "vLLM HTTP Embedding",
                "description": "Using external vLLM server for embeddings",
                "chunking": {
                    "module": "recursive",
                    "params": {
                        "chunk_size": 512,
                        "chunk_overlap": 50
                    }
                },
                "embedding": {
                    "module": "vllm_http",
                    "params": {
                        "base_url": "http://localhost:8000",
                        "model_name": "Qwen/Qwen2.5-Coder-Instruct-8B",
                        "embedding_dim": 4096,
                        "timeout": 120.0
                    }
                },
                "reranking": {
                    "module": "bm25",
                    "params": {}
                }
            },
            {
                "name": "Matryoshka Adaptive",
                "description": "Adaptive dimensionality with Matryoshka embeddings",
                "chunking": {
                    "module": "hierarchical",
                    "params": {
                        "parent_chunk_size": 2048,
                        "child_chunk_size": 512,
                        "overlap": 100
                    }
                },
                "embedding": {
                    "module": "matryoshka",
                    "params": {
                        "model_name": "BAAI/bge-m3",
                        "default_dimension": 512,
                        "adaptive": True
                    }
                },
                "reranking": {
                    "module": "cross_encoder",
                    "params": {
                        "model_name": "BAAI/bge-reranker-v2-m3"
                    }
                }
            },
            {
                "name": "vLLM HTTP Reranking",
                "description": "Using external vLLM server for reranking",
                "chunking": {
                    "module": "recursive",
                    "params": {
                        "chunk_size": 512,
                        "chunk_overlap": 50
                    }
                },
                "embedding": {
                    "module": "bge_m3",
                    "params": {
                        "model_name": "BAAI/bge-m3"
                    }
                },
                "reranking": {
                    "module": "vllm_http",
                    "params": {
                        "base_url": "http://localhost:8001",
                        "model_name": "BAAI/bge-reranker-v2-m3",
                        "timeout": 120.0,
                        "max_retries": 3
                    }
                }
            },
            {
                "name": "Late Chunking with Jina v3",
                "description": "Late chunking strategy (chunking only, uses Jina v3 model internally)",
                "chunking": {
                    "module": "late_chunking",
                    "params": {
                        "model_name": "jinaai/jina-embeddings-v3",
                        "max_length": 8192,
                        "late_chunking": True
                    }
                },
                "embedding": {
                    "module": "bge_m3",
                    "params": {
                        "model_name": "BAAI/bge-m3"
                    }
                },
                "reranking": {
                    "module": "cross_encoder",
                    "params": {
                        "model_name": "BAAI/bge-reranker-v2-m3"
                    }
                }
            }
        ]
    })


class RAGUpdate(BaseModel):
    """RAG 수정 요청 (부분 업데이트)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    chunking: Optional[ChunkingConfig] = None
    embedding: Optional[EmbeddingConfig] = None
    reranking: Optional[RerankingConfig] = None


class RAGResponse(RAGBase):
    """RAG 응답"""
    id: int
    collection_name: str
    chunking_module: str
    chunking_params: Dict[str, Any]
    embedding_module: str
    embedding_params: Dict[str, Any]
    reranking_module: str
    reranking_params: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RAGListResponse(BaseModel):
    """RAG 목록 응답"""
    total: int
    items: list[RAGResponse]

