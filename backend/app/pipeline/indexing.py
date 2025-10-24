"""Indexing Pipeline for document ingestion with PostgreSQL."""

from datetime import datetime
from typing import Any, Dict, List

import structlog
from app.chunking.chunkers import create_chunker
from app.embedding.embedders import create_embedder
from app.embedding.vector_stores import create_vector_store

from app.ingestion.storage.postgres import PostgresDocumentStore

logger = structlog.get_logger(__name__)


class IndexingPipeline:
    """
    Document indexing pipeline: Chunk → Embed → Store (Vector + PostgreSQL).

    Flow:
    1. Check if document changed (via PostgreSQL content_hash)
    2. Chunk documents into smaller pieces
    3. Generate embeddings for chunks
    4. Store chunks in vector store (Qdrant)
    5. Store metadata in PostgreSQL

    Usage:
        pipeline = IndexingPipeline()
        stats = await pipeline.index_documents(documents, datasource_id="...")
    """

    def __init__(
        self,
        chunker_name: str = "recursive",
        embedder_name: str = "bge-m3",
        vector_store_name: str = "qdrant"
    ):
        """
        Initialize indexing pipeline.

        Args:
            chunker_name: Chunker type ('recursive')
            embedder_name: Embedder type ('bge-m3')
            vector_store_name: Vector store type ('qdrant')
        """
        logger.info(
            "initializing_indexing_pipeline",
            chunker=chunker_name,
            embedder=embedder_name,
            vector_store=vector_store_name
        )

        self.chunker = create_chunker(chunker_name)
        self.embedder = create_embedder(embedder_name)
        self.vector_store = create_vector_store(vector_store_name)
        self.document_store = PostgresDocumentStore()

        # Ensure collection exists
        if not self.vector_store.collection_exists():
            self.vector_store.create_collection()

        logger.info("indexing_pipeline_initialized")

    async def index_documents(
        self,
        documents: List[BaseDocument],
        datasource_id: str,
        incremental: bool = True
    ) -> Dict[str, Any]:
        """
        Index documents into vector store and PostgreSQL.

        Args:
            documents: List of BaseDocument
            datasource_id: Datasource ID for tracking
            incremental: If True, skip unchanged documents (default: True)

        Returns:
            Statistics dict with counts and timings
        """
        if not documents:
            logger.warning("no_documents_to_index")
            return {
                "document_count": 0,
                "chunk_count": 0,
                "skipped_count": 0,
                "indexed_count": 0
            }

        logger.info("starting_indexing", document_count=len(documents), incremental=incremental)

        start_time = datetime.utcnow()
        total_chunks = 0
        skipped_count = 0
        indexed_count = 0

        try:
            for document in documents:
                try:
                    # Check if document needs reindexing (incremental sync)
                    if incremental:
                        existing_doc = await self.document_store.get_document(
                            document.id,
                            datasource_id
                        )

                        if existing_doc and existing_doc.content_hash == document.content_hash:
                            logger.debug(
                                "document_unchanged_skipping",
                                document_id=document.id,
                                title=document.title
                            )
                            skipped_count += 1
                            continue

                    # 1. Chunk document
                    chunks = self.chunker.chunk_document(document)
                    if not chunks:
                        logger.warning("no_chunks_created", document_id=document.id)
                        continue

                    # 2. Embed chunks
                    texts = [chunk.content for chunk in chunks]
                    embeddings = self.embedder.embed_texts(texts)

                    # 3. Delete old chunks (if exists)
                    try:
                        self.vector_store.delete_by_document(document.id)
                        await self.document_store.delete_chunks_by_document(
                            document.id,
                            datasource_id
                        )
                    except Exception as e:
                        logger.warning("old_chunks_deletion_failed", error=str(e))

                    # 4. Upsert to vector store
                    self.vector_store.upsert(
                        chunks=chunks,
                        embeddings=embeddings
                    )

                    # 5. Save to PostgreSQL
                    document.datasource_id = datasource_id
                    document.indexed_at = datetime.utcnow()
                    document.chunk_count = len(chunks)

                    await self.document_store.save_document(document)
                    await self.document_store.save_chunks(chunks, datasource_id)

                    total_chunks += len(chunks)
                    indexed_count += 1

                    logger.info(
                        "document_indexed",
                        document_id=document.id,
                        title=document.title,
                        chunk_count=len(chunks)
                    )

                except Exception as e:
                    logger.error(
                        "document_indexing_failed",
                        document_id=document.id,
                        error=str(e)
                    )
                    continue

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            stats = {
                "document_count": len(documents),
                "indexed_count": indexed_count,
                "skipped_count": skipped_count,
                "chunk_count": total_chunks,
                "duration_seconds": duration,
                "chunks_per_second": total_chunks / duration if duration > 0 else 0
            }

            logger.info("indexing_completed", **stats)
            return stats

        except Exception as e:
            logger.error("indexing_failed", error=str(e))
            raise

    async def delete_document(self, document_id: str, datasource_id: str):
        """
        Delete document from vector store and PostgreSQL.

        Args:
            document_id: Document ID
            datasource_id: Datasource ID
        """
        logger.info("deleting_document", document_id=document_id)

        try:
            # Delete from vector store
            self.vector_store.delete_by_document(document_id)

            # Delete from PostgreSQL
            await self.document_store.delete_chunks_by_document(document_id, datasource_id)
            await self.document_store.delete_document(document_id, datasource_id)

            logger.info("document_deleted", document_id=document_id)

        except Exception as e:
            logger.error("document_deletion_failed", document_id=document_id, error=str(e))
            raise
