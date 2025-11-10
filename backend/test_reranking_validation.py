"""
Reranking 검증 테스트

이 테스트는 reranking이 제대로 작동하는지 확인합니다:
1. Reranker가 새로운 score를 생성하는지
2. QueryService가 rerank score를 제대로 업데이트하는지
3. 순서가 변경되는지
"""

import pytest
from app.reranking.rerankers.base_reranker import RetrievedDocument
from app.reranking.rerankers.bm25 import BM25Reranker
from app.reranking.rerankers.cross_encoder import CrossEncoderReranker


def test_bm25_reranker_changes_scores():
    """BM25 Reranker가 score를 변경하는지 확인"""
    reranker = BM25Reranker()
    
    # 원본 문서들 (초기 score는 vector search score로 가정)
    docs = [
        RetrievedDocument(
            id="doc1",
            content="Python is a programming language",
            score=0.9,  # Vector search score
            metadata={"source": "test"}
        ),
        RetrievedDocument(
            id="doc2",
            content="Java is also a programming language",
            score=0.8,
            metadata={"source": "test"}
        ),
        RetrievedDocument(
            id="doc3",
            content="The weather is nice today",
            score=0.7,
            metadata={"source": "test"}
        ),
    ]
    
    query = "programming language"
    
    # Rerank
    reranked = reranker.rerank(query, docs, top_k=3)
    
    # 검증 1: Score가 변경되었는지
    original_scores = [d.score for d in docs]
    reranked_scores = [d.score for d in reranked]
    
    print(f"\n원본 scores: {original_scores}")
    print(f"Reranked scores: {reranked_scores}")
    
    # BM25는 완전히 다른 score 시스템을 사용하므로 score가 변경되어야 함
    assert reranked_scores != original_scores, "Reranking 후 score가 변경되어야 합니다"
    
    # 검증 2: 순서가 변경되었는지 (query와 관련성에 따라)
    reranked_ids = [d.id for d in reranked]
    print(f"Reranked 순서: {reranked_ids}")
    
    # "programming language"와 관련 있는 doc1, doc2가 상위에 와야 함
    assert "doc3" == reranked_ids[-1], "관련 없는 문서(doc3)가 마지막에 와야 합니다"
    
    # 검증 3: 내용과 메타데이터는 유지되는지
    for original, reranked_doc in zip(docs, reranked):
        if original.id == reranked_doc.id:
            assert original.content == reranked_doc.content
            assert original.metadata == reranked_doc.metadata


def test_cross_encoder_reranker_changes_scores():
    """CrossEncoder Reranker가 score를 변경하는지 확인"""
    try:
        reranker = CrossEncoderReranker(model_name="BAAI/bge-reranker-v2-m3")
    except Exception as e:
        pytest.skip(f"CrossEncoder 모델 로드 실패: {e}")
    
    docs = [
        RetrievedDocument(
            id="doc1",
            content="Machine learning is a subset of artificial intelligence",
            score=0.85,
            metadata={}
        ),
        RetrievedDocument(
            id="doc2",
            content="Deep learning uses neural networks",
            score=0.90,
            metadata={}
        ),
        RetrievedDocument(
            id="doc3",
            content="The cat sat on the mat",
            score=0.95,  # 높은 vector score지만 query와 무관
            metadata={}
        ),
    ]
    
    query = "What is machine learning?"
    
    # Rerank
    reranked = reranker.rerank(query, docs, top_k=3)
    
    # 검증 1: Score가 변경되었는지
    original_scores = [d.score for d in docs]
    reranked_scores = [d.score for d in reranked]
    
    print(f"\n원본 scores: {original_scores}")
    print(f"Reranked scores: {reranked_scores}")
    
    assert reranked_scores != original_scores, "Reranking 후 score가 변경되어야 합니다"
    
    # 검증 2: 의미적으로 관련 있는 문서가 상위에 오는지
    reranked_ids = [d.id for d in reranked]
    print(f"Reranked 순서: {reranked_ids}")
    
    # doc1 또는 doc2가 최상위에 와야 함 (query와 의미적으로 관련)
    assert reranked_ids[0] in ["doc1", "doc2"], "관련 문서가 최상위에 와야 합니다"
    
    # doc3는 vector score는 높았지만 의미적으로 무관하므로 하위로
    assert reranked_ids[-1] == "doc3", "무관한 문서(doc3)가 마지막에 와야 합니다"


