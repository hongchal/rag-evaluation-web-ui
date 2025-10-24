# Implementation Tasks - RAG Evaluation System Integration

## Overview
이 문서는 tkai-agents/apps/rag의 evaluation 시스템을 현재 프로젝트에 통합하는 구체적인 작업 목록입니다.

## Task Phases

### Phase 1: Setup & Dependencies
필수 의존성 설치 및 프로젝트 구조 준비

- [ ] **SETUP-1**: requirements.txt 업데이트
  - Files: `backend/requirements.txt`
  - Description: evaluation 시스템에 필요한 패키지 추가
    - FlagEmbedding>=1.2.0 (BGE-M3)
    - anthropic>=0.18.0 (Claude)
    - ragas>=0.1.0 (평가)
    - langchain-text-splitters>=0.0.1
    - langchain-anthropic (RAGAS Claude 지원)
    - langchain-community (HuggingFace embeddings)
    - pandas (비교 테이블)
    - numpy (메트릭 계산)
  - Dependencies: None

- [ ] **SETUP-2**: Backend 디렉토리 구조 생성
  - Files: `backend/app/evaluation/`, `backend/app/chunking/`, `backend/app/embedding/`, `backend/app/pipeline/`, `backend/app/schemas/`
  - Description: 새로운 모듈 디렉토리 생성
  - Dependencies: None

- [ ] **SETUP-3**: 환경 변수 추가
  - Files: `backend/env.example`
  - Description: ANTHROPIC_API_KEY, LLM_MODEL 등 추가
  - Dependencies: None

### Phase 2: Evaluation System Migration
tkai-agents에서 evaluation 코드 가져오기 및 수정

- [ ] **EVAL-1**: evaluation 모듈 복사 및 수정
  - Files: `backend/app/evaluation/evaluator.py`, `backend/app/evaluation/comparator.py`, `backend/app/evaluation/metrics.py`, `backend/app/evaluation/dataset.py`, `backend/app/evaluation/__init__.py`
  - Description: 
    - `/Users/chohongcheol/tkai-agents/apps/rag/src/evaluation/` → `backend/app/evaluation/`
    - Import 경로 수정 (src.* → app.*)
    - Config import 수정 (현재 프로젝트의 config 사용)
  - Dependencies: SETUP-2

- [ ] **EVAL-2**: chunking 모듈 복사 및 수정
  - Files: `backend/app/chunking/chunkers/`, `backend/app/chunking/__init__.py`, `backend/app/chunking/factory.py`
  - Description:
    - `/Users/chohongcheol/tkai-agents/apps/rag/src/chunking/` → `backend/app/chunking/`
    - Import 경로 수정
    - Factory 패턴 추가 (ChunkerFactory)
  - Dependencies: SETUP-2

- [ ] **EVAL-3**: embedding 모듈 복사 및 수정
  - Files: `backend/app/embedding/embedders/`, `backend/app/embedding/__init__.py`, `backend/app/embedding/factory.py`
  - Description:
    - `/Users/chohongcheol/tkai-agents/apps/rag/src/embedding/` → `backend/app/embedding/`
    - Import 경로 수정
    - Factory 패턴 추가 (EmbedderFactory)
  - Dependencies: SETUP-2

- [ ] **EVAL-4**: pipeline 모듈 복사 및 수정
  - Files: `backend/app/pipeline/query.py`, `backend/app/pipeline/generators/`, `backend/app/pipeline/retrievers/`, `backend/app/pipeline/__init__.py`
  - Description:
    - `/Users/chohongcheol/tkai-agents/apps/rag/src/pipeline/` → `backend/app/pipeline/`
    - QueryPipeline, ClaudeGenerator 통합
    - Import 경로 수정
  - Dependencies: SETUP-2

- [ ] **EVAL-5**: Qdrant 서비스 확장
  - Files: `backend/app/services/qdrant_service.py`
  - Description:
    - Hybrid search 지원 추가 (dense + sparse vectors)
    - Batch operations 추가 (add_chunks, get_by_ids)
    - Collection 관리 개선 (collection_exists)
  - Dependencies: None

### Phase 2.5: Document Indexing System (새로 추가) 🆕
프로덕션 문서 인덱싱 시스템

