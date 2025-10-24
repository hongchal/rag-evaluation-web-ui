from __future__ import annotations

from typing import List

from .base_reranker import BaseReranker, RetrievedDocument


class NoneReranker(BaseReranker):
    """순위를 변경하지 않는 패스스루 리랭커."""

    def rerank(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: int | None = None,
    ) -> List[RetrievedDocument]:
        if top_k is None:
            return documents
        return documents[:top_k]
