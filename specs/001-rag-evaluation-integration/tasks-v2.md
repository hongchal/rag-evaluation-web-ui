# Implementation Tasks v2 - RAG Evaluation System

## Overview
사용자의 5단계 플로우에 맞춘 구현 작업 목록:
1. RAG 생성 (청킹 + 임베딩 + 리랭킹)
2. 데이터 소스 추가
3. 데이터 동기화 (어떤 RAG가 처리했는지 기록)
4. RAG 성능 평가 (정량)
5. 검색/답변 생성 (정성)

## Task Phases

### Phase 1: Setup & Dependencies
필수 의존성 설치

- [X] **SETUP-1**: requirements.txt 업데이트
  - Files: `backend/requirements.txt`
  - Description: 
    - FlagEmbedding>=1.2.0 (BGE-M3)
    - anthropic>=0.18.0 (Claude)
    - ragas>=0.1.0
    - langchain-text-splitters>=0.0.1
    - langchain-anthropic
    - langchain-community
    - sentence-transformers (CrossEncoder)
    - rank-bm25 (BM25 reranker)
    - pandas, numpy
  - Dependencies: None

- [X] **SETUP-2**: Backend 디렉토리 구조 생성
  - Files: 디렉토리 생성
  - Description:
    - `backend/app/evaluation/`
    - `backend/app/chunking/`
    - `backend/app/embedding/`
    - `backend/app/reranking/` 🆕
    - `backend/app/pipeline/`
    - `backend/app/schemas/`
  - Dependencies: None

- [X] **SETUP-3**: 환경 변수 추가
  - Files: `backend/env.example`
  - Description:
    - ANTHROPIC_API_KEY
    - LLM_MODEL=claude-sonnet-4-20250514
  - Dependencies: None

### Phase 2: Evaluation System Migration
tkai-agents 코드 마이그레이션

- [X] **EVAL-1**: evaluation 모듈 복사 및 수정
  - Files: `backend/app/evaluation/`
  - Description:
    - `/Users/chohongcheol/tkai-agents/apps/rag/src/evaluation/` → `backend/app/evaluation/`
    - Import 경로 수정 (src.* → app.*)
  - Dependencies: SETUP-2

- [X] **EVAL-2**: chunking 모듈 복사 및 수정
  - Files: `backend/app/chunking/`
  - Description:
    - `/Users/chohongcheol/tkai-agents/apps/rag/src/chunking/` → `backend/app/chunking/`
    - Import 경로 수정
  - Dependencies: SETUP-2

- [X] **EVAL-3**: embedding 모듈 복사 및 수정
  - Files: `backend/app/embedding/`
  - Description:
    - `/Users/chohongcheol/tkai-agents/apps/rag/src/embedding/` → `backend/app/embedding/`
    - Import 경로 수정
  - Dependencies: SETUP-2

- [X] **EVAL-4**: pipeline 모듈 복사 및 수정
  - Files: `backend/app/pipeline/`
  - Description:
    - `/Users/chohongcheol/tkai-agents/apps/rag/src/pipeline/` → `backend/app/pipeline/`
    - QueryPipeline, ClaudeGenerator
  - Dependencies: SETUP-2

- [X] **EVAL-5**: Qdrant 서비스 확장
  - Files: `backend/app/services/qdrant_service.py`
  - Description:
    - Hybrid search 지원
    - Batch operations (add_chunks, get_by_ids)
    - Filter support (datasource_id)
  - Dependencies: None

### Phase 3: Reranking Module Implementation 🆕
리랭킹 모듈 구현 (새로 추가)

- [X] **RERANK-1**: Base Reranker 인터페이스
  - Files: `backend/app/reranking/rerankers/base_reranker.py`
  - Description:
    - BaseReranker 추상 클래스
    - rerank(query, documents, top_k) 메서드
  - Dependencies: None

