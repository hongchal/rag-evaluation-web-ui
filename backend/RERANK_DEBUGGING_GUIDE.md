# ReRank 성능 디버깅 가이드

ReRank를 사용했을 때 성능이 떨어지는 문제를 진단하고 해결하는 방법입니다.

## 문제 증상

- ReRank 없는 파이프라인: NDCG@10 = 0.75
- ReRank 있는 파이프라인: NDCG@10 = 0.65
- **ReRank를 사용했는데 오히려 성능이 떨어짐**

## 진단 단계

### 1단계: 백엔드 재시작

변경사항을 적용하려면 백엔드를 재시작해야 합니다:

```bash
# Docker Compose 사용 시
docker-compose restart backend

# 로컬 실행 시
# 프로세스를 종료하고 다시 시작
```

### 2단계: 평가 실행 및 로그 수집

```bash
# 1. 웹 UI에서 평가 실행
#    - ReRank 있는 파이프라인으로 테스트
#    - 예: Pipeline ID 77, 78, 79, 80 등

# 2. 로그 수집
docker-compose logs backend > backend_logs.txt
```

### 3단계: 로그 분석

```bash
cd backend
python3 analyze_rerank_performance.py backend_logs.txt
```

출력 예시:
```
================================================================================
ReRank 성능 분석
================================================================================

[1] 로그 파일 분석 중: backend_logs.txt
✓ 50개의 ReRank 로그 발견

[2] ReRank 영향 분석
--------------------------------------------------------------------------------
총 쿼리 수: 50
순서가 변경된 쿼리: 45 (90.0%)

순위 상승 문서: 120개
순위 하락 문서: 180개  # ← 문제!

최대 순위 하락: frames_q0_doc5
  2위 → 8위 (-6)  # ← 관련 문서가 밀려남

[3] 쿼리별 상세 분석 (처음 5개)
...

[5] 권장사항
--------------------------------------------------------------------------------
⚠️  순위 하락 문서가 더 많습니다
   → ReRank가 오히려 성능을 저하시킬 수 있습니다
   → 다른 ReRank 모델을 시도하거나 top_k 배수를 조정하세요
```

## 원인 분석

### 원인 1: top_k 배수가 너무 큼 (해결됨)

**문제:**
```python
# ReRank 없음: top 10개 검색
# ReRank 있음: top 40개 검색 → ReRank → top 10개
```

**해결:**
- `top_k * 4` → `top_k * 2`로 축소 완료
- 40개 중에서 고르면 노이즈가 많음
- 20개 중에서 고르면 더 정확

### 원인 2: ReRank 모델과 데이터셋 불일치

**BGE Reranker:**
- 학습 데이터: MS MARCO, NQ 등 (주로 영어)
- 한국어 데이터셋에서는 성능이 떨어질 수 있음

**Qwen Reranker:**
- 다국어 지원하지만 특정 도메인에서는 부정확

**해결:**
- BM25 시도: 키워드 기반이라 언어 독립적
- 데이터셋별로 다른 ReRank 모델 테스트

### 원인 3: 벡터 검색이 이미 정확함

**문제:**
- 벡터 검색 자체가 이미 매우 정확
- ReRank가 불필요한 변경을 가함
- 특히 late chunking + 좋은 임베딩 모델 사용 시

**해결:**
- ReRank 제거 고려
- 또는 매우 높은 threshold 설정

### 원인 4: ReRank 스코어 신뢰도 문제

**문제:**
- CrossEncoder가 짧은 쿼리/문서에서 부정확
- VLLM HTTP ReRank의 스코어 스케일 차이

**해결:**
- ReRank 파라미터 조정
- 다른 모델 시도

## 해결 방법

### 방법 1: BM25 ReRank 시도 (추천)

키워드 기반이라 언어 독립적이고 빠릅니다:

```python
# 웹 UI에서 새 RAG 생성
{
    "name": "LateChunking/BGE-M3/BM25",
    "reranking": {
        "module": "bm25",
        "params": {}
    }
}
```

### 방법 2: top_k 배수 조정

이미 2로 줄였지만, 더 실험해볼 수 있습니다:

```python
# backend/app/services/query_service.py:134
search_limit = top_k * 1.5  # 또는 top_k * 1
```

### 방법 3: ReRank 없이 테스트

벡터 검색만으로도 충분한지 확인:

```python
{
    "reranking_module": "none",
    "reranking_params": {}
}
```

### 방법 4: 다른 CrossEncoder 모델

```python
{
    "reranking_module": "cross_encoder",
    "reranking_params": {
        "model_name": "cross-encoder/ms-marco-MiniLM-L-12-v2"  # 더 큰 모델
    }
}
```

## 상세 로그 확인

특정 쿼리에서 무슨 일이 일어나는지 확인:

```bash
# ReRank 로그만 필터링
docker-compose logs backend | grep reranking_detailed

# 특정 파이프라인 로그
docker-compose logs backend | grep "pipeline_id=79"

# JSON 파싱하여 pretty print
docker-compose logs backend | grep reranking_detailed | python -m json.tool
```

## 체크리스트

- [ ] 백엔드 재시작 완료
- [ ] ReRank 사용 파이프라인으로 평가 실행
- [ ] 로그 수집 완료
- [ ] 분석 스크립트 실행
- [ ] 순위 변화 패턴 확인
- [ ] 원인 파악
- [ ] 해결 방법 적용
- [ ] 재평가 및 비교

## 예상 결과

### 개선 전
```
ReRank 없음: NDCG@10 = 0.75
BGE ReRank: NDCG@10 = 0.65  # 성능 저하
```

### 개선 후 (top_k * 2 + BM25)
```
ReRank 없음: NDCG@10 = 0.75
BM25 ReRank: NDCG@10 = 0.78  # 성능 향상!
```

## 추가 지원

문제가 해결되지 않으면:

1. **데이터셋 확인**: 어떤 데이터셋인지 (BEIR, FRAMES, 커스텀)
2. **쿼리 타입 확인**: 짧은 쿼리 vs 긴 쿼리
3. **문서 특성 확인**: 문서 길이, 도메인
4. **ReRank 모델별 성능 비교**: BGE vs Qwen vs BM25
5. **Ground Truth 검증**: 평가 데이터셋의 정답이 정확한지

## 참고

- 변경된 파일: `backend/app/services/query_service.py`
- 분석 스크립트: `backend/analyze_rerank_performance.py`
- ReRank 설정 확인: `python backend/check_rerank_status.py`

