from __future__ import annotations

from typing import List

from sentence_transformers import CrossEncoder

from .base_reranker import BaseReranker, RetrievedDocument


class CrossEncoderReranker(BaseReranker):
    """BAAI/bge-reranker-v2-m3를 사용하는 CrossEncoder 리랭커."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str | None = None):
        self.model = CrossEncoder(model_name, device=device)

    def rerank(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: int | None = None,
    ) -> List[RetrievedDocument]:
        if not documents:
            return documents

        pairs = [(query, d.content) for d in documents]
        scores = self.model.predict(pairs)
        reranked = [
            RetrievedDocument(id=doc.id, content=doc.content, score=float(score), metadata=doc.metadata)
            for doc, score in zip(documents, scores)
        ]
        reranked.sort(key=lambda d: d.score, reverse=True)
        if top_k is None:
            return reranked
        return reranked[:top_k]
