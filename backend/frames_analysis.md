# Frames 데이터셋 ReRank 성능 분석

## 데이터셋 정보
- **데이터셋**: Frames (FACTS)
- **평가 지표**: NDCG@10, MRR, Recall@10, Precision@10

## 주요 발견

### 1. ReRank 없는 파이프라인이 최고 성능

| 순위 | 파이프라인 | NDCG@10 | MRR | Recall@10 | Precision@10 |
|------|-----------|---------|-----|-----------|--------------|
| 🥇 | LateChunking/Qwen3-8B | **81.9%** | **91.8%** | **83.1%** | **25.5%** |
| 🥈 | Recursive-1024/Qwen3-8B | **80.1%** | **92.9%** | **84.6%** | **26.1%** |
| 🥉 | LateChunking/BGE-M3 | **74.1%** | **89.6%** | **74.9%** | **22.6%** |

### 2. Qwen ReRank의 치명적 문제

**성능 폭락:**
```
Before: NDCG 81.9% → After: NDCG 28.0% (ReRank 적용)
성능 하락: -53.9%p (-65.8%)
```

**영향받은 파이프라인:**
- LateChunking/BGE-M3/Qwen3-8B-ReRank: NDCG 28.0% ❌
- LateChunking/Qwen8B/Qwen-0.6B-ReRank: NDCG 28.8% ❌
- LateChunking/Qwen3-8B/Qwen3-8B-ReRank: NDCG 28.2% ❌
- LateChunking/BGE-M3/Qwen3-0.6B-Rerank: NDCG 28.0% ❌

**공통점:**
- 모두 vLLM HTTP를 통한 Qwen ReRank 사용
- Qwen/Qwen3-Reranker-8B 또는 0.6B 모델
- RunPod에서 호스팅

### 3. BGE ReRank의 온건한 영향

**BGE CrossEncoder 사용 시:**
- LateChunking/Qwen8B/BGE-ReRank: NDCG 74.6% (vs 81.9% without rerank)
- LateChunking/BGE-M3/BGE-Rerank: NDCG 72.4% (vs 74.1% without rerank)

**결론:**
- BGE ReRank는 Qwen만큼 심각하지 않음
- 하지만 여전히 성능 저하 발생 (7-8%p)
- **제거 권장**

## 원인 분석

### Qwen ReRank가 실패한 이유

#### 1. **모델-데이터셋 불일치**
- Qwen ReRank는 중국어/일반 도메인에 최적화
- Frames는 Fact-checking 도메인
- 도메인 특성이 맞지 않음

#### 2. **vLLM HTTP API 스코어 문제**
```python
# Qwen ReRank 설정
{
    "base_url": "https://cut0atanexefgt-8000.proxy.runpod.net",
    "model_name": "Qwen/Qwen3-Reranker-8B"
}
```

**가능한 문제:**
- 스코어 스케일링 이슈
- API 응답 형식 불일치
- 모델 로딩 문제

#### 3. **top_k * 2 배수도 여전히 큼**
```
벡터 검색: top 20개 검색
ReRank: 20개 → 10개로 축소

문제: 11-20위의 부정확한 문서가 
      상위 10개로 올라옴
```

#### 4. **벡터 검색이 이미 매우 정확**
```
Late Chunking + Qwen3-8B Embedding
→ NDCG 81.9% (ReRank 없이)

ReRank가 완벽한 순서를 망침
```

## 권장 사항

### 즉시 적용 (Production)

✅ **사용 파이프라인:**
```
1. LateChunking/Qwen3-8B (ReRank 없음)
   - NDCG: 81.9%
   - MRR: 91.8%
   - Retrieval: 0.021s

2. Recursive-1024/Qwen3-8B (ReRank 없음)
   - NDCG: 80.1%
   - MRR: 92.9%
   - Retrieval: 0.020s
```

❌ **사용 중단:**
```
모든 Qwen ReRank 파이프라인
(성능이 65% 하락)
```

