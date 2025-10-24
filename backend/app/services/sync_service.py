"""Sync Service for synchronizing data sources with RAG configurations."""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import structlog
import traceback
import time

from app.models.rag import RAGConfiguration
from app.models.datasource import DataSource
from app.models.datasource_sync import DataSourceSync, SyncStatus
from app.models.base_chunk import BaseChunk
from app.services.rag_factory import RAGFactory
from app.services.document_loader import DocumentLoader
from app.services.qdrant_service import QdrantService

logger = structlog.get_logger(__name__)


class SyncService:
    """Service for synchronizing data sources with RAG configurations."""

    def __init__(self, db: Session, qdrant_service: QdrantService):
        """
        Initialize SyncService.
        
        Args:
            db: Database session
            qdrant_service: Qdrant service instance
        """
        self.db = db
        self.qdrant_service = qdrant_service

    def sync_datasource_by_id(self, sync_id: int) -> DataSourceSync:
        """
        Synchronize using existing sync record.
        
        Args:
            sync_id: Existing sync record ID
            
        Returns:
            Updated DataSourceSync record
        """
        sync = self.get_sync(sync_id)
        if not sync:
            raise ValueError(f"Sync {sync_id} not found")
        
        return self.sync_datasource(sync.rag_id, sync.datasource_id, sync_id=sync_id)

    def sync_datasource(
        self,
        rag_id: int,
        datasource_id: int,
        sync_id: Optional[int] = None,
    ) -> DataSourceSync:
        """
        Synchronize a data source with a RAG configuration.
        
        This method performs the following steps:
        1. Load RAG configuration and create modules (chunker, embedder)
        2. Load data source file
        3. Chunk the document (with progress updates)
        4. Embed chunks (with progress updates)
        5. Store vectors in Qdrant collection "rag_{rag_id}"
        
        Args:
            rag_id: RAG configuration ID
            datasource_id: Data source ID
            sync_id: Optional existing sync ID to update
            
        Returns:
            DataSourceSync record with status and results
            
        Raises:
            ValueError: If RAG or DataSource not found
        """
        # Load RAG and DataSource
        rag = self.db.query(RAGConfiguration).filter(RAGConfiguration.id == rag_id).first()
        if not rag:
            raise ValueError(f"RAG configuration {rag_id} not found")
        
        datasource = self.db.query(DataSource).filter(DataSource.id == datasource_id).first()
        if not datasource:
            raise ValueError(f"Data source {datasource_id} not found")
        
        # Get existing sync or create new one
        if sync_id:
            sync = self.get_sync(sync_id)
            if not sync:
                raise ValueError(f"Sync {sync_id} not found")
        else:
            sync = DataSourceSync(
                rag_id=rag_id,
                datasource_id=datasource_id,
                status=SyncStatus.PENDING,
                progress=0.0,
                current_step="Initializing",
            )
            self.db.add(sync)
            self.db.commit()
            self.db.refresh(sync)
        
        # Start sync
        sync.status = SyncStatus.IN_PROGRESS
        sync.progress = 0.0
        sync.current_step = "Loading modules"
        sync.error_message = None
        self.db.commit()
        
        start_time = time.time()
        
        try:
            # Step 1: Create RAG modules
            logger.info(
                "sync_started",
                sync_id=sync.id,
                rag_id=rag_id,
                datasource_id=datasource_id
            )
            
            chunker = RAGFactory.create_chunker(
                rag.chunking_module,
                rag.chunking_params
            )
            embedder = RAGFactory.create_embedder(
                rag.embedding_module,
                rag.embedding_params
            )
            
            sync.progress = 10.0
            sync.current_step = "Loading document"
            self.db.commit()
            
            # Step 2: Load document
            documents = DocumentLoader.load_file(datasource.source_uri)
            if not documents:
                raise ValueError(f"No documents loaded from {datasource.source_uri}")
            
            # For now, handle single document
            document = documents[0]
            
            sync.progress = 20.0
            sync.current_step = "Chunking document"
            self.db.commit()
            
            # Step 3: Chunk document
            chunks: List[BaseChunk] = chunker.chunk_document(document)
            num_chunks = len(chunks)
            
            logger.info(
                "chunking_completed",
                sync_id=sync.id,
                num_chunks=num_chunks
            )
            
            sync.progress = 40.0
            sync.current_step = f"Embedding {num_chunks} chunks"
            self.db.commit()
            
            # Step 4: Embed chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = embedder.embed(chunk_texts)
            
            logger.info(
                "embedding_completed",
                sync_id=sync.id,
                num_embeddings=len(embeddings)
            )
            
            sync.progress = 70.0
            sync.current_step = "Storing in Qdrant"
            self.db.commit()
            
            # Step 5: Ensure collection exists
            vector_size = len(embeddings[0]) if embeddings else 1024
            self.qdrant_service.create_collection(
                collection_name=rag.collection_name,
                vector_size=vector_size,
                enable_hybrid=False,  # For now, dense only
            )
            
            # Step 6: Store in Qdrant
            self.qdrant_service.add_chunks(
                collection_name=rag.collection_name,
                chunks=chunks,
                embeddings=embeddings,
                datasource_id=datasource_id,
            )
            
            logger.info(
                "qdrant_storage_completed",
                sync_id=sync.id,
                collection=rag.collection_name
            )
            
            # Calculate sync time
            sync_time = time.time() - start_time
            
            # Update sync record
            sync.status = SyncStatus.COMPLETED
            sync.progress = 100.0
            sync.current_step = "Completed"
            sync.num_chunks = num_chunks
            sync.sync_time = sync_time
            self.db.commit()
            
            logger.info(
                "sync_completed",
                sync_id=sync.id,
                num_chunks=num_chunks,
                sync_time=sync_time
            )
            
            return sync
            
        except Exception as e:
            # Handle error
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            logger.error(
                "sync_failed",
                sync_id=sync.id,
                error=error_msg,
                trace=error_trace
            )
            
            sync.status = SyncStatus.FAILED
            sync.error_message = error_msg
            self.db.commit()
            
            raise

    def get_sync(self, sync_id: int) -> Optional[DataSourceSync]:
        """Get sync record by ID."""
        return self.db.query(DataSourceSync).filter(DataSourceSync.id == sync_id).first()

    def get_syncs_by_rag(self, rag_id: int) -> List[DataSourceSync]:
        """Get all syncs for a RAG configuration."""
        return (
            self.db.query(DataSourceSync)
            .filter(DataSourceSync.rag_id == rag_id)
            .all()
        )

    def get_syncs_by_datasource(self, datasource_id: int) -> List[DataSourceSync]:
        """Get all syncs for a data source."""
        return (
            self.db.query(DataSourceSync)
            .filter(DataSourceSync.datasource_id == datasource_id)
            .all()
        )

    def cancel_sync(self, sync_id: int) -> bool:
        """
        Cancel a running sync.
        
        Returns:
            True if cancelled, False if not found or not running
        """
        sync = self.get_sync(sync_id)
        if not sync or sync.status != SyncStatus.IN_PROGRESS:
            return False
        
        sync.status = SyncStatus.FAILED
        sync.error_message = "Cancelled by user"
        self.db.commit()
        
        logger.info("sync_cancelled", sync_id=sync_id)
        
        return True

    def retry_sync(self, sync_id: int) -> DataSourceSync:
        """
        Retry a failed sync.
        
        Returns:
            Updated sync record
            
        Raises:
            ValueError: If sync not found or not in failed state
        """
        sync = self.get_sync(sync_id)
        if not sync:
            raise ValueError(f"Sync {sync_id} not found")
        
        if sync.status != SyncStatus.FAILED:
            raise ValueError(f"Sync {sync_id} is not in failed state")
        
        # Re-run sync
        return self.sync_datasource(sync.rag_id, sync.datasource_id)

    def delete_sync(self, sync_id: int) -> bool:
        """
        Delete a sync record.
        
        Returns:
            True if deleted, False if not found
        """
        sync = self.get_sync(sync_id)
        if not sync:
            return False
        
        self.db.delete(sync)
        self.db.commit()
        
        logger.info("sync_deleted", sync_id=sync_id)
        
        return True

