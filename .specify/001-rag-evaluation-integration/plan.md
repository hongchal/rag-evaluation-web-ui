# RAG Evaluation System Integration - Implementation Plan

## 개요

`tkai-agents/apps/rag`의 검증된 evaluation 시스템을 현재 프로젝트에 통합하여, **다양한 RAG 전략을 비교하고 검색/답변을 실시간으로 확인할 수 있는 웹 UI**를 구축합니다.

### 목표

1. **다양한 전략 지원**: Chunking, Embedding, Reranking 전략을 선택하고 조합 가능
2. **성능 비교**: 여러 전략을 동시에 평가하고 메트릭 비교
3. **실시간 검색**: 선택한 전략으로 질의하고 검색 결과 + LLM 답변 확인
4. **시각화**: 평가 결과를 차트와 테이블로 직관적으로 표시

## 기술 스택

### Backend (Python)
- **FastAPI**: REST API 서버
- **PostgreSQL**: 메타데이터, 평가 결과 저장
- **Qdrant**: Vector store (Hybrid Search 지원)
- **SQLAlchemy**: ORM
- **Pydantic**: 데이터 검증
- **structlog**: 구조화된 로깅

### Evaluation & RAG Components (from tkai-agents)
- **FlagEmbedding (BGE-M3)**: Multi-lingual embedding (1024-dim)
- **Matryoshka Embeddings**: 차원 축소 임베딩
- **VLLM HTTP**: 외부 임베딩 서버 지원
- **Jina Late Chunking**: Late chunking 전략
- **LangChain Text Splitters**: Recursive chunking
- **Anthropic Claude**: LLM 답변 생성
- **RAGAS**: End-to-end RAG 평가 (Context Relevance, Faithfulness 등)

### Frontend (TypeScript)
- **React 19**: UI 프레임워크
- **Vite**: 빌드 도구
- **TanStack Router**: File-based routing
- **TanStack Query**: Data fetching & caching
- **shadcn/ui**: UI 컴포넌트 (Radix UI 기반)
- **Tailwind CSS v4**: 스타일링
- **Recharts**: 차트 시각화

## 아키텍처

### 전체 구조

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                    │
│                                                          │
│  - Strategy Selection UI                                │
│  - Evaluation Dashboard                                 │
│  - Real-time Search & Answer                            │
│  - Comparison Charts                                    │
└─────────────────────┬───────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────┐
│                   Backend (FastAPI)                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   API        │  │  Services    │  │  Evaluation  │  │
│  │  Endpoints   │──│   Layer      │──│   System     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
└─────────────┬────────────────────────────┬───────────────┘
              │                            │
      ┌───────▼────────┐          ┌───────▼────────┐
      │   PostgreSQL   │          │     Qdrant     │
      │  (Metadata &   │          │  (Vector DB)   │
      │   Results)     │          │                │
      └────────────────┘          └────────────────┘