- [X] **RERANK-2**: CrossEncoder Reranker
  - Files: `backend/app/reranking/rerankers/cross_encoder.py`
  - Description:
    - BAAI/bge-reranker-v2-m3 사용
    - sentence-transformers CrossEncoder
  - Dependencies: RERANK-1

- [X] **RERANK-3**: BM25 Reranker
  - Files: `backend/app/reranking/rerankers/bm25.py`
  - Description:
    - rank-bm25 라이브러리
    - 키워드 기반 재순위화
  - Dependencies: RERANK-1

- [ ] **RERANK-4**: ColBERT Reranker (Optional)
  - Files: `backend/app/reranking/rerankers/colbert.py`
  - Description:
    - ColBERT token-level 상호작용
    - (Optional, 복잡도 높음)
  - Dependencies: RERANK-1

- [X] **RERANK-5**: None Reranker
  - Files: `backend/app/reranking/rerankers/none.py`
  - Description:
    - Pass-through reranker (순위 변경 없음)
  - Dependencies: RERANK-1

### Phase 4: Data Models (용어 변경)
RAG, DataSource, DataSourceSync 모델

- [X] **MODEL-1**: RAGConfiguration 모델
  - Files: `backend/app/models/rag.py`, `backend/app/models/__init__.py`
  - Description:
    - id, name, description
    - chunking_module, chunking_params
    - embedding_module, embedding_params
    - reranking_module, reranking_params (필수)
    - collection_name: "rag_{id}"
  - Dependencies: None

- [X] **MODEL-2**: DataSource 모델
  - Files: `backend/app/models/datasource.py`
  - Description:
    - id, name, source_type, source_uri
    - file_size, content_hash, status, metadata
  - Dependencies: None

- [X] **MODEL-3**: DataSourceSync 모델
  - Files: `backend/app/models/datasource_sync.py`
  - Description:
    - rag_id, datasource_id (FK)
    - status, progress, current_step
    - num_chunks, sync_time, memory_usage
    - error_message
    - UNIQUE(rag_id, datasource_id)
  - Dependencies: MODEL-1, MODEL-2

- [X] **MODEL-4**: EvaluationDataset 모델
  - Files: `backend/app/models/evaluation_dataset.py`
  - Description:
    - id, name, description
    - dataset_uri (JSON 파일 경로)
    - num_queries, num_documents
  - Dependencies: None

- [X] **MODEL-5**: Evaluation & EvaluationResult 모델
  - Files: `backend/app/models/evaluation.py`
  - Description:
    - Evaluation: rag_id, dataset_id, status, progress
    - EvaluationResult: evaluation_id, metrics (NDCG, MRR, etc.)
  - Dependencies: MODEL-1, MODEL-4

### Phase 5: RAG Factory
통합 Factory (3개 모듈)

- [X] **FACTORY-1**: RAGFactory 구현
  - Files: `backend/app/services/rag_factory.py`
  - Description:
    - create_chunker(module, params) → Chunker
    - create_embedder(module, params) → Embedder (Singleton)
    - create_reranker(module, params) → Reranker
    - create_rag(rag_config) → (chunker, embedder, reranker)
    - 지원 모듈:
      - Chunking: recursive, hierarchical, semantic, late_chunking
      - Embedding: bge_m3, matryoshka, vllm_http, jina_late_chunking
      - Reranking: cross_encoder, bm25, colbert, none
  - Dependencies: EVAL-2, EVAL-3, RERANK-5

### Phase 6: Pydantic Schemas

- [X] **SCHEMA-1**: RAG 스키마
  - Files: `backend/app/schemas/rag.py`
  - Description:
    - RAGCreate: name, description, 3개 모듈 선택
    - RAGUpdate, RAGResponse
    - ChunkingConfig, EmbeddingConfig, RerankingConfig
  - Dependencies: None

- [X] **SCHEMA-2**: DataSource 스키마
  - Files: `backend/app/schemas/datasource.py`
  - Description:
    - DataSourceCreate, DataSourceResponse
    - UploadResponse
  - Dependencies: None