- [ ] **MODEL-1**: DocumentIndex 모델 추가
  - Files: `backend/app/models/document_index.py`, `backend/app/models/__init__.py`
  - Description:
    - document_id, strategy_id (FK)
    - collection_name (Qdrant collection)
    - status, progress, current_step, error_message
    - num_chunks, indexing_time, memory_usage
    - started_at, completed_at, created_at, updated_at
    - Unique constraint: (document_id, strategy_id)
  - Dependencies: None

- [ ] **SCHEMA-5**: DocumentIndex 스키마
  - Files: `backend/app/schemas/document_index.py`
  - Description:
    - IndexRequest: { strategy_id: int }
    - IndexResponse: DocumentIndex 정보
    - IndexStatus: status, progress, current_step
    - IndexProgress: 실시간 진행 상황
  - Dependencies: None

- [ ] **SERVICE-4**: IndexingService 구현
  - Files: `backend/app/services/indexing_service.py`
  - Description:
    - index_document(document_id, strategy_id) → DocumentIndex
    - Background task로 비동기 인덱싱
    - Factory로 Chunker/Embedder 생성
    - Qdrant collection 관리:
      - collection_name = f"strategy_{strategy_id}"
      - payload에 document_id 포함
    - 진행 상황 업데이트 (status, progress)
    - 에러 핸들링 및 롤백
  - Dependencies: FACTORY-1, FACTORY-2

- [ ] **API-1.5**: Document Indexing 엔드포인트
  - Files: `backend/app/api/routes/documents.py` (기존 파일 확장)
  - Description:
    - POST /api/v1/documents/{id}/index
    - GET /api/v1/documents/{id}/indexes
    - GET /api/v1/documents/{id}/indexes/{index_id}
    - DELETE /api/v1/documents/{id}/indexes/{index_id}
    - POST /api/v1/documents/{id}/indexes/{index_id}/rebuild
  - Dependencies: SCHEMA-5, SERVICE-4

### Phase 3: Factory Pattern Implementation
전략 생성을 위한 Factory 구현

- [ ] **FACTORY-1**: ChunkerFactory 구현
  - Files: `backend/app/chunking/factory.py`
  - Description:
    - 전략 이름과 파라미터로 Chunker 인스턴스 생성
    - 지원: recursive, hierarchical, semantic, late_chunking
    - 파라미터 검증 (Pydantic)
  - Dependencies: EVAL-2

- [ ] **FACTORY-2**: EmbedderFactory 구현
  - Files: `backend/app/embedding/factory.py`
  - Description:
    - 전략 이름과 파라미터로 Embedder 인스턴스 생성
    - 지원: bge_m3, matryoshka, vllm_http, jina_late_chunking
    - Singleton 패턴 (모델 중복 로딩 방지)
  - Dependencies: EVAL-3

### Phase 4: Pydantic Schemas
API request/response 스키마 정의

- [ ] **SCHEMA-1**: Strategy 스키마
  - Files: `backend/app/schemas/strategy.py`
  - Description:
    - StrategyCreate, StrategyUpdate, StrategyResponse
    - ChunkingConfig, EmbeddingConfig 중첩 스키마
    - 파라미터 검증 로직
  - Dependencies: None

- [ ] **SCHEMA-2**: Evaluation 스키마
  - Files: `backend/app/schemas/evaluation.py`
  - Description:
    - EvaluationCreate, EvaluationResponse
    - EvaluationStatus, EvaluationProgress
    - MetricsResponse (retrieval, efficiency, rag)
  - Dependencies: None

- [ ] **SCHEMA-3**: Query 스키마 (수정됨) 🔄
  - Files: `backend/app/schemas/query.py`
  - Description:
    - SearchRequest: query, strategy_id, document_ids (Optional[List[int]]), top_k
    - SearchResponse: results (List[RetrievedChunk]), total
    - AnswerRequest: query, strategy_id, document_ids (Optional[List[int]]), top_k
    - AnswerResponse: answer, sources, search_results
    - RetrievedChunk: chunk_id, document_id, content, score, metadata
  - Dependencies: None

- [ ] **SCHEMA-4**: Comparison 스키마
  - Files: `backend/app/schemas/comparison.py`
  - Description:
    - CompareRequest (strategy_ids, dataset)
    - ComparisonResponse (table, winner, charts data)
  - Dependencies: None

