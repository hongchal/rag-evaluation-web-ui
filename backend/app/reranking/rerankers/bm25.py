from __future__ import annotations

from typing import List

from rank_bm25 import BM25Okapi

from .base_reranker import BaseReranker, RetrievedDocument


class BM25Reranker(BaseReranker):
    """키워드 기반 BM25 리랭커."""

    def __init__(self):
        self._last_corpus = None
        self._last_bm25: BM25Okapi | None = None

    def _build(self, documents: List[RetrievedDocument]) -> BM25Okapi:
        corpus = [d.content for d in documents]
        if self._last_corpus == corpus and self._last_bm25 is not None:
            return self._last_bm25
        tokenized = [doc.split() for doc in corpus]
        bm25 = BM25Okapi(tokenized)
        self._last_corpus = corpus
        self._last_bm25 = bm25
        return bm25

    def rerank(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: int | None = None,
    ) -> List[RetrievedDocument]:
        if not documents:
            return documents
        bm25 = self._build(documents)
        scores = bm25.get_scores(query.split())
        reranked = [
            RetrievedDocument(id=doc.id, content=doc.content, score=float(score), metadata=doc.metadata)
            for doc, score in zip(documents, scores)
        ]
        reranked.sort(key=lambda d: d.score, reverse=True)
        if top_k is None:
            return reranked
        return reranked[:top_k]
