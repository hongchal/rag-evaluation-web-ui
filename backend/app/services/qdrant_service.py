"""Qdrant vector store service."""

from typing import Optional, List, Dict, Any

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchAny,
    MatchValue,
    SparseVector,
    SparseVectorParams,
    SparseIndexParams,
)

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
        enable_hybrid: bool = False,
    ) -> None:
        """Create a new collection if it doesn't exist.
        
        Args:
            collection_name: Name of the collection
            vector_size: Size of dense vectors
            distance: Distance metric for dense vectors
            enable_hybrid: If True, enable hybrid search (dense + sparse)
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection_name in collection_names:
                logger.info("collection_exists", collection=collection_name)
                return

            # Create collection with hybrid search support
            if enable_hybrid:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config={
                        "dense": VectorParams(
                            size=vector_size,
                            distance=distance,
                        ),
                    },
                    sparse_vectors_config={
                        "sparse": SparseVectorParams(
                            index=SparseIndexParams(),
                        ),
                    },
                )
                logger.info("hybrid_collection_created", collection=collection_name)
            else:
                # Standard dense-only collection
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

    def collection_exists(self, collection_name: str) -> bool:
        """Return True if collection exists."""
        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception as e:
            logger.error("collection_exists_check_failed", collection=collection_name, error=str(e))
            return False

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
        sparse_vectors: Optional[list[dict]] = None,
    ) -> None:
        """Upsert vectors into collection.
        
        Args:
            collection_name: Name of the collection
            vectors: Dense vectors
            payloads: Metadata for each vector
            ids: Optional IDs for vectors
            sparse_vectors: Optional sparse vectors for hybrid search
                Format: [{"indices": [1, 2, 3], "values": [0.5, 0.3, 0.2]}, ...]
        """
        try:
            if ids is None:
                ids = list(range(len(vectors)))

            # Build points with hybrid vectors if provided
            if sparse_vectors:
                points = [
                    PointStruct(
                        id=point_id,
                        vector={
                            "dense": vector,
                            "sparse": SparseVector(
                                indices=sparse["indices"],
                                values=sparse["values"],
                            ),
                        },
                        payload=payload,
                    )
                    for point_id, vector, sparse, payload in zip(
                        ids, vectors, sparse_vectors, payloads
                    )
                ]
            else:
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
                hybrid=sparse_vectors is not None,
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
        filter_conditions: Optional[dict] = None,
        query_sparse_vector: Optional[dict] = None,
        hybrid_fusion: str = "rrf",
    ) -> list[dict]:
        """Search for similar vectors with optional hybrid search.
        
        Args:
            collection_name: Name of the collection
            query_vector: Dense query vector
            top_k: Number of results to return
            filter_conditions: Optional filters
            query_sparse_vector: Optional sparse query vector for hybrid search
                Format: {"indices": [1, 2, 3], "values": [0.5, 0.3, 0.2]}
            hybrid_fusion: Fusion method for hybrid search ("rrf" or "dbsf")
        """
        try:
            query_filter = None
            if filter_conditions:
                must_conditions = []
                for key, cond in filter_conditions.items():
                    if isinstance(cond, dict) and "$in" in cond:
                        must_conditions.append(
                            FieldCondition(key=key, match=MatchAny(any=cond["$in"]))
                        )
                    else:
                        # equality match fallback
                        value = cond if not isinstance(cond, dict) else cond.get("$eq")
                        if value is not None:
                            must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
                if must_conditions:
                    query_filter = Filter(must=must_conditions)

            # Hybrid search if sparse vector provided
            if query_sparse_vector:
                from qdrant_client.models import Prefetch, Query, FusionQuery

                # Prefetch dense results
                dense_prefetch = Prefetch(
                    query=query_vector,
                    using="dense",
                    limit=top_k * 2,
                )

                # Prefetch sparse results
                sparse_prefetch = Prefetch(
                    query=SparseVector(
                        indices=query_sparse_vector["indices"],
                        values=query_sparse_vector["values"],
                    ),
                    using="sparse",
                    limit=top_k * 2,
                )

                # Fusion query
                results = self.client.query_points(
                    collection_name=collection_name,
                    prefetch=[dense_prefetch, sparse_prefetch],
                    query=FusionQuery(fusion=hybrid_fusion),
                    limit=top_k,
                    query_filter=query_filter,
                )
                
                return [
                    {
                        "id": hit.id,
                        "score": hit.score,
                        "payload": hit.payload,
                    }
                    for hit in results.points
                ]
            else:
                # Standard dense-only search
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                    query_filter=query_filter,
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

    def add_chunks(
        self,
        collection_name: str,
        chunks: list,
        embeddings: list[list[float]],
        payload_extra: Optional[dict] = None,
        vector_size: int = 1024,
        distance: Distance = Distance.COSINE,
        sparse_embeddings: Optional[list[dict]] = None,
        enable_hybrid: bool = False,
    ) -> None:
        """Create collection if needed and upsert chunk vectors with payloads.

        Args:
            collection_name: Name of the collection
            chunks: list of objects having attribute 'content' or dicts with 'content'
            embeddings: Dense embeddings
            payload_extra: merged into each payload (e.g., {"datasource_id": 1})
            vector_size: Size of dense vectors
            distance: Distance metric
            sparse_embeddings: Optional sparse embeddings for hybrid search
            enable_hybrid: If True, create hybrid collection
        """
        try:
            if not self.collection_exists(collection_name):
                self.create_collection(
                    collection_name,
                    vector_size=vector_size,
                    distance=distance,
                    enable_hybrid=enable_hybrid,
                )

            payloads: list[dict] = []
            for ch in chunks:
                content = None
                if isinstance(ch, dict):
                    content = ch.get("content")
                else:
                    content = getattr(ch, "content", None)
                if content is None:
                    content = str(ch)
                p = {"content": content}
                if payload_extra:
                    p.update(payload_extra)
                payloads.append(p)

            self.upsert_vectors(
                collection_name=collection_name,
                vectors=embeddings,
                payloads=payloads,
                sparse_vectors=sparse_embeddings,
            )
        except Exception as e:
            logger.error("add_chunks_failed", collection=collection_name, error=str(e))
            raise
