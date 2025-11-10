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
                        "similarity_threshold": 0.75,
                        "min_chunk_tokens": 100,
                        "max_chunk_tokens": 800,
                        "embedder_module": "bge_m3",
                        "embedder_params": {}
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
                "description": "Using external vLLM server for embeddings (base_url defaults to env VLLM_EMBEDDING_URL)",
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
                "description": "Using external vLLM server for reranking (base_url defaults to env VLLM_RERANKING_URL)",
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
                        "model_name": "BAAI/bge-reranker-v2-m3",
                        "timeout": 120.0,
                        "max_retries": 3
                    }
                }
            },
            {
                "name": "Late Chunking with Jina v3",
                "description": "Late chunking strategy - sentence-level chunking optimized for Jina embeddings",
                "chunking": {
                    "module": "late_chunking",
                    "params": {
                        "sentences_per_chunk": 3,
                        "min_chunk_tokens": 50,
                        "max_chunk_tokens": 512
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
    """
    RAG 수정 요청 (파라미터만 수정 가능)
    
    수정 가능:
    - name, description (기본 정보)
    - chunking_params, embedding_params, reranking_params (모듈 파라미터)
    
    수정 불가:
    - chunking_module, embedding_module, reranking_module (모듈 타입)
    - collection_name (이미 생성된 컬렉션)
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="RAG 설정 이름")
    description: Optional[str] = Field(None, description="RAG 설정 설명")
    chunking_params: Optional[Dict[str, Any]] = Field(None, description="청킹 모듈 파라미터 (예: chunk_size, chunk_overlap)")
    embedding_params: Optional[Dict[str, Any]] = Field(None, description="임베딩 모듈 파라미터 (예: model_name, base_url)")
    reranking_params: Optional[Dict[str, Any]] = Field(None, description="리랭킹 모듈 파라미터 (예: model_name, top_k)")
    
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "name": "Updated RAG Name",
                "description": "Updated description",
                "embedding_params": {
                    "model_name": "Qwen/Qwen3-Embedding-0.6B"
                }
            }
        ]
    })


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