- [X] **SCHEMA-3**: Sync 스키마
  - Files: `backend/app/schemas/sync.py`
  - Description:
    - SyncRequest: { rag_id, datasource_id }
    - SyncResponse: DataSourceSync 정보
    - SyncStatus, SyncProgress
  - Dependencies: None

- [X] **SCHEMA-4**: EvaluationDataset 스키마
  - Files: `backend/app/schemas/dataset.py`
  - Description:
    - DatasetUploadRequest
    - DatasetResponse
    - DatasetDetail (queries, documents 포함)
  - Dependencies: None

- [X] **SCHEMA-5**: Evaluation 스키마
  - Files: `backend/app/schemas/evaluation.py`
  - Description:
    - EvaluationCreate: { rag_id, dataset_id }
    - CompareRequest: { rag_ids: [int], dataset_id }
    - EvaluationResponse, ComparisonResponse
    - MetricsResponse
  - Dependencies: None

- [X] **SCHEMA-6**: Query 스키마
  - Files: `backend/app/schemas/query.py`
  - Description:
    - SearchRequest: query, rag_id, datasource_ids, top_k
    - SearchResponse: results, total
    - AnswerRequest: 동일
    - AnswerResponse: answer, sources, tokens_used
    - RetrievedChunk: chunk_id, datasource_id, content, score
  - Dependencies: None

### Phase 7: Services Layer

- [X] **SERVICE-1**: SyncService 구현 (핵심!) 🔑
  - Files: `backend/app/services/sync_service.py`
  - Description:
    - sync_datasource(rag_id, datasource_id) → DataSourceSync
    - Background task로 비동기 동기화:
      1. RAG 로드 → Factory로 3개 모듈 생성
      2. DataSource 로드
      3. Chunking (progress 업데이트)
      4. Embedding (progress 업데이트)
      5. Qdrant "rag_{id}" collection에 저장
         - payload: { datasource_id, chunk_id, content }
      6. DataSourceSync 완료
    - get_sync_status(sync_id) → SyncStatus
    - delete_sync(sync_id) - Qdrant에서도 삭제
  - Dependencies: FACTORY-1, MODEL-3

- [X] **SERVICE-2**: QueryService 구현
  - Files: `backend/app/services/query_service.py`
  - Description:
    - search(rag_id, query, datasource_ids, top_k):
      1. RAG 로드 → embedder, reranker 생성
      2. Query embedding
      3. Qdrant search (top_k * 4)
         - collection: "rag_{id}"
         - filter: datasource_id in [...]
      4. Reranking (top_k * 4 → top_k)
    - answer(rag_id, query, datasource_ids, top_k):
      1. search() 호출
      2. Context 조립
      3. ClaudeGenerator로 답변 생성
  - Dependencies: FACTORY-1, EVAL-4

- [X] **SERVICE-3**: EvaluationService 구현
  - Files: `backend/app/services/evaluation_service.py`
  - Description:
    - evaluate_rag(rag_id, dataset_id) → Evaluation
    - compare_rags(rag_ids, dataset_id) → ComparisonResult
    - Background task로 RAGEvaluator 실행
  - Dependencies: EVAL-1, FACTORY-1, MODEL-5

- [X] **SERVICE-4**: RAGService 구현
  - Files: `backend/app/services/rag_service.py`
  - Description:
    - create_rag(data) → RAGConfiguration
    - validate_rag_params() - 모듈 파라미터 검증
    - get_datasources(rag_id) - 할당된 데이터 소스 목록
    - seed_default_rags() - 초기 기본 RAG 3개 생성
  - Dependencies: MODEL-1

### Phase 8: API Endpoints

- [X] **API-1**: RAG 엔드포인트
  - Files: `backend/app/api/routes/rags.py`
  - Description:
    - POST /api/v1/rags - RAG 생성
    - GET /api/v1/rags - RAG 목록
    - GET /api/v1/rags/{id} - RAG 조회
    - PUT /api/v1/rags/{id} - RAG 수정
    - DELETE /api/v1/rags/{id} - RAG 삭제
    - GET /api/v1/rags/{id}/datasources - 할당된 데이터 소스
  - Dependencies: SCHEMA-1, SERVICE-4