```

### Backend 디렉토리 구조

```
backend/
├── app/
│   ├── api/                    # API 엔드포인트
│   │   ├── routes/
│   │   │   ├── documents.py   # 문서 업로드/관리
│   │   │   ├── strategies.py  # 전략 CRUD
│   │   │   ├── evaluate.py    # 평가 실행
│   │   │   ├── compare.py     # 전략 비교
│   │   │   └── query.py       # 실시간 검색/답변
│   │   └── deps.py            # 의존성 주입
│   │
│   ├── core/                   # 핵심 설정
│   │   ├── config.py
│   │   └── database.py
│   │
│   ├── models/                 # SQLAlchemy 모델
│   │   ├── document.py
│   │   ├── strategy.py
│   │   ├── evaluation.py
│   │   └── __init__.py
│   │
│   ├── schemas/                # Pydantic 스키마
│   │   ├── document.py
│   │   ├── strategy.py
│   │   ├── evaluation.py
│   │   └── query.py
│   │
│   ├── services/               # 비즈니스 로직
│   │   ├── file_processor.py  # 파일 처리
│   │   ├── qdrant_service.py  # Vector store
│   │   ├── evaluation_service.py
│   │   └── query_service.py
│   │
│   ├── evaluation/             # ← tkai-agents에서 가져올 핵심
│   │   ├── __init__.py
│   │   ├── evaluator.py       # RAGEvaluator
│   │   ├── comparator.py      # StrategyComparator
│   │   ├── metrics.py         # 평가 메트릭
│   │   └── dataset.py         # 평가 데이터셋
│   │
│   ├── chunking/               # ← tkai-agents에서 가져올 것
│   │   ├── __init__.py
│   │   ├── factory.py         # Chunker factory
│   │   └── chunkers/
│   │       ├── base_chunker.py
│   │       ├── recursive.py   # RecursiveChunker
│   │       ├── hierarchical.py # HierarchicalChunker
│   │       ├── semantic.py    # SemanticChunker
│   │       └── late_chunking.py
│   │
│   ├── embedding/              # ← tkai-agents에서 가져올 것
│   │   ├── __init__.py
│   │   ├── factory.py         # Embedder factory
│   │   └── embedders/
│   │       ├── bge_m3.py      # BGEM3Embedder
│   │       ├── matryoshka.py  # MatryoshkaEmbedder
│   │       ├── vllm_http.py   # VLLMHTTPEmbedder
│   │       └── jina_late_chunking.py
│   │
│   ├── pipeline/               # ← tkai-agents에서 가져올 것
│   │   ├── __init__.py
│   │   ├── query.py           # QueryPipeline
│   │   ├── generators/
│   │   │   └── claude.py      # ClaudeGenerator
│   │   └── retrievers/
│   │       └── base.py
│   │
│   └── main.py
│
├── requirements.txt
└── Dockerfile
```

### Frontend 디렉토리 구조

```
frontend/
├── src/
│   ├── routes/                     # TanStack Router
│   │   ├── __root.tsx             # Root layout
│   │   ├── index.tsx              # Home (overview)
│   │   ├── upload.tsx             # 문서 업로드
│   │   ├── strategies.tsx         # 전략 관리
│   │   ├── evaluate.tsx           # 평가 실행 & 비교
│   │   └── query.tsx              # 실시간 검색
│   │
│   ├── components/
│   │   ├── ui/                    # shadcn/ui components
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── strategy/
│   │   │   ├── StrategyCard.tsx
│   │   │   ├── StrategyForm.tsx
│   │   │   └── StrategySelector.tsx
│   │   ├── evaluation/
│   │   │   ├── EvaluationProgress.tsx
│   │   │   ├── MetricsTable.tsx
│   │   │   ├── ComparisonChart.tsx
│   │   │   └── ResultDashboard.tsx
│   │   └── query/
│   │       ├── SearchBar.tsx
│   │       ├── SearchResults.tsx
│   │       └── AnswerDisplay.tsx
│   │
│   ├── lib/
│   │   ├── api.ts                 # API client
│   │   ├── utils.ts
│   │   └── types.ts               # TypeScript 타입
│   │
│   ├── hooks/
│   │   ├── useEvaluation.ts
│   │   ├── useQuery.ts
│   │   └── useWebSocket.ts        # (Optional) 실시간 업데이트
│   │
│   └── main.tsx
│
├── package.json
└── vite.config.ts
```

## 주요 컴포넌트

### 1. Evaluation System (from tkai-agents)

#### RAGEvaluator
- **역할**: 단일 전략(chunker + embedder) 평가
- **메트릭**:
  - Retrieval: NDCG@K, MRR, Precision@K, Recall@K, Hit Rate, MAP
  - Efficiency: Indexing Time, Query Latency, Memory Usage
  - RAG (Optional): Context Relevance, Answer Relevance, Faithfulness
- **프로세스**:
  1. 문서 인덱싱 (chunking → embedding → vector store)
  2. 쿼리 실행 (embedding → search)
  3. 메트릭 계산

#### StrategyComparator
- **역할**: 여러 전략 동시 비교
- **기능**:
  - 병렬 평가 (ProcessPoolExecutor)
  - 결과 집계 및 비교 테이블 생성
  - Winner 선정 (NDCG 기준)

### 2. Chunking Strategies

| Strategy | Description | Parameters |
|----------|-------------|------------|
| **Recursive** | LangChain RecursiveCharacterTextSplitter | `chunk_size`, `chunk_overlap` |
| **Hierarchical** | 계층적 청킹 | `chunk_size`, `overlap` |
| **Semantic** | 의미 기반 경계 탐지 | `similarity_threshold`, `min_chunk_tokens` |
| **Late Chunking** | Jina embedder 통합 | `chunk_size` |

### 3. Embedding Strategies

| Strategy | Description | Dimensions |
|----------|-------------|------------|
| **BGE-M3** | BAAI 다국어 임베딩 (Hybrid Search) | 1024 |
| **Matryoshka** | 차원 축소 임베딩 | 64~1024 (configurable) |
| **VLLM HTTP** | 외부 임베딩 서버 | Configurable |
| **Jina Late Chunking** | Late chunking 최적화 | 768 |

### 4. API Endpoints

#### Documents
- `POST /api/v1/documents/upload` - 파일 업로드
- `GET /api/v1/documents` - 문서 목록
- `GET /api/v1/documents/{id}` - 문서 조회
- `DELETE /api/v1/documents/{id}` - 문서 삭제

#### Document Indexing (새로 추가) 🆕
- `POST /api/v1/documents/{id}/index` - 문서를 특정 전략으로 인덱싱
  - Request: `{ "strategy_id": 1 }`
  - Response: `DocumentIndex` (status: pending)
- `GET /api/v1/documents/{id}/indexes` - 문서의 모든 인덱스 목록
- `GET /api/v1/documents/{id}/indexes/{index_id}` - 인덱스 상태 조회
- `DELETE /api/v1/documents/{id}/indexes/{index_id}` - 인덱스 삭제 (Qdrant collection도 정리)
- `POST /api/v1/documents/{id}/indexes/{index_id}/rebuild` - 재인덱싱

#### Strategies
- `POST /api/v1/strategies` - 전략 생성
- `GET /api/v1/strategies` - 전략 목록
- `GET /api/v1/strategies/{id}` - 전략 조회
- `PUT /api/v1/strategies/{id}` - 전략 수정
- `DELETE /api/v1/strategies/{id}` - 전략 삭제

#### Evaluation
- `POST /api/v1/evaluations/run` - 단일 전략 평가 실행
- `POST /api/v1/evaluations/compare` - 여러 전략 비교
- `GET /api/v1/evaluations/{id}` - 평가 결과 조회
- `GET /api/v1/evaluations/{id}/status` - 평가 진행 상황
- `POST /api/v1/evaluations/{id}/cancel` - 평가 취소

#### Query (수정됨) 🔄
- `POST /api/v1/query/search` - 벡터 검색만
  - Request: `{ "query": "...", "strategy_id": 1, "document_ids": [1,2], "top_k": 5 }`
  - document_ids: Optional, 특정 문서만 검색 (미지정 시 전체)
  - Response: `{ "results": [...], "total": 10 }`
- `POST /api/v1/query/answer` - 검색 + LLM 답변 생성
  - Request: `{ "query": "...", "strategy_id": 1, "document_ids": [1,2], "top_k": 5 }`
  - Response: `{ "answer": "...", "sources": [...], "search_results": [...] }`
- `POST /api/v1/query/stream` - Streaming 답변 (Optional)

## 데이터 모델

### Document
```python
id: int
filename: str
file_type: str  # pdf, txt
content_hash: str
file_size: int
num_pages: Optional[int]
status: str  # uploaded, processing, indexed, failed
created_at: datetime
updated_at: datetime
```

### Strategy
```python
id: int
name: str
description: Optional[str]

