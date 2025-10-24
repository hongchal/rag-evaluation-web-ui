"""Base Retriever for semantic search."""

from typing import Dict, List, Optional, Set

import structlog
from app.models.query import SearchResult

logger = structlog.get_logger(__name__)


class BaseRetriever:
    """
    Base Retriever for semantic search.

    Uses embedder and vector store for retrieval.
    Supports adjacent chunk expansion for better context.
    """

    def __init__(self, embedder, vector_store):
        """
        Initialize retriever.

        Args:
            embedder: Embedder instance
            vector_store: Vector store instance
        """
        self.embedder = embedder
        self.vector_store = vector_store

        logger.info("base_retriever_initialized")

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        datasource_id: Optional[str] = None,
        datasource_ids: Optional[list] = None,
        expand_adjacent: Optional[bool] = None,
        adjacent_window: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Retrieve relevant chunks with optional adjacent expansion (backup style).

        Args:
            query: Query string
            top_k: Number of results (default: from settings)
            datasource_id: Filter by datasource ID
            datasource_ids: Filter by multiple datasource IDs
            expand_adjacent: Expand with adjacent chunks (default: from settings)
            adjacent_window: Window size for neighbors (default: from settings)

        Returns:
            List of SearchResult
        """
        from app.config import settings

        # Use settings if not provided
        if top_k is None:
            top_k = settings.top_k
        if expand_adjacent is None:
            expand_adjacent = settings.expand_adjacent_chunks
        if adjacent_window is None:
            adjacent_window = settings.adjacent_window

        logger.info("retrieving", query_length=len(query), top_k=top_k, expand_adjacent=expand_adjacent)

        try:
            # 1. Embed query
            query_embedding = self.embedder.embed_query(query)

            # 2. Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                datasource_id=datasource_id,
                datasource_ids=datasource_ids
            )

            # 3. Expand with adjacent chunks if enabled (backup style)
            if expand_adjacent and adjacent_window > 0:
                results = self._expand_with_neighbors(results, adjacent_window)

            logger.info("retrieval_completed", result_count=len(results))
            return results

        except Exception as e:
            logger.error("retrieval_failed", error=str(e))
            raise

    def _expand_with_neighbors(
        self,
        results: List[SearchResult],
        window: int
    ) -> List[SearchResult]:
        """
        Expand search results with adjacent chunks from same documents (backup style).

        Args:
            results: Initial search results
            window: Number of chunks to fetch on each side

        Returns:
            Expanded list of SearchResult
        """
        if not results or window <= 0:
            return results

        expanded = []
        seen_chunks: Set[str] = set()

        # Collect unique documents and their hit positions
        doc_to_positions: Dict[str, List[int]] = {}
        for result in results:
            if result.document_id and result.metadata.get("position") is not None:
                pos = int(result.metadata["position"])
                doc_to_positions.setdefault(result.document_id, []).append(pos)

        # For each hit, fetch neighbors
        for result in results:
            # Add original hit
            if result.chunk_id not in seen_chunks:
                expanded.append(result)
                seen_chunks.add(result.chunk_id)

            # Fetch and add neighbors
            if result.document_id and result.metadata.get("position") is not None:
                try:
                    neighbors = self.vector_store.get_neighbors(
                        document_id=result.document_id,
                        center_position=int(result.metadata["position"]),
                        window=window
                    )

                    for neighbor in neighbors:
                        chunk_id = f"{result.document_id}_pos_{neighbor.get('position')}"
                        if chunk_id in seen_chunks:
                            continue

                        # Create SearchResult for neighbor
                        neighbor_result = SearchResult(
                            chunk_id=chunk_id,
                            document_id=result.document_id,
                            score=result.score * 0.8,  # Lower score for neighbors
                            content=neighbor.get("content", ""),
                            metadata={
                                "title": neighbor.get("title", result.metadata.get("title", "")),
                                "path": neighbor.get("path", result.metadata.get("path", "")),
                                "url": neighbor.get("url", result.metadata.get("url", "")),
                                "datasource_id": neighbor.get("datasource_id", result.metadata.get("datasource_id", "")),
                                "position": neighbor.get("position"),
                                "token_count": neighbor.get("token_count"),
                            }
                        )
                        expanded.append(neighbor_result)
                        seen_chunks.add(chunk_id)

                except Exception as e:
                    logger.debug("failed_to_fetch_neighbors", document_id=result.document_id, error=str(e))
                    continue

        logger.info("expansion_completed", original=len(results), expanded=len(expanded))
        return expanded

