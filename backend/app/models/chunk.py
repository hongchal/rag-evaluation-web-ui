"""
Chunk Model

청크 정보를 데이터베이스에 저장하는 모델
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Index, BigInteger
from sqlalchemy.orm import relationship

from app.core.database import Base


class Chunk(Base):
    """
    Chunk: 문서를 청킹한 결과
    
    Pipeline 생성 시 생성되며, 검색 결과 추적 및 디버깅에 사용
    """
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    
    # 관계
    pipeline_id = Column(
        Integer,
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    document_id = Column(Integer, nullable=True, index=True)  # Document ID (from datasource or dataset)
    
    # 청크 정보
    chunk_index = Column(Integer, nullable=False)  # 문서 내 청크 순서
    content = Column(Text, nullable=False)  # 청크 내용
    
    # 메타데이터
    metadata = Column(JSON, nullable=True)  # 파일명, 페이지 번호, 라인 번호 등
    
    # 벡터 ID (Qdrant point ID와 매핑)
    vector_id = Column(BigInteger, nullable=True, index=True)
    
    # 통계
    token_count = Column(Integer, nullable=True)  # 토큰 수
    char_count = Column(Integer, nullable=True)   # 문자 수
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 인덱스
    __table_args__ = (
        Index('ix_chunks_pipeline_document', 'pipeline_id', 'document_id'),
        Index('ix_chunks_pipeline_vector', 'pipeline_id', 'vector_id'),
    )

    def __repr__(self):
        return (
            f"<Chunk(id={self.id}, pipeline_id={self.pipeline_id}, "
            f"chunk_index={self.chunk_index}, length={len(self.content) if self.content else 0})>"
        )

    @property
    def preview(self) -> str:
        """청크 내용 미리보기 (처음 100자)"""
        if not self.content:
            return ""
        return self.content[:100] + ("..." if len(self.content) > 100 else "")