# Chunking
chunking_strategy: str  # recursive, hierarchical, semantic, late_chunking
chunking_params: JSON

# Embedding
embedding_strategy: str  # bge_m3, matryoshka, vllm_http, jina_late_chunking
embedding_params: JSON

# Reranking (Optional)
reranking_strategy: Optional[str]
reranking_params: Optional[JSON]

created_at: datetime
updated_at: datetime
```

### DocumentIndex (새로 추가) 🆕
```python
id: int
document_id: int  # FK to Document
strategy_id: int  # FK to Strategy

# Qdrant Collection
collection_name: str  # 전략별 통합 collection: "strategy_{strategy_id}"

# Status
status: str  # pending, indexing, completed, failed
progress: float  # 0.0 ~ 1.0
current_step: Optional[str]  # chunking, embedding, storing
error_message: Optional[str]

# Metrics
num_chunks: int
indexing_time: float  # seconds
memory_usage: float  # MB

# Timestamps
started_at: Optional[datetime]
completed_at: Optional[datetime]
created_at: datetime
updated_at: datetime

# Constraints
UNIQUE(document_id, strategy_id)  # 같은 문서는 같은 전략으로 한번만 인덱싱
```

### Evaluation
```python
id: int
name: str
description: Optional[str]
document_id: int
strategy_id: int