- [X] **API-2**: DataSource 엔드포인트
  - Files: `backend/app/api/routes/datasources.py`
  - Description:
    - POST /api/v1/datasources/upload - 파일 업로드
    - GET /api/v1/datasources - 데이터 소스 목록
    - GET /api/v1/datasources/{id} - 조회
    - DELETE /api/v1/datasources/{id} - 삭제
    - GET /api/v1/datasources/{id}/syncs - 동기화 기록
  - Dependencies: SCHEMA-2

- [X] **API-3**: Sync 엔드포인트 (핵심!) 🔑
  - Files: `backend/app/api/routes/sync.py`
  - Description:
    - POST /api/v1/sync - 동기화 시작
    - GET /api/v1/sync - 모든 동기화 기록
    - GET /api/v1/sync/{id} - 동기화 상태 조회
    - DELETE /api/v1/sync/{id} - 동기화 삭제
    - POST /api/v1/sync/{id}/rebuild - 재동기화
  - Dependencies: SCHEMA-3, SERVICE-1

- [X] **API-4**: EvaluationDataset 엔드포인트
  - Files: `backend/app/api/routes/datasets.py`
  - Description:
    - POST /api/v1/datasets/upload - JSON 업로드
    - GET /api/v1/datasets - 데이터셋 목록
    - GET /api/v1/datasets/{id} - 조회 (queries 포함)
    - DELETE /api/v1/datasets/{id} - 삭제
  - Dependencies: SCHEMA-4

- [X] **API-5**: Evaluation 엔드포인트
  - Files: `backend/app/api/routes/evaluate.py`
  - Description:
    - POST /api/v1/evaluations/run - 단일 RAG 평가
    - POST /api/v1/evaluations/compare - 여러 RAG 비교
    - GET /api/v1/evaluations/{id} - 평가 결과
    - GET /api/v1/evaluations/{id}/status - 진행 상황
    - POST /api/v1/evaluations/{id}/cancel - 취소
  - Dependencies: SCHEMA-5, SERVICE-3

- [X] **API-6**: Query 엔드포인트
  - Files: `backend/app/api/routes/query.py`
  - Description:
    - POST /api/v1/query/search - 벡터 검색 (reranking 포함)
    - POST /api/v1/query/answer - 검색 + LLM 답변
  - Dependencies: SCHEMA-6, SERVICE-2

- [X] **API-7**: API 라우터 등록
  - Files: `backend/app/main.py`
  - Description:
    - 모든 라우터 등록
    - CORS 설정
    - Startup event (seed_default_rags)
  - Dependencies: All API tasks

### Phase 9: Frontend - API Client

- [ ] **FE-API-1**: API 타입 정의
  - Files: `frontend/src/lib/types.ts`
  - Description:
    - RAG, DataSource, DataSourceSync
    - EvaluationDataset, Evaluation
    - Query types
  - Dependencies: None

- [ ] **FE-API-2**: API 클라이언트 함수
  - Files: `frontend/src/lib/api.ts`
  - Description:
    - RAG: create, list, get, update, delete
    - DataSource: upload, list, get, delete
    - Sync: start, getStatus, list, delete
    - Dataset: upload, list, get, delete
    - Evaluation: run, compare, getStatus
    - Query: search, answer
  - Dependencies: FE-API-1

### Phase 10: Frontend - RAG Management
RAG 생성 및 관리

- [ ] **FE-RAG-1**: RAG 목록 페이지
  - Files: `frontend/src/routes/rags/index.tsx`
  - Description:
    - RAG 카드 목록
    - 각 카드: 3개 모듈 표시, 동기화된 데이터 소스 수
    - "Create RAG" 버튼
  - Dependencies: FE-API-2