### Phase 5: Services Layer
비즈니스 로직 구현

- [ ] **SERVICE-1**: EvaluationService 구현
  - Files: `backend/app/services/evaluation_service.py`
  - Description:
    - run_evaluation(strategy_id, document_id) → Evaluation
    - compare_strategies(strategy_ids, document_id) → Comparison
    - get_evaluation_status(evaluation_id) → Status
    - cancel_evaluation(evaluation_id)
    - Database와 RAGEvaluator 통합
  - Dependencies: EVAL-1, FACTORY-1, FACTORY-2

- [ ] **SERVICE-2**: QueryService 구현 (수정됨) 🔄
  - Files: `backend/app/services/query_service.py`
  - Description:
    - search(query, strategy_id, document_ids, top_k) → SearchResults
    - answer(query, strategy_id, document_ids, top_k) → Answer + Sources
    - Qdrant collection: f"strategy_{strategy_id}"
    - Qdrant filter: document_id in document_ids (if specified)
    - QueryPipeline 통합 (ClaudeGenerator)
  - Dependencies: EVAL-4, FACTORY-1, FACTORY-2

- [ ] **SERVICE-3**: StrategyService 구현 (확장됨) 🔄
  - Files: `backend/app/services/strategy_service.py`
  - Description:
    - create_strategy(data) → Strategy
    - validate_strategy_params(chunker, embedder, params)
    - get_default_strategies() → List[Strategy]
    - seed_default_strategies() - 초기 기본 전략 생성
      - Strategy 1: Recursive + BGE-M3 (빠른 전략)
      - Strategy 2: Semantic + Matryoshka (균형 전략)
      - Strategy 3: Hierarchical + BGE-M3 (정밀 전략)
  - Dependencies: None

### Phase 6: API Endpoints
REST API 구현

- [ ] **API-1**: Strategy 엔드포인트
  - Files: `backend/app/api/routes/strategies.py`
  - Description:
    - POST /api/v1/strategies
    - GET /api/v1/strategies
    - GET /api/v1/strategies/{id}
    - PUT /api/v1/strategies/{id}
    - DELETE /api/v1/strategies/{id}
  - Dependencies: SCHEMA-1, SERVICE-3

- [ ] **API-2**: Evaluation 엔드포인트
  - Files: `backend/app/api/routes/evaluate.py`
  - Description:
    - POST /api/v1/evaluations/run
    - GET /api/v1/evaluations/{id}
    - GET /api/v1/evaluations/{id}/status
    - POST /api/v1/evaluations/{id}/cancel
    - Background task로 평가 실행
  - Dependencies: SCHEMA-2, SERVICE-1

- [ ] **API-3**: Comparison 엔드포인트
  - Files: `backend/app/api/routes/compare.py`
  - Description:
    - POST /api/v1/compare
    - GET /api/v1/compare/{id}
    - 병렬 평가 지원
  - Dependencies: SCHEMA-4, SERVICE-1

- [ ] **API-4**: Query 엔드포인트
  - Files: `backend/app/api/routes/query.py`
  - Description:
    - POST /api/v1/query/search
    - POST /api/v1/query/answer
    - Strategy 기반 실시간 검색/답변
  - Dependencies: SCHEMA-3, SERVICE-2

- [ ] **API-5**: API 라우터 등록
  - Files: `backend/app/main.py`
  - Description:
    - 새로운 라우터들 app에 등록
    - CORS 설정 확인
  - Dependencies: API-1, API-2, API-3, API-4

### Phase 7: Frontend - API Client
TypeScript API 클라이언트

- [ ] **FE-API-1**: API 타입 정의
  - Files: `frontend/src/lib/types.ts`
  - Description:
    - Backend 스키마와 일치하는 TypeScript 타입
    - Strategy, Evaluation, Query 타입
  - Dependencies: None

- [ ] **FE-API-2**: API 클라이언트 함수
  - Files: `frontend/src/lib/api.ts`
  - Description:
    - strategies: create, list, get, update, delete
    - evaluations: run, getStatus, cancel
    - compare: run, getResults
    - query: search, answer
    - Axios/Fetch 기반 HTTP 클라이언트
  - Dependencies: FE-API-1

### Phase 8: Frontend - Strategy Management
전략 관리 UI

