"""RAG Service for managing RAG configurations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import structlog

from app.models.rag import RAGConfiguration
from app.services.rag_factory import RAGFactory

logger = structlog.get_logger(__name__)


class RAGService:
    """Service for managing RAG configurations."""

    @staticmethod
    def create_rag(
        db: Session,
        name: str,
        description: Optional[str],
        chunking_module: str,
        chunking_params: dict,
        embedding_module: str,
        embedding_params: dict,
        reranking_module: str,
        reranking_params: dict,
    ) -> RAGConfiguration:
        """
        Create a new RAG configuration.
        
        Args:
            db: Database session
            name: RAG configuration name
            description: Optional description
            chunking_module: Chunking module name
            chunking_params: Chunking parameters
            embedding_module: Embedding module name
            embedding_params: Embedding parameters
            reranking_module: Reranking module name
            reranking_params: Reranking parameters
            
        Returns:
            Created RAGConfiguration
            
        Raises:
            ValueError: If validation fails
            IntegrityError: If name already exists
        """
        # Validate modules
        RAGService.validate_rag_params(
            chunking_module, chunking_params,
            embedding_module, embedding_params,
            reranking_module, reranking_params
        )
        
        # Generate collection name
        # Will be updated with actual ID after creation
        collection_name = f"rag_temp_{name.lower().replace(' ', '_')}"
        
        # Create RAG configuration
        rag = RAGConfiguration(
            name=name,
            description=description,
            chunking_module=chunking_module,
            chunking_params=chunking_params,
            embedding_module=embedding_module,
            embedding_params=embedding_params,
            reranking_module=reranking_module,
            reranking_params=reranking_params,
            collection_name=collection_name,
        )
        
        try:
            db.add(rag)
            db.flush()  # Get ID without committing
            
            # Update collection name with actual ID
            rag.collection_name = f"rag_{rag.id}"
            
            db.commit()
            db.refresh(rag)
            
            logger.info(
                "rag_created",
                rag_id=rag.id,
                name=rag.name,
                collection=rag.collection_name
            )
            
            return rag
            
        except IntegrityError as e:
            db.rollback()
            logger.error("rag_creation_failed", error=str(e), name=name)
            raise ValueError(f"RAG with name '{name}' already exists")

    @staticmethod
    def validate_rag_params(
        chunking_module: str,
        chunking_params: dict,
        embedding_module: str,
        embedding_params: dict,
        reranking_module: str,
        reranking_params: dict,
    ) -> None:
        """
        Validate RAG module parameters.
        
        Raises:
            ValueError: If validation fails
        """
        # Validate chunking module
        valid_chunkers = ["recursive", "hierarchical", "semantic", "late_chunking"]
        if chunking_module not in valid_chunkers:
            raise ValueError(
                f"Invalid chunking module: {chunking_module}. "
                f"Must be one of: {', '.join(valid_chunkers)}"
            )
        
        # Validate embedding module
        valid_embedders = ["bge_m3", "matryoshka", "vllm_http", "jina_late_chunking"]
        if embedding_module not in valid_embedders:
            raise ValueError(
                f"Invalid embedding module: {embedding_module}. "
                f"Must be one of: {', '.join(valid_embedders)}"
            )
        
        # Validate reranking module
        valid_rerankers = ["none", "cross_encoder", "bm25", "vllm_http"]
        if reranking_module not in valid_rerankers:
            raise ValueError(
                f"Invalid reranking module: {reranking_module}. "
                f"Must be one of: {', '.join(valid_rerankers)}"
            )
        
        # Try to create modules to validate params
        # Note: This validation is skipped for now to avoid loading heavy models during config creation
        # Models will be loaded lazily when actually used
        # TODO: Add lightweight parameter validation without loading models
        
        # try:
        #     RAGFactory.create_chunker(chunking_module, chunking_params)
        # except Exception as e:
        #     raise ValueError(f"Invalid chunking params: {e}")
        
        # try:
        #     RAGFactory.create_embedder(embedding_module, embedding_params)
        # except Exception as e:
        #     raise ValueError(f"Invalid embedding params: {e}")
        
        # try:
        #     RAGFactory.create_reranker(reranking_module, reranking_params)
        # except Exception as e:
        #     raise ValueError(f"Invalid reranking params: {e}")
        
        logger.info("rag_params_validation_skipped", 
                   chunking=chunking_module, 
                   embedding=embedding_module,
                   reranking=reranking_module)

    @staticmethod
    def get_rag(db: Session, rag_id: int) -> Optional[RAGConfiguration]:
        """Get RAG configuration by ID."""
        return db.query(RAGConfiguration).filter(RAGConfiguration.id == rag_id).first()

    @staticmethod
    def get_rag_by_name(db: Session, name: str) -> Optional[RAGConfiguration]:
        """Get RAG configuration by name."""
        return db.query(RAGConfiguration).filter(RAGConfiguration.name == name).first()

    @staticmethod
    def list_rags(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[RAGConfiguration]:
        """List all RAG configurations."""
        return db.query(RAGConfiguration).offset(skip).limit(limit).all()

    @staticmethod
    def update_rag(
        db: Session,
        rag_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        chunking_params: Optional[dict] = None,
        embedding_params: Optional[dict] = None,
        reranking_params: Optional[dict] = None,
    ) -> Optional[RAGConfiguration]:
        """
        Update RAG configuration (파라미터만 수정 가능).
        
        수정 가능한 필드:
        - name, description: 기본 정보
        - chunking_params, embedding_params, reranking_params: 각 모듈의 파라미터
        
        수정 불가능한 필드:
        - chunking_module, embedding_module, reranking_module: 모듈 타입 (이미 인덱싱된 파이프라인에 영향)
        - collection_name: Qdrant 컬렉션 이름
        
        Returns:
            Updated RAGConfiguration or None if not found
            
        Raises:
            ValueError: If params validation fails
        """
        rag = RAGService.get_rag(db, rag_id)
        if not rag:
            return None
        
        # Update basic info
        if name is not None:
            rag.name = name
        if description is not None:
            rag.description = description
        
        # Update module parameters
        if chunking_params is not None:
            rag.chunking_params = {**rag.chunking_params, **chunking_params}  # Merge
        if embedding_params is not None:
            rag.embedding_params = {**rag.embedding_params, **embedding_params}  # Merge
        if reranking_params is not None:
            rag.reranking_params = {**rag.reranking_params, **reranking_params}  # Merge
        
        # Validate updated configuration
        if any([chunking_params, embedding_params, reranking_params]):
            RAGService.validate_rag_params(
                rag.chunking_module, rag.chunking_params,
                rag.embedding_module, rag.embedding_params,
                rag.reranking_module, rag.reranking_params
            )
        
        db.commit()
        db.refresh(rag)
        
        logger.info("rag_updated", rag_id=rag.id, name=rag.name)
        
        return rag

    @staticmethod
    def delete_rag(db: Session, rag_id: int) -> bool:
        """
        Delete RAG configuration.
        
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If RAG is used by existing pipelines
        """
        from app.models.pipeline import Pipeline
        
        rag = RAGService.get_rag(db, rag_id)
        if not rag:
            return False
        
        # Check if RAG is used by any pipelines
        pipeline_count = db.query(Pipeline).filter(Pipeline.rag_id == rag_id).count()
        if pipeline_count > 0:
            logger.warning("rag_delete_blocked", rag_id=rag_id, pipeline_count=pipeline_count)
            raise ValueError(f"Cannot delete RAG: {pipeline_count} pipeline(s) are using this RAG configuration. Please delete the pipelines first.")
        
        db.delete(rag)
        db.commit()
        
        logger.info("rag_deleted", rag_id=rag_id)
        
        return True

    @staticmethod
    def seed_default_rags(db: Session) -> List[RAGConfiguration]:
        """
        Seed default RAG configurations for quick start.
        
        Returns:
            List of created RAG configurations
        """
        default_rags = [
            {
                "name": "Fast RAG (Recursive + BGE-M3)",
                "description": "빠른 처리를 위한 기본 RAG 설정",
                "chunking_module": "recursive",
                "chunking_params": {"chunk_size": 512, "chunk_overlap": 50},
                "embedding_module": "bge_m3",
                "embedding_params": {},
                "reranking_module": "none",
                "reranking_params": {},
            },
            {
                "name": "Accurate RAG (Hierarchical + CrossEncoder)",
                "description": "정확도 우선 RAG 설정",
                "chunking_module": "hierarchical",
                "chunking_params": {"chunk_size": 512, "chunk_overlap": 100},
                "embedding_module": "bge_m3",
                "embedding_params": {},
                "reranking_module": "cross_encoder",
                "reranking_params": {"model_name": "BAAI/bge-reranker-v2-m3"},
            },
            {
                "name": "Semantic RAG (Semantic + BM25)",
                "description": "의미 기반 청킹 + BM25 리랭킹",
                "chunking_module": "semantic",
                "chunking_params": {"similarity_threshold": 0.7},
                "embedding_module": "bge_m3",
                "embedding_params": {},
                "reranking_module": "bm25",
                "reranking_params": {},
            },
        ]
        
        created_rags = []
        for rag_data in default_rags:
            # Check if already exists
            existing = RAGService.get_rag_by_name(db, rag_data["name"])
            if existing:
                logger.info("default_rag_already_exists", name=rag_data["name"])
                created_rags.append(existing)
                continue
            
            try:
                rag = RAGService.create_rag(db, **rag_data)
                created_rags.append(rag)
                logger.info("default_rag_created", name=rag.name)
            except Exception as e:
                logger.error("default_rag_creation_failed", name=rag_data["name"], error=str(e))
        
        return created_rags