- [ ] **FE-RAG-2**: RAG 생성 페이지 (핵심!) 🔑
  - Files: `frontend/src/routes/rags/create.tsx`
  - Description:
    - 3개 모듈 선택 UI:
      1. Chunking 모듈 선택 (드롭다운 + 파라미터)
      2. Embedding 모듈 선택 (드롭다운 + 파라미터)
      3. Reranking 모듈 선택 (드롭다운 + 파라미터)
    - 각 모듈별 설명 tooltip
    - 추천 조합 preset (빠른, 균형, 정밀)
  - Dependencies: None

- [ ] **FE-RAG-3**: Module Selector 컴포넌트
  - Files: `frontend/src/components/rag/ModuleSelector.tsx`
  - Description:
    - 모듈 타입별 선택 UI
    - 파라미터 동적 폼
    - Validation
  - Dependencies: None

### Phase 11: Frontend - DataSource Management

- [ ] **FE-DS-1**: DataSource 목록 페이지
  - Files: `frontend/src/routes/datasources/index.tsx`
  - Description:
    - 데이터 소스 카드
    - 동기화 상태 표시
    - "Upload" 버튼
  - Dependencies: FE-API-2

- [ ] **FE-DS-2**: DataSource 업로드 페이지
  - Files: `frontend/src/routes/datasources/upload.tsx`
  - Description:
    - Drag & Drop 파일 업로드
    - PDF, TXT 지원
    - 업로드 후 RAG 할당 옵션
  - Dependencies: None

### Phase 12: Frontend - Sync Management (핵심!)

- [ ] **FE-SYNC-1**: Sync 관리 페이지 🔑
  - Files: `frontend/src/routes/sync.tsx`
  - Description:
    - 동기화 시작 UI:
      1. RAG 선택 (드롭다운)
      2. DataSource 선택 (멀티 선택)
      3. "Start Sync" 버튼
    - 진행 중인 동기화 목록
    - 완료된 동기화 기록
  - Dependencies: FE-API-2

- [ ] **FE-SYNC-2**: Sync Progress 컴포넌트
  - Files: `frontend/src/components/sync/SyncProgress.tsx`
  - Description:
    - Progress bar (0-100%)
    - Current step 표시 (chunking, embedding, storing)
    - 소요 시간, 예상 남은 시간
    - Polling으로 실시간 업데이트 (1초 간격)
  - Dependencies: None

- [ ] **FE-SYNC-3**: Sync History 컴포넌트
  - Files: `frontend/src/components/sync/SyncHistory.tsx`
  - Description:
    - 동기화 기록 테이블
    - RAG, DataSource, 상태, 소요 시간
    - 액션: 재동기화, 삭제
  - Dependencies: None

### Phase 13: Frontend - Evaluation (정량적 평가)

- [ ] **FE-EVAL-1**: Evaluation Dataset 관리
  - Files: `frontend/src/routes/evaluate/datasets.tsx`
  - Description:
    - 데이터셋 업로드 (JSON)
    - 데이터셋 목록 (queries 수, documents 수)
    - 데이터셋 상세 보기 (쿼리 목록)
  - Dependencies: FE-API-2

- [ ] **FE-EVAL-2**: Evaluation 실행 페이지
  - Files: `frontend/src/routes/evaluate/index.tsx`
  - Description:
    - 단일 평가:
      - RAG 선택
      - Dataset 선택
      - "Run Evaluation" 버튼
    - 평가 진행 상황
    - 결과 표시 (MetricsTable)
  - Dependencies: FE-API-2

- [ ] **FE-EVAL-3**: RAG 비교 페이지 (핵심!) 🔑
  - Files: `frontend/src/routes/evaluate/compare.tsx`
  - Description:
    - 여러 RAG 선택 (체크박스)
    - Dataset 선택
    - "Compare" 버튼
    - 비교 테이블 (MetricsTable)
    - 비교 차트 (ComparisonChart)
    - Winner 표시
  - Dependencies: FE-API-2

