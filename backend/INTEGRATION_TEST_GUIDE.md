# 통합 테스트 실행 가이드

## ✅ 완료된 작업

### 1. API 개발 완료
- **Pipeline API**: CRUD 완전 구현 ✓
- **Query API**: pipeline_id 기반 검색 ✓
- **Evaluation API**: pipeline_ids 기반 평가 ✓

### 2. 핵심 로직 구현
- 파이프라인별 데이터 격리 (pipeline_id payload) ✓
- 하이브리드 서치 활성화 (BGE-M3) ✓
- 자동 인덱싱 (파이프라인 생성 시) ✓
- TEST Pipeline 실시간 비교 ✓

### 3. 테스트 파일 생성
- `test_data/sample_document.txt` - RAG 시스템 개요 ✓
- `test_data/tech_trends.txt` - AI 기술 동향 보고서 ✓
- `test_data/products.json` - 상품 정보 JSON ✓

## 🚀 실행 방법

### 사전 요구사항

1. **Python 패키지 설치**
```bash
cd backend
pip install -r requirements.txt
```

필요한 추가 패키지:
```bash
pip install peft  # FlagEmbedding용
```

2. **Qdrant 서버 실행**
```bash
# 프로젝트 루트에서
docker-compose up -d qdrant
```

3. **PostgreSQL 실행**
```bash
docker-compose up -d postgres
```

4. **DB 마이그레이션**
```bash
cd backend
PYTHONPATH=$(pwd) python scripts/migrate_db.py
```

### 통합 테스트 실행

```bash
cd backend

# Qdrant URL 설정 (포트 6335 사용)
export QDRANT_URL=http://localhost:6335

# 통합 테스트 실행
python run_integration_test.py
```

## 📝 테스트 시나리오

### 시나리오 1: NORMAL Pipeline 생성 및 쿼리

1. **RAG Configuration 생성**
   - Chunking: recursive (512/50)
   - Embedding: bge_m3
   - Reranking: none

2. **DataSource 생성**
   - TXT 파일 2개
   - JSON 파일 1개

3. **Pipeline 생성**
   ```python
   POST /api/v1/pipelines
   {
     "name": "Test-Pipeline",
     "pipeline_type": "normal",
     "rag_id": 1,
     "datasource_ids": [1, 2, 3]
   }
   ```
   → 자동 인덱싱 실행 (청킹 + 임베딩 + Qdrant 업로드)

4. **쿼리 실행**
   ```python
   POST /api/v1/query/search
   {
     "query": "RAG 시스템이 무엇인가요?",
     "pipeline_id": 1,
     "top_k": 5
   }
   ```

### 시나리오 2: TEST Pipeline 및 평가

1. **EvaluationDataset 준비**
   - FRAMES dataset 또는 커스텀 dataset

2. **TEST Pipeline 생성**
   ```python
   POST /api/v1/pipelines
   {
     "name": "Test-Eval-Pipeline",
     "pipeline_type": "test",
     "rag_id": 1,
     "dataset_id": 1
   }
   ```

3. **Query with Comparison**
   ```python
   POST /api/v1/query/search
   {
     "query": "test query",
     "pipeline_id": 2,
     "top_k": 10
   }
   ```
   → Response에 comparison 메트릭 포함 (precision, recall, hit_rate)

4. **Evaluation 실행**
   ```python
   POST /api/v1/evaluations/run
   {
     "name": "Evaluation Test",
     "pipeline_ids": [2, 3, 4]
   }
   ```

### 시나리오 3: 파이프라인 비교

```python
POST /api/v1/evaluations/compare
{
  "pipeline_ids": [2, 3, 4]
}
```

## 🔍 검증 포인트

### 1. 파이프라인별 데이터 격리 확인

```python
# Pipeline 1 생성 (DataSource A)
# Pipeline 2 생성 (DataSource A) - 같은 데이터 소스

# Pipeline 1 삭제
DELETE /api/v1/pipelines/1

# Pipeline 2 쿼리 - 정상 작동해야 함!
POST /api/v1/query/search
{
  "query": "test",
  "pipeline_id": 2
}
```

→ Pipeline 1의 벡터만 삭제되고, Pipeline 2는 정상 작동해야 함

### 2. 하이브리드 서치 확인

Qdrant 컬렉션 확인:
```bash
curl http://localhost:6335/collections/collection_name
```

→ `sparse_vectors` named vector 존재 확인

### 3. TEST Pipeline 비교 메트릭 확인

```json
{
  "query": "test query",
  "pipeline_id": 2,
  "pipeline_type": "test",
  "results": [...],
  "comparison": {
    "query_id": 1,
    "query_text": "test query",
    "golden_doc_ids": ["doc1", "doc2"],
    "retrieved_doc_ids": ["doc1", "doc3"],
    "precision_at_k": 0.5,
    "recall_at_k": 0.5,
    "hit_rate": 1.0
  }
}
```

## 🎯 예상 결과

### 성공 케이스

1. **Pipeline 생성**: 3-10초 (파일 크기에 따라)
2. **Query 응답**: 0.5-2초
3. **Evaluation**: 쿼리 수에 비례 (10 queries ≈ 10-30초)

### 성능 메트릭 목표

- Precision@10: > 0.7
- Recall@10: > 0.6
- NDCG@10: > 0.75
- MRR: > 0.8

## 🐛 트러블슈팅

### 문제 1: `ModuleNotFoundError: No module named 'peft'`

**해결**:
```bash
pip install peft
```

### 문제 2: Qdrant 연결 실패

**확인**:
```bash
# Qdrant 포트 확인
docker ps | grep qdrant

# 6335 포트 사용 시
export QDRANT_URL=http://localhost:6335
```

### 문제 3: 임베딩 모델 다운로드 느림

**해결**: 첫 실행 시 HuggingFace에서 BGE-M3 모델 (약 2GB) 다운로드
- 이후 캐시 사용으로 빠름

### 문제 4: GPU/MPS 오류

**해결**:
```bash
# CPU 강제 사용
export EMBEDDING_DEVICE=cpu
```

## 📊 성능 모니터링

### Qdrant 대시보드
```
http://localhost:6335/dashboard
```

### 로그 확인
```bash
# Backend 로그
docker-compose logs -f backend

# Qdrant 로그
docker-compose logs -f qdrant
```

## 🎉 완료 확인

모든 테스트가 성공하면:

- [ ] Pipeline 생성 및 자동 인덱싱 동작
- [ ] Query 정상 응답 (검색 결과 반환)
- [ ] TEST Pipeline comparison 메트릭 출력
- [ ] Pipeline 삭제 후 다른 파이프라인 정상 동작
- [ ] Evaluation 실행 및 결과 저장

## 📚 참고 자료

- API 문서: `http://localhost:8001/docs` (서버 실행 후)
- 테스트 결과: `backend/TEST_SUMMARY.md`
- 데이터베이스 스키마: `backend/app/models/`
- API 엔드포인트: `backend/app/api/routes/`

## 다음 단계

1. ✅ API 로직 검증 완료
2. 🔄 통합 테스트 실행 (이 가이드)
3. ⏭️ Frontend 연동
4. ⏭️ 성능 최적화
5. ⏭️ 배포 준비