# Status
status: str  # pending, running, completed, failed, cancelled
progress: float  # 0.0 ~ 1.0
current_step: Optional[str]
error_message: Optional[str]

# Timestamps
started_at: Optional[datetime]
completed_at: Optional[datetime]
created_at: datetime
updated_at: datetime
```

### EvaluationResult
```python
id: int
evaluation_id: int

# Retrieval Metrics
ndcg_at_k: float
mrr: float
precision_at_k: float
recall_at_k: float
hit_rate: float
map_score: float

# Efficiency Metrics
chunking_time: float
embedding_time: float
retrieval_time: float
total_time: float
num_chunks: int
avg_chunk_size: float

# RAG Metrics (Optional)
context_relevance: Optional[float]
answer_relevance: Optional[float]
faithfulness: Optional[float]
context_recall: Optional[float]
context_precision: Optional[float]

# Additional Data
query_results: Optional[JSON]
metadata: Optional[JSON]

created_at: datetime
```

## 통합 전략

### Phase 1: Evaluation System 통합
1. `tkai-agents/apps/rag/src/evaluation` → `backend/app/evaluation`
2. `tkai-agents/apps/rag/src/chunking` → `backend/app/chunking`
3. `tkai-agents/apps/rag/src/embedding` → `backend/app/embedding`
4. `tkai-agents/apps/rag/src/pipeline` → `backend/app/pipeline`
5. 의존성 추가 (`requirements.txt`)

### Phase 2: Backend API 개발
1. DocumentIndex 모델 추가 (문서-전략 인덱싱 상태)
2. Factory 패턴으로 Chunker/Embedder 생성
3. IndexingService (문서 인덱싱 관리) 🆕
4. EvaluationService (평가 실행 관리)
5. QueryService (실시간 검색/답변)
6. API 엔드포인트 구현
7. WebSocket (Optional, 실시간 진행 상황)

### Phase 3: Frontend UI 개발
1. Strategy 관리 UI
2. Evaluation 실행 & 진행 상황 표시
3. 비교 대시보드 (차트, 테이블)
4. 실시간 Query UI
5. 결과 시각화

### Phase 4: 최적화 & 테스트
1. 병렬 평가 최적화
2. 캐싱 전략
3. 에러 핸들링
4. E2E 테스트
5. 성능 튜닝

## 기술적 고려사항

### 1. Async Processing
- FastAPI Background Tasks로 장시간 평가 실행
- Celery/Redis 도입 고려 (나중에)
- 진행 상황 업데이트 (polling 또는 WebSocket)

### 2. Qdrant Collection 전략 (중요!) 🔑

#### 프로덕션 인덱싱 (실제 검색용)
```
Collection 이름: "strategy_{strategy_id}"
예: "strategy_1", "strategy_2"