- [ ] **FE-EVAL-4**: Metrics Table 컴포넌트
  - Files: `frontend/src/components/evaluation/MetricsTable.tsx`
  - Description:
    - Retrieval metrics (NDCG, MRR, Precision, Recall, Hit Rate, MAP)
    - Efficiency metrics (Sync Time, Query Latency, Memory)
    - RAG Metrics (optional, Context Relevance, Faithfulness)
  - Dependencies: None

- [ ] **FE-EVAL-5**: Comparison Chart 컴포넌트
  - Files: `frontend/src/components/evaluation/ComparisonChart.tsx`
  - Description:
    - Bar chart (여러 RAG 메트릭 비교)
    - Radar chart (종합 성능)
    - 메트릭 선택 드롭다운
  - Dependencies: None

### Phase 14: Frontend - Query (정성적 평가)

- [ ] **FE-QUERY-1**: Query 페이지 (핵심!) 🔑
  - Files: `frontend/src/routes/query.tsx`
  - Description:
    - RAG 선택 (드롭다운)
    - DataSource 필터 (멀티 선택 또는 "All")
    - Query 입력
    - "Search" / "Answer" 버튼
    - 결과 표시 영역
  - Dependencies: FE-API-2

- [ ] **FE-QUERY-2**: Search Results 컴포넌트
  - Files: `frontend/src/components/query/ResultsList.tsx`
  - Description:
    - Retrieved chunks 목록
    - 각 chunk: content, score, datasource_name
    - Reranking 전후 순위 비교 (optional)
  - Dependencies: None

- [ ] **FE-QUERY-3**: Answer Display 컴포넌트
  - Files: `frontend/src/components/query/AnswerDisplay.tsx`
  - Description:
    - LLM 답변 (Markdown rendering)
    - Sources 카드 (클릭 시 원문)
    - Relevance score 시각화
  - Dependencies: None

- [ ] **FE-QUERY-4**: Dataset Query Tester
  - Files: `frontend/src/components/query/DatasetQueryTester.tsx`
  - Description:
    - 평가 데이터셋의 쿼리 선택
    - 해당 쿼리로 검색/답변 테스트
    - Ground truth와 비교
  - Dependencies: None

### Phase 15: Integration & Testing

- [ ] **TEST-1**: Backend 통합 테스트
  - Files: `backend/tests/integration/test_sync.py`, `backend/tests/integration/test_evaluation.py`, `backend/tests/integration/test_query.py`
  - Description:
    - Sync end-to-end 테스트
    - Evaluation end-to-end 테스트
    - Query pipeline 테스트
  - Dependencies: All backend tasks

- [ ] **TEST-2**: API 엔드포인트 테스트
  - Files: `backend/tests/api/`
  - Description:
    - 각 엔드포인트 HTTP 테스트
    - Request/Response 검증
  - Dependencies: All API tasks

- [ ] **TEST-3**: Frontend E2E 테스트 (Optional)
  - Files: `frontend/e2e/`
  - Description:
    - RAG 생성 → DataSource 추가 → Sync → Query 플로우
    - Evaluation 플로우
  - Dependencies: All frontend tasks

### Phase 16: Polish & Documentation

- [ ] **POLISH-1**: Error handling 개선
  - Files: 전체
  - Description:
    - User-friendly error messages
    - Toast notifications (frontend)
    - Retry logic
  - Dependencies: None

- [ ] **POLISH-2**: Loading states & UX
  - Files: Frontend components
  - Description:
    - Skeleton loaders
    - Optimistic updates
    - Smooth transitions
  - Dependencies: None

- [ ] **POLISH-3**: Seed default RAGs
  - Files: `backend/app/services/rag_service.py`, `backend/app/main.py`
  - Description:
    - Startup event에서 기본 RAG 3개 생성
    - RAG 1: Recursive + BGE-M3 + None (빠른)
    - RAG 2: Semantic + Matryoshka + CrossEncoder (균형)
    - RAG 3: Hierarchical + BGE-M3 + CrossEncoder (정밀)
  - Dependencies: SERVICE-4

