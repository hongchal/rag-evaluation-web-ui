from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Protocol, Any


@dataclass
class RetrievedDocument:
    id: Any
    content: str
    score: float
    metadata: dict | None = None


class BaseReranker(ABC):
    """리랭커 기본 인터페이스."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: int | None = None,
    ) -> List[RetrievedDocument]:
        """query와 documents를 받아 재순위화된 리스트를 반환한다."""
        raise NotImplementedError