구조:
- 하나의 전략당 하나의 collection
- 여러 문서가 같은 collection에 저장
- Payload에 document_id 포함하여 필터링 가능

Payload:
{
  "document_id": 1,
  "chunk_id": "doc_1_chunk_0",
  "content": "...",
  "metadata": {...}
}

검색 시:
- collection_name = "strategy_{strategy_id}"
- filter: document_id in [1, 2, 3]  (optional)
```

#### 평가용 임시 Collection
```
Collection 이름: "eval_{hash}"
예: "eval_a1b2c3d4"

- RAGEvaluator가 평가 시 생성
- 평가 완료 후 자동 삭제 (cleanup_after=True)
- 프로덕션 collection과 분리
```

#### 장점:
- 전략별로 한번만 인덱싱 (재사용)
- 여러 문서 검색 가능
- Collection 수 최소화 (전략 개수만큼만)
- Payload 필터링으로 유연한 검색

### 3. Embedding Optimization
- Batch embedding for efficiency
- Model caching (GPU 메모리 최적화)
- Mixed precision (FP16) 지원

### 4. Frontend State Management
- TanStack Query로 서버 상태 관리
- Optimistic updates
- Cache invalidation 전략

### 5. Error Handling
- Graceful degradation
- Retry logic (transient errors)
- User-friendly error messages
- Structured logging

## 성능 목표

### Backend
- Document upload: < 5s (10MB PDF)
- Evaluation (1000 chunks): < 5 minutes
- Query latency: < 2s (search + answer generation)

### Frontend
- Initial load: < 2s
- Page transitions: < 500ms
- Chart rendering: < 1s

## 보안

### API
- Rate limiting
- Input validation (Pydantic)
- File type/size validation
- CORS 설정

### Data
- Environment variables for secrets
- PostgreSQL connection pooling
- Qdrant API key authentication

## 배포

### Development
```bash
docker-compose up -d
```

### Production (향후)
- Kubernetes deployment
- Multi-replica backend
- CDN for frontend
- Managed PostgreSQL (RDS)
- Managed Qdrant (cloud)

## 전체 사용자 플로우 (End-to-End) 🎯

### 시나리오 1: 전략 생성 및 문서 인덱싱

```
1️⃣ 전략 생성
   사용자 → /strategies → "New Strategy" 버튼 클릭
   → Form에서 선택:
      - Chunking: Recursive (chunk_size: 512, overlap: 50)
      - Embedding: BGE-M3
   → POST /api/v1/strategies
   → Strategy(id=1) 생성 ✅

2️⃣ 문서 업로드
   사용자 → /upload → PDF 파일 드래그&드롭
   → POST /api/v1/documents/upload
   → Document(id=1, status="uploaded") 생성 ✅

3️⃣ 문서 인덱싱 🆕
   사용자 → /documents → Document(id=1) 카드
   → "Index with Strategy" 버튼 → Strategy(id=1) 선택
   → POST /api/v1/documents/1/index { "strategy_id": 1 }
   
   Backend (Background Task):
   a. DocumentIndex 생성 (status="pending")
   b. Strategy 로드 → Factory로 Chunker, Embedder 생성
   c. Document 로드 → Chunking (progress 업데이트)
   d. Embedding 생성 (progress 업데이트)
   e. Qdrant "strategy_1" collection에 저장
      - payload: { document_id: 1, chunk_id, content, ... }
   f. DocumentIndex 업데이트 (status="completed", num_chunks=100)
   
   → DocumentIndex(id=1, status="completed") ✅