- [ ] **POLISH-4**: README 업데이트
  - Files: `README.md`
  - Description:
    - 5단계 플로우 설명
    - 스크린샷 추가
    - API 문서 링크
  - Dependencies: None

- [ ] **POLISH-5**: Docker Compose 업데이트
  - Files: `docker-compose.yml`
  - Description:
    - 환경 변수 추가
    - 볼륨 설정
  - Dependencies: None

## Task Summary

### Total Tasks: 77

### By Phase:
- Setup & Dependencies: 3 tasks
- Evaluation System Migration: 5 tasks
- **Reranking Module: 5 tasks** 🆕
- Data Models: 5 tasks (용어 변경: RAG, DataSource, DataSourceSync)
- RAG Factory: 1 task (3개 모듈 통합)
- Pydantic Schemas: 6 tasks
- Services Layer: 4 tasks (SyncService 핵심)
- API Endpoints: 7 tasks
- Frontend API Client: 2 tasks
- Frontend RAG Management: 3 tasks
- Frontend DataSource Management: 2 tasks
- **Frontend Sync Management: 3 tasks** 🔑
- Frontend Evaluation: 5 tasks
- Frontend Query: 4 tasks
- Integration & Testing: 3 tasks
- Polish & Documentation: 5 tasks

### Parallel Execution Notes:
- SETUP tasks can run in parallel
- EVAL-2, EVAL-3, EVAL-4 can run in parallel
- RERANK-2, RERANK-3, RERANK-4, RERANK-5 can run in parallel
- MODEL tasks can run in parallel
- SCHEMA tasks can run in parallel
- Frontend tasks within same phase can run in parallel

## Execution Strategy

1. **Setup Phase**: 의존성 설치 (SETUP-1~3)
2. **Migration Phase**: 코드 복사 (EVAL-1~5)
3. **Reranking Phase**: 리랭킹 모듈 구현 (RERANK-1~5) 🆕
4. **Model Phase**: 데이터 모델 정의 (MODEL-1~5)
5. **Factory Phase**: RAG Factory 구현 (FACTORY-1)
6. **Schema Phase**: API 스키마 (SCHEMA-1~6)
7. **Service Phase**: 비즈니스 로직 (SERVICE-1~4)
8. **API Phase**: REST API (API-1~7)
9. **Frontend Phase**: UI 구현 (FE-*-*)
10. **Test Phase**: 통합 테스트 (TEST-1~3)
11. **Polish Phase**: 마무리 (POLISH-1~5)

## Critical Path (우선 순위)

### Must-Have (MVP):
1. ✅ Reranking 모듈 (RERANK-1~5)
2. ✅ 용어 변경 (RAG, DataSource, DataSourceSync)
3. ✅ SyncService (SERVICE-1) - 핵심!
4. ✅ RAG Factory (FACTORY-1)
5. ✅ Frontend RAG 생성 (FE-RAG-2)
6. ✅ Frontend Sync UI (FE-SYNC-1~3)
7. ✅ Query Service & UI (SERVICE-2, FE-QUERY-1~3)

### Should-Have:
1. Evaluation system (SERVICE-3, FE-EVAL-1~5)
2. Dataset management (API-4, FE-EVAL-1)
3. Comparison charts (FE-EVAL-3~5)

### Nice-to-Have:
1. ColBERT reranker (RERANK-4)
2. Dataset query tester (FE-QUERY-4)
3. E2E tests (TEST-3)

## Notes

- **핵심 개념**: 어떤 RAG가 동기화했는지 기록 (DataSourceSync)
- **Qdrant Collection 전략**: `rag_{id}` 형식
- **리랭킹 필수**: 3개 모듈 모두 선택 필요
- **5단계 플로우** 중심 설계:
  1. RAG 생성 (3개 모듈 선택)
  2. DataSource 추가
  3. Sync (진행 상황 추적)
  4. Evaluation (정량)
  5. Query (정성)
- Factory 패턴으로 모듈 생성 일원화
- Frontend는 Backend API 완성 후 시작 권장