- [ ] **FE-STRATEGY-1**: Strategy 목록 페이지
  - Files: `frontend/src/routes/strategies.tsx`
  - Description:
    - 전략 목록 표시 (카드 형태)
    - 생성/수정/삭제 버튼
    - TanStack Query로 데이터 fetching
  - Dependencies: FE-API-2

- [ ] **FE-STRATEGY-2**: Strategy 생성/수정 폼
  - Files: `frontend/src/components/strategy/StrategyForm.tsx`
  - Description:
    - Chunking 전략 선택 (드롭다운)
    - 파라미터 입력 (동적 폼)
    - Embedding 전략 선택
    - Validation & 제출
  - Dependencies: None

- [ ] **FE-STRATEGY-3**: Strategy 카드 컴포넌트
  - Files: `frontend/src/components/strategy/StrategyCard.tsx`
  - Description:
    - 전략 정보 표시
    - 액션 버튼 (수정, 삭제, 평가 실행)
  - Dependencies: None

### Phase 9: Frontend - Evaluation UI
평가 실행 및 결과 표시

- [ ] **FE-EVAL-1**: Evaluation 실행 페이지
  - Files: `frontend/src/routes/evaluate.tsx`
  - Description:
    - 문서 선택
    - 전략 선택 (단일 또는 복수)
    - 평가 시작 버튼
    - 실행 중인 평가 목록
  - Dependencies: FE-API-2

- [ ] **FE-EVAL-2**: 평가 진행 상황 컴포넌트
  - Files: `frontend/src/components/evaluation/EvaluationProgress.tsx`
  - Description:
    - Progress bar
    - Current step 표시
    - Polling으로 상태 업데이트 (1초 간격)
    - 취소 버튼
  - Dependencies: None

- [ ] **FE-EVAL-3**: 메트릭 테이블 컴포넌트
  - Files: `frontend/src/components/evaluation/MetricsTable.tsx`
  - Description:
    - Retrieval metrics (NDCG, MRR, Precision, Recall, Hit Rate, MAP)
    - Efficiency metrics (Indexing Time, Query Latency, Memory)
    - RAG metrics (Context Relevance, Faithfulness 등) - optional
  - Dependencies: None

- [ ] **FE-EVAL-4**: 비교 차트 컴포넌트
  - Files: `frontend/src/components/evaluation/ComparisonChart.tsx`
  - Description:
    - Recharts Bar chart (여러 전략 메트릭 비교)
    - Radar chart (종합 성능)
    - 메트릭 선택 드롭다운
  - Dependencies: None

- [ ] **FE-EVAL-5**: 결과 대시보드
  - Files: `frontend/src/components/evaluation/ResultDashboard.tsx`
  - Description:
    - 메트릭 테이블 + 차트 통합
    - Winner 표시
    - Export 기능 (CSV, JSON)
  - Dependencies: FE-EVAL-3, FE-EVAL-4

### Phase 10: Frontend - Query UI
실시간 검색 및 답변

- [ ] **FE-QUERY-1**: Query 페이지
  - Files: `frontend/src/routes/query.tsx`
  - Description:
    - 전략 선택
    - 검색 바
    - 결과 표시 영역
  - Dependencies: FE-API-2

- [ ] **FE-QUERY-2**: 검색 바 컴포넌트
  - Files: `frontend/src/components/query/SearchBar.tsx`
  - Description:
    - Text input
    - Search 버튼
    - Top-K 설정
    - Loading state
  - Dependencies: None

- [ ] **FE-QUERY-3**: 검색 결과 컴포넌트
  - Files: `frontend/src/components/query/SearchResults.tsx`
  - Description:
    - Retrieved chunks 목록
    - Score 표시
    - Source document 링크
    - Highlight keywords
  - Dependencies: None

- [ ] **FE-QUERY-4**: 답변 표시 컴포넌트
  - Files: `frontend/src/components/query/AnswerDisplay.tsx`
  - Description:
    - LLM 생성 답변 표시
    - Sources 참조
    - Markdown rendering
  - Dependencies: None

### Phase 11: Integration & Testing
통합 및 테스트

- [ ] **TEST-1**: Backend 통합 테스트
  - Files: `backend/tests/integration/test_evaluation.py`
  - Description:
    - Evaluation end-to-end 테스트
    - Strategy CRUD 테스트
    - Query pipeline 테스트
  - Dependencies: All backend tasks

