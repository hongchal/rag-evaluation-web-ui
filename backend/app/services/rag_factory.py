"""RAG Factory - Creates chunker, embedder, and reranker modules"""
from __future__ import annotations

from typing import Tuple, Any

# Chunkers
from app.chunking.chunkers.recursive import RecursiveChunker
from app.chunking.chunkers.hierarchical import HierarchicalChunker
from app.chunking.chunkers.semantic import SemanticChunker
from app.chunking.chunkers.late_chunking import LateChunkingWrapper

# Embedders
from app.embedding.embedders.bge_m3 import BGEM3Embedder
from app.embedding.embedders.matryoshka import MatryoshkaEmbedder
from app.embedding.embedders.vllm_http import VLLMHTTPEmbedder

# Rerankers
from app.reranking.rerankers.none import NoneReranker
from app.reranking.rerankers.cross_encoder import CrossEncoderReranker
from app.reranking.rerankers.bm25 import BM25Reranker
from app.reranking.rerankers.vllm_http import VLLMHTTPReranker
from app.reranking.rerankers.base_reranker import BaseReranker


class RAGFactory:
    """RAG 구성의 3가지 모듈을 생성하는 통합 Factory"""

    # Singleton instances for embedders (모델 중복 로딩 방지)
    _embedder_instances = {}

    @classmethod
    def create_chunker(cls, module: str, params: dict, embedder=None) -> Any:
        """
        Chunker 생성
        
        Args:
            module: Chunker module name
            params: Chunker parameters
            embedder: Embedder instance (optional, can be overridden by params)
        """
        if module == "recursive":
            return RecursiveChunker(**params)
        elif module == "hierarchical":
            return HierarchicalChunker(**params)
        elif module == "semantic":
            # Semantic chunker requires an embedder
            # Check if custom embedder is specified in params
            params_copy = params.copy()
            if "embedder_module" in params_copy:
                embedder_module = params_copy.pop("embedder_module")
                embedder_params = params_copy.pop("embedder_params", {})
                embedder = cls.create_embedder(embedder_module, embedder_params)
            
            if embedder is None:
                raise ValueError(
                    "Embedder must be provided for semantic chunker. "
                    "Either pass embedder parameter or specify 'embedder_module' in params."
                )
            return SemanticChunker(embedder=embedder, **params_copy)
        elif module == "late_chunking":
            return LateChunkingWrapper(**params)
        else:
            raise ValueError(f"Unknown chunker: {module}")

    @classmethod
    def create_embedder(cls, module: str, params: dict) -> Any:
        """Embedder 생성 (Singleton)"""
        # Singleton 패턴: 동일한 모듈은 한 번만 로드
        cache_key = f"{module}_{hash(frozenset(params.items()))}"
        
        if cache_key in cls._embedder_instances:
            return cls._embedder_instances[cache_key]
        
        if module == "bge_m3":
            embedder = BGEM3Embedder(**params)
        elif module == "matryoshka":
            embedder = MatryoshkaEmbedder(**params)
        elif module == "vllm_http":
            embedder = VLLMHTTPEmbedder(**params)
        else:
            raise ValueError(f"Unknown embedder: {module}")
        
        cls._embedder_instances[cache_key] = embedder
        return embedder

    @staticmethod
    def create_reranker(module: str, params: dict) -> BaseReranker:
        """Reranker 생성"""
        if module == "none":
            return NoneReranker()
        elif module == "cross_encoder":
            return CrossEncoderReranker(**params)
        elif module == "bm25":
            return BM25Reranker(**params)
        elif module == "vllm_http":
            return VLLMHTTPReranker(**params)
        # elif module == "colbert":
        #     return ColBERTReranker(**params)
        else:
            raise ValueError(f"Unknown reranker: {module}")

    @classmethod
    def create_rag(cls, config) -> Tuple[Any, Any, BaseReranker]:
        """RAG Configuration으로부터 전체 모듈 생성"""
        # Create embedder first (needed for semantic chunker)
        embedder = cls.create_embedder(
            config.embedding_module,
            config.embedding_params
        )
        
        # Create chunker (pass embedder for semantic chunking)
        chunker = cls.create_chunker(
            config.chunking_module,
            config.chunking_params,
            embedder=embedder
        )
        
        reranker = cls.create_reranker(
            config.reranking_module,
            config.reranking_params
        )

        return chunker, embedder, reranker