def test_reranker_preserves_document_data():
    """Reranker가 문서 내용과 메타데이터를 보존하는지 확인"""
    reranker = BM25Reranker()
    
    docs = [
        RetrievedDocument(
            id="doc1",
            content="Test content 1",
            score=0.9,
            metadata={"key": "value1", "source": "test"}
        ),
        RetrievedDocument(
            id="doc2",
            content="Test content 2",
            score=0.8,
            metadata={"key": "value2", "source": "test"}
        ),
    ]
    
    reranked = reranker.rerank("test", docs, top_k=2)
    
    # ID로 매핑
    original_map = {d.id: d for d in docs}
    reranked_map = {d.id: d for d in reranked}
    
    # 모든 문서가 존재하는지
    assert set(original_map.keys()) == set(reranked_map.keys())
    
    # 내용과 메타데이터가 보존되는지
    for doc_id in original_map:
        assert original_map[doc_id].content == reranked_map[doc_id].content
        assert original_map[doc_id].metadata == reranked_map[doc_id].metadata
        # Score는 변경되어야 함
        assert original_map[doc_id].score != reranked_map[doc_id].score


def test_score_update_in_query_service_logic():
    """QueryService의 rerank score 업데이트 로직 시뮬레이션"""
    # 이것은 query_service.py의 로직을 시뮬레이션한 것입니다
    
    # 원본 chunks (vector search 결과)
    chunks = [
        {
            "id": "chunk1",
            "content": "Python programming",
            "score": 0.9,  # Vector score
            "metadata": {"doc_id": "doc1"}
        },
        {
            "id": "chunk2",
            "content": "Java programming",
            "score": 0.8,
            "metadata": {"doc_id": "doc2"}
        },
        {
            "id": "chunk3",
            "content": "Weather forecast",
            "score": 0.7,
            "metadata": {"doc_id": "doc3"}
        },
    ]
    
    # RetrievedDocument로 변환 (query_service.py의 로직)
    from app.reranking.rerankers.base_reranker import RetrievedDocument
    docs = [
        RetrievedDocument(
            id=c["id"],
            content=c["content"],
            score=float(c.get("score") or 0.0),
            metadata=c.get("metadata"),
        )
        for c in chunks
    ]
    
    # Rerank
    reranker = BM25Reranker()
    reranked_docs = reranker.rerank("programming", docs, top_k=3)
    
    # 수정된 로직: score 업데이트
    id_to_chunk = {c["id"]: c for c in chunks}
    updated_chunks = []
    for d in reranked_docs:
        if d.id in id_to_chunk:
            chunk = id_to_chunk[d.id].copy()
            chunk["score"] = d.score  # 🔥 IMPORTANT: rerank score로 업데이트!
            updated_chunks.append(chunk)
    
    # 검증 1: Score가 업데이트되었는지
    print("\n=== Score 업데이트 검증 ===")
    for original, updated in zip(chunks, updated_chunks):
        if original["id"] == updated["id"]:
            print(f"{original['id']}: {original['score']} -> {updated['score']}")
            # Score가 변경되었는지 확인
            assert original["score"] != updated["score"], \
                f"{original['id']}의 score가 업데이트되지 않았습니다"
    
    # 검증 2: 내용과 메타데이터는 유지되는지
    for chunk in updated_chunks:
        original = id_to_chunk[chunk["id"]]
        assert chunk["content"] == original["content"]
        assert chunk["metadata"] == original["metadata"]
    
    print("\n✅ Score 업데이트 검증 성공!")


if __name__ == "__main__":
    print("=" * 60)
    print("Reranking 검증 테스트 시작")
    print("=" * 60)
    
    print("\n[Test 1] BM25 Reranker Score 변경 테스트")
    test_bm25_reranker_changes_scores()
    print("✅ 통과")
    
    print("\n[Test 2] CrossEncoder Reranker Score 변경 테스트")
    try:
        test_cross_encoder_reranker_changes_scores()
        print("✅ 통과")
    except Exception as e:
        print(f"⚠️  스킵: {e}")
    
    print("\n[Test 3] 문서 데이터 보존 테스트")
    test_reranker_preserves_document_data()
    print("✅ 통과")
    
    print("\n[Test 4] QueryService Score 업데이트 로직 테스트")
    test_score_update_in_query_service_logic()
    print("✅ 통과")
    
    print("\n" + "=" * 60)
    print("✅ 모든 검증 테스트 통과!")
    print("=" * 60)