- [ ] **TEST-2**: API 엔드포인트 테스트
  - Files: `backend/tests/api/test_routes.py`
  - Description:
    - 각 엔드포인트 HTTP 테스트
    - Request/Response 검증
  - Dependencies: All API tasks

- [ ] **TEST-3**: Frontend E2E 테스트 (Optional)
  - Files: `frontend/e2e/evaluation.spec.ts`
  - Description:
    - Playwright E2E 테스트
    - 전략 생성 → 평가 실행 → 결과 확인 플로우
  - Dependencies: All frontend tasks

### Phase 12: Polish & Documentation
마무리 및 문서화

- [ ] **POLISH-1**: Error handling 개선
  - Files: `backend/app/api/routes/*.py`, `frontend/src/components/**/*.tsx`
  - Description:
    - User-friendly error messages
    - Toast notifications (frontend)
    - Retry logic
  - Dependencies: None

- [ ] **POLISH-2**: Loading states & UX
  - Files: `frontend/src/components/**/*.tsx`
  - Description:
    - Skeleton loaders
    - Optimistic updates
    - Smooth transitions
  - Dependencies: None

- [ ] **POLISH-3**: README 업데이트
  - Files: `README.md`
  - Description:
    - 새로운 기능 설명
    - API 문서 링크
    - 스크린샷 추가
  - Dependencies: None

- [ ] **POLISH-4**: Docker Compose 업데이트
  - Files: `docker-compose.yml`
  - Description:
    - 새로운 환경 변수 추가
    - 볼륨 설정 확인
  - Dependencies: None

## Task Summary

### Total Tasks: 60 (4개 추가됨) 🔄

### By Phase:
- Setup & Dependencies: 3 tasks
- Evaluation System Migration: 5 tasks
- **Document Indexing System: 4 tasks** 🆕
- Factory Pattern: 2 tasks
- Pydantic Schemas: 4 tasks (SCHEMA-3 수정, SCHEMA-5 추가)
- Services Layer: 3 tasks (SERVICE-2 수정, SERVICE-3 확장)
- API Endpoints: 5 tasks (API-1.5 추가, API-4 수정)
- Frontend API Client: 2 tasks
- Strategy Management: 3 tasks
- Evaluation UI: 5 tasks
- Query UI: 4 tasks
- Integration & Testing: 3 tasks
- Polish & Documentation: 4 tasks

### Parallel Execution Notes:
- SETUP-1, SETUP-2, SETUP-3 can run in parallel
- EVAL-2, EVAL-3, EVAL-4 can run in parallel after SETUP-2
- SCHEMA-1, SCHEMA-2, SCHEMA-3, SCHEMA-4 can run in parallel
- Frontend tasks within same phase can run in parallel

## Execution Strategy

1. **Setup Phase**: 필수 의존성 설치 (SETUP-1~3)
2. **Migration Phase**: 코드 복사 및 수정 (EVAL-1~5)
3. **Indexing Phase**: Document Indexing 시스템 (MODEL-1, SCHEMA-5, SERVICE-4, API-1.5) 🆕
4. **Factory Phase**: Factory 패턴 구현 (FACTORY-1~2)
5. **Schema Phase**: API 스키마 정의 (SCHEMA-1~4)
6. **Service Phase**: 비즈니스 로직 (SERVICE-1~3)
7. **API Phase**: REST API 엔드포인트 (API-1~5)
8. **Frontend Phase**: UI 구현 (FE-*-*)
9. **Test Phase**: 통합 테스트 (TEST-1~3)
10. **Polish Phase**: 마무리 (POLISH-1~4)

## Notes

- 각 Phase는 순차적으로 진행
- Phase 내에서는 독립적인 작업은 병렬 가능
- 파일 복사 작업 시 import 경로 주의
- Factory 패턴으로 전략 생성 일원화
- **Qdrant Collection 전략**: `strategy_{strategy_id}` 형식 🔑
  - 하나의 전략 = 하나의 collection
  - Payload에 document_id 포함하여 필터링
  - 평가용 collection은 별도 (`eval_{hash}`)
- **DocumentIndex 모델**: 문서-전략 인덱싱 상태 추적 필수 🆕
- Frontend는 Backend API 완성 후 시작 권장