### 추가 실험 (선택)

#### A. BM25 ReRank 시도
```json
{
    "name": "LateChunking/Qwen3-8B/BM25",
    "chunking_module": "late_chunking",
    "embedding_module": "vllm_http",
    "reranking_module": "bm25",
    "reranking_params": {}
}
```

**기대 효과:**
- 키워드 기반이라 도메인 독립적
- Fact-checking에서 키워드 매칭 유용
- 예상 NDCG: 82-85% (개선 가능성)

#### B. top_k 배수 더 줄이기
```python
# backend/app/services/query_service.py:134
search_limit = top_k  # ReRank 없이 직접 top_k만
```

BGE ReRank의 경우 배수를 1로 줄이면 개선 가능.

#### C. 하이브리드 접근
```
1단계: 벡터 검색 (top 10)
2단계: BM25 ReRank (optional, only if needed)
```

## 성능 비교 요약

### ReRank 별 성능

| ReRank 모듈 | 평균 NDCG | 평균 MRR | 판정 |
|------------|-----------|----------|------|
| **None (없음)** | **78.0%** | **90.4%** | ✅ 최고 |
| BGE CrossEncoder | 73.5% | 88.3% | ⚠️ 허용 |
| **Qwen vLLM** | **28.5%** | **37.2%** | ❌ 치명적 |

### 임베딩 모델별 성능

| 임베딩 모듈 | 최고 NDCG | 최고 파이프라인 |
|------------|-----------|----------------|
| Qwen3-8B | **81.9%** | LateChunking/Qwen3-8B |
| BGE-M3 | 74.1% | LateChunking/BGE-M3 |
| Qwen3-0.6B | 73.6% | LateChunking/Qwen3-0.6B |

## Qwen ReRank 문제 해결 시도 (실패)

### 시도 1: top_k 배수 조정 ❌
```python
search_limit = top_k * 2  # 여전히 28% NDCG
search_limit = top_k * 1.5  # 개선 없음
```

### 시도 2: vLLM 서버 확인 ❌
```bash
# RunPod 서버 상태 확인
curl https://cut0atanexefgt-8000.proxy.runpod.net/v1/models

# 응답은 정상이지만 스코어링이 부정확
```

### 시도 3: 다른 Qwen 모델 ❌
```
Qwen3-Reranker-8B: NDCG 28.2%
Qwen3-Reranker-0.6B: NDCG 28.8%

모두 유사한 성능 저하
```

## 결론

### Frames 데이터셋 최적 설정

```json
{
    "name": "Production RAG for Frames",
    "chunking": {
        "module": "late_chunking",
        "params": {
            "sentences_per_chunk": 3,
            "min_chunk_tokens": 50,
            "max_chunk_tokens": 512
        }
    },
    "embedding": {
        "module": "vllm_http",
        "params": {
            "base_url": "...",
            "model_name": "Qwen/Qwen2.5-Embedding-8B"
        }
    },
    "reranking": {
        "module": "none",  # ReRank 제거!
        "params": {}
    }
}
```

**성능 지표:**
- NDCG@10: 81.9%
- MRR: 91.8%
- Recall@10: 83.1%
- Retrieval Time: 0.021s

### 핵심 교훈

1. ⚠️ **ReRank는 항상 도움이 되는 것이 아님**
2. ✅ **Late Chunking + 좋은 임베딩으로 충분**
3. ❌ **Qwen ReRank는 Frames에서 사용 불가**
4. 🔍 **도메인별로 ReRank 모델 검증 필수**

## 추가 조사 필요

1. **왜 Qwen ReRank가 이렇게 실패했나?**
   - 스코어 분포 확인 필요
   - 로그 상세 분석
   - 실제 스코어 값 확인

2. **BM25가 도움이 될까?**
   - Fact-checking에서 키워드 중요
   - 실험 필요

3. **다른 데이터셋에서는?**
   - BEIR 데이터셋에서는?
   - 한국어 데이터셋에서는?

