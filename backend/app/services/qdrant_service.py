"""Qdrant vector store service."""

from typing import Optional

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings

logger = structlog.get_logger(__name__)


class QdrantService:
    """Service for managing Qdrant vector store."""

    def __init__(self):
        """Initialize Qdrant client."""
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        logger.info("qdrant_client_initialized", url=settings.qdrant_url)

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1024,
        distance: Distance = Distance.COSINE,
    ) -> None:
        """Create a new collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection_name in collection_names:
                logger.info("collection_exists", collection=collection_name)
                return

            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                ),
            )
            logger.info("collection_created", collection=collection_name)
        except Exception as e:
            logger.error(
                "collection_creation_failed",
                collection=collection_name,
                error=str(e),
            )
            raise

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection."""
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info("collection_deleted", collection=collection_name)
        except Exception as e:
            logger.error(
                "collection_deletion_failed",
                collection=collection_name,
                error=str(e),
            )
            raise

    def upsert_vectors(
        self,
        collection_name: str,
        vectors: list[list[float]],
        payloads: list[dict],
        ids: Optional[list[int]] = None,
    ) -> None:
        """Upsert vectors into collection."""
        try:
            if ids is None:
                ids = list(range(len(vectors)))

            points = [
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
                for point_id, vector, payload in zip(ids, vectors, payloads)
            ]

            self.client.upsert(
                collection_name=collection_name,
                points=points,
            )
            logger.info(
                "vectors_upserted",
                collection=collection_name,
                count=len(vectors),
            )
        except Exception as e:
            logger.error(
                "vector_upsert_failed",
                collection=collection_name,
                error=str(e),
            )
            raise

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
    ) -> list[dict]:
        """Search for similar vectors."""
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
            )

            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(
                "search_failed",
                collection=collection_name,
                error=str(e),
            )
            raise