```

### 시나리오 2: 실시간 검색 및 답변 생성

```
4️⃣ 질의하기
   사용자 → /query → Strategy(id=1) 선택
   → Query 입력: "RAG란 무엇인가?"
   → (Optional) Documents 필터: [Document(id=1)]
   → POST /api/v1/query/answer
   
   Backend:
   a. Strategy(id=1) 로드 → Factory로 Embedder 생성
   b. Query embedding 생성
   c. Qdrant search:
      - collection: "strategy_1"
      - filter: document_id = 1
      - top_k: 5
   d. Retrieved chunks를 context로 조립
   e. ClaudeGenerator로 답변 생성
   
   → Response:
   {
     "answer": "RAG는 Retrieval-Augmented Generation의 약자로...",
     "sources": [
       { "document_id": 1, "chunk_id": "...", "score": 0.92 },
       ...
     ],
     "search_results": [...]
   }
   
   Frontend:
   - 답변 표시 (Markdown rendering)
   - Sources 표시 (카드 형태, 클릭 시 원문 보기)
   - 검색 결과 표시 (Relevance score와 함께)
```

### 시나리오 3: 여러 전략 성능 비교

```
5️⃣ 다른 전략 생성
   사용자 → Strategy(id=2) 생성
      - Chunking: Semantic (similarity_threshold: 0.8)
      - Embedding: Matryoshka (dimension: 512)
   
6️⃣ 동일 문서 인덱싱
   사용자 → POST /api/v1/documents/1/index { "strategy_id": 2 }
   → DocumentIndex(id=2, document_id=1, strategy_id=2) 생성
   → Qdrant "strategy_2" collection에 저장

7️⃣ 평가 실행
   사용자 → /evaluate → Strategies [1, 2] 선택
   → Document(id=1) 선택
   → Evaluation Dataset 업로드 (queries + ground truth)
   → POST /api/v1/compare
   
   Backend (병렬 실행):
   - Strategy 1 평가
   - Strategy 2 평가
   
   → Comparison Result:
   
   | Strategy | NDCG | MRR | Precision | Indexing Time |
   |----------|------|-----|-----------|---------------|
   | Strategy 1 (Recursive + BGE-M3) | 0.82 | 0.75 | 0.70 | 45s |
   | Strategy 2 (Semantic + Matryoshka) | 0.85 | 0.78 | 0.72 | 120s |
   
   Winner: Strategy 2 (NDCG: 0.85) 🏆
   
8️⃣ 결과 시각화
   Frontend:
   - Comparison Table (위 표)
   - Radar Chart (종합 성능)
   - Bar Chart (메트릭별 비교)
   - Export 버튼 (CSV, JSON)
```

### 시나리오 4: 여러 문서에서 검색

```
9️⃣ 추가 문서 인덱싱
   사용자 → Document(id=2) 업로드 및 Strategy(id=1)로 인덱싱
   → Document(id=3) 업로드 및 Strategy(id=1)로 인덱싱
   
   모두 같은 "strategy_1" collection에 저장
   (payload의 document_id로 구분)

🔟 다중 문서 검색
   사용자 → /query → Strategy(id=1) 선택
   → Query: "기술 스택은?"
   → Documents: [1, 2, 3] (전체 선택)
   → POST /api/v1/query/answer
   
   Backend:
   - collection: "strategy_1"
   - filter: document_id in [1, 2, 3]
   - 3개 문서에서 모두 검색
   
   → 답변에 여러 문서의 정보가 통합됨 ✅
```

## 다음 단계

1. ✅ Feature 브랜치 생성
2. ✅ Spec 문서 작성 (plan.md, tasks.md)
3. ⬜ Evaluation 시스템 파일 복사 및 수정
4. ⬜ Factory 패턴 구현
5. ⬜ API 엔드포인트 개발
6. ⬜ Frontend UI 개발
7. ⬜ 통합 테스트
8. ⬜ 문서화


