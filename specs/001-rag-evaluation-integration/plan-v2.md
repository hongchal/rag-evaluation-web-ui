# RAG Evaluation System - Implementation Plan v2

## 개요

사용자가 **청킹, 임베딩, 리랭킹 모듈을 선택**하여 자신만의 RAG를 구성하고, 데이터 소스를 추가하여 동기화한 후, **정량적/정성적 평가**를 통해 RAG 성능을 비교할 수 있는 웹 UI 시스템.

### 핵심 기획 의도

```
1️⃣ RAG 생성
   사용자가 청킹 + 임베딩 + 리랭킹 모듈을 선택하여 RAG 구성

2️⃣ 데이터 소스 추가
   사용자가 데이터 소스(PDF, TXT 등)를 특정 RAG에 할당

3️⃣ 데이터 동기화
   할당된 RAG로 데이터를 처리하여 vector store에 저장
   ⚠️ 중요: 어떤 RAG가 동기화했는지 기록 → 해당 RAG만 데이터 접근 가능

4️⃣ RAG 성능 평가 (정량적)
   평가 데이터셋을 업로드하여 NDCG, MRR 등 정량 지표로 측정
   동일 데이터셋으로 검색/답변 테스트도 가능

5️⃣ 검색, 답변 생성 (정성적)
   실제 RAG를 사용하여 질의하고 답변 품질 직접 확인
```

## 핵심 개념

### 1. RAG Configuration (RAG 구성)

사용자가 선택한 3가지 모듈의 조합:

```python
class RAGConfiguration:
    """사용자가 만든 RAG"""
    id: int
    name: str  # 예: "빠른 RAG", "정밀 RAG"
    description: str
    
    # 3가지 모듈 선택 (필수)
    chunking_module: str      # recursive, hierarchical, semantic, late_chunking
    chunking_params: JSON
    
    embedding_module: str     # bge_m3, matryoshka, vllm_http, jina_late_chunking
    embedding_params: JSON
    
    reranking_module: str     # cross_encoder, bm25, colbert, none
    reranking_params: JSON
    
    # Qdrant Collection
    collection_name: str      # "rag_{id}"
    
    created_at: datetime
    updated_at: datetime
```

**의미:**
- 하나의 RAG = 특정 모듈 조합
- 각 RAG는 독립적인 Qdrant collection 소유
- RAG별로 성능 비교 가능

### 2. DataSource (데이터 소스)

RAG에 추가할 데이터:

```python
class DataSource:
    """데이터 소스 (파일, URL 등)"""
    id: int
    name: str
    source_type: str          # pdf, txt, url, notion, etc.
    source_uri: str           # 파일 경로 또는 URL
    file_size: int
    content_hash: str
    
    status: str               # uploaded, pending, ready
    
    created_at: datetime
    updated_at: datetime
```

**의미:**
- DataSource는 RAG에 종속되지 않음 (재사용 가능)
- 여러 RAG에 동일 DataSource 할당 가능
- 동기화 전까지는 검색 불가

### 3. DataSourceSync (동기화 기록)

**핵심**: 어떤 RAG가 어떤 데이터를 처리했는지 기록

```python
class DataSourceSync:
    """RAG가 DataSource를 동기화한 기록"""
    id: int
    rag_id: int               # FK to RAGConfiguration
    datasource_id: int        # FK to DataSource
    
    # 동기화 상태
    status: str               # pending, syncing, completed, failed
    progress: float           # 0.0 ~ 1.0
    current_step: str         # chunking, embedding, reranking, storing
    
    # 결과 메트릭
    num_chunks: int
    sync_time: float          # seconds
    memory_usage: float       # MB
    
    error_message: Optional[str]
    
    # Timestamps
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Constraints
    UNIQUE(rag_id, datasource_id)  # 같은 RAG로 같은 소스 중복 동기화 방지
```

**의미:**
- RAG-DataSource 간 N:N 관계
- 동기화 완료된 것만 검색 가능
- 동기화 진행 상황 실시간 추적

### 4. EvaluationDataset (평가 데이터셋)

정량적 평가를 위한 ground truth:

```python
class EvaluationDataset:
    """평가용 데이터셋"""
    id: int
    name: str
    description: str
    
    # 데이터셋 파일 (JSON)
    dataset_uri: str          # 저장된 파일 경로
    
    # 메타데이터
    num_queries: int          # 쿼리 개수
    num_documents: int        # 참조 문서 개수
    
    created_at: datetime
```

**구조 (JSON):**
```json
{
  "name": "Q1 평가셋",
  "documents": [
    {"doc_id": "doc1", "content": "...", "title": "..."},
    ...
  ],
  "queries": [
    {
      "query": "RAG란 무엇인가?",
      "relevant_doc_ids": ["doc1", "doc3"],
      "expected_answer": "RAG는...",
      "difficulty": "easy"
    },
    ...
  ]
}
```

### 5. Evaluation (RAG 평가 실행)

```python
class Evaluation:
    """특정 RAG의 평가 실행"""
    id: int
    rag_id: int               # FK to RAGConfiguration
    dataset_id: int           # FK to EvaluationDataset
    
    # 평가 상태
    status: str               # pending, running, completed, failed
    progress: float
    current_step: str
    
    # 결과 (EvaluationResult FK)
    
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
```

## 기술 스택

### Backend (Python)
- **FastAPI**: REST API 서버
- **PostgreSQL**: 메타데이터, 평가 결과 저장
- **Qdrant**: Vector store (RAG별 collection)
- **SQLAlchemy**: ORM
- **Pydantic**: 데이터 검증
- **structlog**: 구조화된 로깅

### RAG Components (from tkai-agents)
#### Chunking 모듈
- **Recursive**: LangChain RecursiveCharacterTextSplitter
- **Hierarchical**: 계층적 청킹
- **Semantic**: 의미 기반 경계 탐지
- **Late Chunking**: Jina late chunking

#### Embedding 모듈
- **BGE-M3**: BAAI 다국어 임베딩 (1024-dim, Hybrid Search)
- **Matryoshka**: 차원 축소 임베딩 (64~1024)
- **VLLM HTTP**: 외부 임베딩 서버
- **Jina Late Chunking**: Late chunking 최적화

#### Reranking 모듈 (새로 추가) 🆕
- **CrossEncoder**: BAAI/bge-reranker-v2-m3
- **BM25**: 키워드 기반 재순위화
- **ColBERT**: Token-level 상호작용
- **None**: 리랭킹 없음

### Frontend (TypeScript)
- **React 19**: UI 프레임워크
- **Vite**: 빌드 도구
- **TanStack Router**: File-based routing
- **TanStack Query**: Data fetching & caching
- **shadcn/ui**: UI 컴포넌트
- **Tailwind CSS v4**: 스타일링
- **Recharts**: 차트 시각화

## 아키텍처

### 전체 구조

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│                                                          │
│  1. RAG 생성 UI (모듈 선택)                              │
│  2. 데이터 소스 관리 & RAG 할당                          │
│  3. 동기화 진행 상황                                     │
│  4. 평가 대시보드 (정량)                                 │
│  5. 검색/답변 UI (정성)                                  │
└─────────────────────┬───────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────┐
│                   Backend (FastAPI)                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  RAG Factory │  │   Sync       │  │  Evaluation  │  │
│  │  (3 Modules) │──│   Service    │──│   System     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
└─────────────┬────────────────────────────┬───────────────┘
              │                            │
      ┌───────▼────────┐          ┌───────▼────────┐
      │   PostgreSQL   │          │     Qdrant     │
      │  (Metadata &   │          │  (RAG별 분리)  │
      │   Sync 기록)   │          │  rag_1, rag_2  │
      └────────────────┘          └────────────────┘
```

### Backend 디렉토리 구조

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── rags.py              # RAG CRUD
│   │   │   ├── datasources.py       # DataSource CRUD
│   │   │   ├── sync.py              # 동기화 API
│   │   │   ├── evaluate.py          # 평가 실행
│   │   │   ├── datasets.py          # 평가 데이터셋
│   │   │   └── query.py             # 검색/답변
│   │   └── deps.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   │
│   ├── models/
│   │   ├── rag.py                   # RAGConfiguration
│   │   ├── datasource.py            # DataSource
│   │   ├── datasource_sync.py       # DataSourceSync
│   │   ├── evaluation_dataset.py    # EvaluationDataset
│   │   ├── evaluation.py            # Evaluation, EvaluationResult
│   │   └── __init__.py
│   │
│   ├── schemas/
│   │   ├── rag.py
│   │   ├── datasource.py
│   │   ├── sync.py
│   │   ├── evaluation.py
│   │   ├── dataset.py
│   │   └── query.py
│   │
│   ├── services/
│   │   ├── rag_factory.py           # 3개 모듈 Factory
│   │   ├── sync_service.py          # 동기화 관리
│   │   ├── evaluation_service.py    # 평가 관리
│   │   ├── query_service.py         # 검색/답변
│   │   ├── file_processor.py
│   │   └── qdrant_service.py
│   │
│   ├── evaluation/                  # tkai-agents
│   │   ├── evaluator.py
│   │   ├── comparator.py
│   │   ├── metrics.py
│   │   └── dataset.py
│   │
│   ├── chunking/                    # tkai-agents
│   │   └── chunkers/
│   │       ├── recursive.py
│   │       ├── hierarchical.py
│   │       ├── semantic.py
│   │       └── late_chunking.py
│   │
│   ├── embedding/                   # tkai-agents
│   │   └── embedders/
│   │       ├── bge_m3.py
│   │       ├── matryoshka.py
│   │       ├── vllm_http.py
│   │       └── jina_late_chunking.py
│   │
│   ├── reranking/                   # 🆕 새로 추가
│   │   └── rerankers/
│   │       ├── base_reranker.py
│   │       ├── cross_encoder.py
│   │       ├── bm25.py
│   │       ├── colbert.py
│   │       └── none.py
│   │
│   ├── pipeline/                    # tkai-agents
│   │   ├── query.py
│   │   └── generators/
│   │       └── claude.py
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
│   ├── routes/
│   │   ├── __root.tsx
│   │   ├── index.tsx              # 대시보드
│   │   ├── rags/
│   │   │   ├── index.tsx          # RAG 목록
│   │   │   └── create.tsx         # RAG 생성 (모듈 선택)
│   │   ├── datasources/
│   │   │   ├── index.tsx          # 데이터 소스 목록
│   │   │   └── upload.tsx         # 업로드
│   │   ├── sync.tsx               # 동기화 관리
│   │   ├── evaluate/
│   │   │   ├── index.tsx          # 평가 목록
│   │   │   ├── datasets.tsx       # 데이터셋 관리
│   │   │   └── compare.tsx        # 비교 대시보드
│   │   └── query.tsx              # 검색/답변 UI
│   │
│   ├── components/
│   │   ├── rag/
│   │   │   ├── RAGCard.tsx
│   │   │   ├── RAGForm.tsx        # 3개 모듈 선택
│   │   │   └── ModuleSelector.tsx
│   │   ├── datasource/
│   │   │   ├── DataSourceCard.tsx
│   │   │   ├── UploadZone.tsx
│   │   │   └── RAGAssignDialog.tsx
│   │   ├── sync/
│   │   │   ├── SyncProgress.tsx
│   │   │   └── SyncHistory.tsx
│   │   ├── evaluation/
│   │   │   ├── DatasetUpload.tsx
│   │   │   ├── MetricsTable.tsx
│   │   │   └── ComparisonChart.tsx
│   │   └── query/
│   │       ├── SearchBar.tsx
│   │       ├── ResultsList.tsx
│   │       └── AnswerDisplay.tsx
│   │
│   └── lib/
│       ├── api.ts
│       ├── types.ts
│       └── utils.ts
```

## 데이터 모델 상세

### RAGConfiguration
```python
id: int
name: str
description: Optional[str]

# 3가지 필수 모듈
chunking_module: str
chunking_params: JSON

embedding_module: str
embedding_params: JSON

reranking_module: str  # 필수!
reranking_params: JSON

# Qdrant Collection
collection_name: str  # "rag_{id}"

created_at: datetime
updated_at: datetime
```

### DataSource
```python
id: int
name: str
source_type: str      # pdf, txt, url
source_uri: str
file_size: int
content_hash: str
status: str           # uploaded, ready
metadata: JSON

created_at: datetime
updated_at: datetime
```

### DataSourceSync
```python
id: int
rag_id: int           # FK
datasource_id: int    # FK

status: str           # pending, syncing, completed, failed
progress: float
current_step: str

num_chunks: int
sync_time: float
memory_usage: float
error_message: Optional[str]

started_at: Optional[datetime]
completed_at: Optional[datetime]
created_at: datetime
updated_at: datetime

UNIQUE(rag_id, datasource_id)
```

### EvaluationDataset
```python
id: int
name: str
description: str
dataset_uri: str      # JSON 파일 경로
num_queries: int
num_documents: int
created_at: datetime
```

### Evaluation
```python
id: int
rag_id: int
dataset_id: int

status: str
progress: float
current_step: str
error_message: Optional[str]

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
indexing_time: float
query_latency: float
memory_usage: float
num_chunks: int

# RAG Metrics (Optional)
context_relevance: Optional[float]
answer_relevance: Optional[float]
faithfulness: Optional[float]

created_at: datetime
```

## API 엔드포인트

### 1. RAG Configuration
```
POST   /api/v1/rags                 # RAG 생성 (3개 모듈 선택)
GET    /api/v1/rags                 # RAG 목록
GET    /api/v1/rags/{id}            # RAG 조회
PUT    /api/v1/rags/{id}            # RAG 수정
DELETE /api/v1/rags/{id}            # RAG 삭제
GET    /api/v1/rags/{id}/datasources # 할당된 데이터 소스 목록
```

**RAG 생성 예시:**
```json
POST /api/v1/rags
{
  "name": "빠른 RAG",
  "description": "응답 속도 최우선",
  "chunking_module": "recursive",
  "chunking_params": { "chunk_size": 512, "overlap": 50 },
  "embedding_module": "bge_m3",
  "embedding_params": {},
  "reranking_module": "none",
  "reranking_params": {}
}
```

### 2. DataSource
```
POST   /api/v1/datasources/upload   # 파일 업로드
GET    /api/v1/datasources          # 데이터 소스 목록
GET    /api/v1/datasources/{id}     # 조회
DELETE /api/v1/datasources/{id}     # 삭제
GET    /api/v1/datasources/{id}/syncs  # 동기화 기록
```

### 3. Synchronization (핵심!) 🔑
```
POST   /api/v1/sync                 # 동기화 시작
       Body: { rag_id, datasource_id }
       
GET    /api/v1/sync                 # 모든 동기화 기록
GET    /api/v1/sync/{id}            # 동기화 상태 조회
DELETE /api/v1/sync/{id}            # 동기화 삭제 (vector도 삭제)
POST   /api/v1/sync/{id}/rebuild    # 재동기화
```

**동기화 시작 예시:**
```json
POST /api/v1/sync
{
  "rag_id": 1,
  "datasource_id": 1
}

→ DataSourceSync 생성
→ Background Task:
  1. RAG 로드 (chunking, embedding, reranking 모듈)
  2. DataSource 로드
  3. Chunking (progress 업데이트)
  4. Embedding (progress 업데이트)
  5. Reranking 준비
  6. Qdrant "rag_1" collection에 저장
     - payload: { datasource_id: 1, chunk_id, content, ... }
  7. DataSourceSync 업데이트 (status="completed")
```

### 4. Evaluation Dataset
```
POST   /api/v1/datasets/upload      # 평가 데이터셋 업로드 (JSON)
GET    /api/v1/datasets             # 데이터셋 목록
GET    /api/v1/datasets/{id}        # 조회
DELETE /api/v1/datasets/{id}        # 삭제
```

### 5. Evaluation
```
POST   /api/v1/evaluations/run      # 단일 RAG 평가
       Body: { rag_id, dataset_id }
       
POST   /api/v1/evaluations/compare  # 여러 RAG 비교
       Body: { rag_ids: [1,2,3], dataset_id }
       
GET    /api/v1/evaluations/{id}     # 평가 결과 조회
GET    /api/v1/evaluations/{id}/status  # 진행 상황
POST   /api/v1/evaluations/{id}/cancel  # 취소
```

### 6. Query (검색/답변)
```
POST   /api/v1/query/search         # 벡터 검색
       Body: {
         rag_id: int,
         query: str,
         datasource_ids: [int],  # Optional
         top_k: int
       }
       
POST   /api/v1/query/answer         # 검색 + LLM 답변
       Body: {
         rag_id: int,
         query: str,
         datasource_ids: [int],  # Optional
         top_k: int
       }
```

## Qdrant Collection 전략

### RAG별 독립 Collection

```
Collection 이름: "rag_{rag_id}"
예: "rag_1", "rag_2", "rag_3"

구조:
- 하나의 RAG = 하나의 collection
- 여러 DataSource가 같은 collection에 저장
- Payload에 datasource_id 포함하여 필터링

Payload:
{
  "datasource_id": 1,
  "chunk_id": "ds_1_chunk_0",
  "content": "...",
  "metadata": {...}
}

검색 시:
- collection_name = f"rag_{rag_id}"
- filter: datasource_id in [1, 2, 3]  (optional)
```

### 평가용 임시 Collection

```
Collection 이름: "eval_{hash}"
예: "eval_a1b2c3d4"

- 평가 시에만 생성
- 평가 완료 후 자동 삭제
- Production collection과 분리
```

**장점:**
- RAG별로 완전히 격리
- 동기화한 DataSource만 검색 가능
- 성능 비교 시 공정함 보장

## 전체 사용자 플로우 (End-to-End)

### 시나리오 1: RAG 생성 및 데이터 동기화

```
1️⃣ RAG 생성
   사용자 → /rags/create
   → 모듈 선택:
      - Chunking: Recursive (512, overlap 50)
      - Embedding: BGE-M3
      - Reranking: CrossEncoder
   → POST /api/v1/rags
   → RAGConfiguration(id=1) 생성 ✅

2️⃣ 데이터 소스 업로드
   사용자 → /datasources/upload
   → PDF 파일 드래그&드롭
   → POST /api/v1/datasources/upload
   → DataSource(id=1, status="ready") ✅

3️⃣ 데이터 동기화 (핵심!) 🔑
   사용자 → /sync
   → RAG(id=1) 선택
   → DataSource(id=1) 선택
   → POST /api/v1/sync { rag_id: 1, datasource_id: 1 }
   
   Backend (Background Task):
   a. DataSourceSync 생성 (status="pending")
   b. RAG(id=1) 로드
      - ChunkerFactory → RecursiveChunker
      - EmbedderFactory → BGEM3Embedder
      - RerankerFactory → CrossEncoderReranker
   c. DataSource(id=1) 로드 → PDF 파싱
   d. Chunking (progress: 0% → 33%)
   e. Embedding (progress: 33% → 66%)
   f. Qdrant "rag_1" collection에 저장 (progress: 66% → 100%)
      - payload: { datasource_id: 1, chunk_id, content }
   g. DataSourceSync 업데이트:
      - status="completed"
      - num_chunks=100
      - sync_time=45.2s
   
   → DataSourceSync(id=1, status="completed") ✅
   
   Frontend:
   - 실시간 progress bar 업데이트
   - 완료 시 알림
```

### 시나리오 2: 실시간 검색 및 답변 (정성적 평가)

```
4️⃣ 검색 및 답변 생성
   사용자 → /query
   → RAG(id=1) 선택
   → Query 입력: "RAG의 장점은?"
   → (Optional) DataSource(id=1) 선택 또는 전체
   → "Answer" 버튼 클릭
   → POST /api/v1/query/answer
   
   Backend:
   a. RAG(id=1) 로드
      - EmbedderFactory → BGEM3Embedder
      - RerankerFactory → CrossEncoderReranker
   b. Query embedding 생성
   c. Qdrant search:
      - collection: "rag_1"
      - filter: datasource_id = 1 (if specified)
      - top_k: 20 (reranking 전)
   d. Reranking:
      - CrossEncoder로 top 20 → top 5 재순위화
   e. Context 조립 (top 5 chunks)
   f. ClaudeGenerator로 답변 생성
   
   → Response:
   {
     "answer": "RAG의 주요 장점은...",
     "sources": [
       {
         "datasource_id": 1,
         "datasource_name": "rag_paper.pdf",
         "chunk_id": "...",
         "content": "...",
         "score": 0.92
       },
       ...
     ],
     "search_results": [...]
   }
   
   Frontend:
   - 답변 표시 (Markdown)
   - Sources 카드 (클릭 시 원문)
   - Relevance score 시각화
   
   사용자가 직접 품질 확인 → 정성적 평가 ✅
```

### 시나리오 3: 다른 RAG와 성능 비교

```
5️⃣ 다른 RAG 생성
   사용자 → RAG(id=2) 생성
      - Chunking: Semantic (threshold 0.8)
      - Embedding: Matryoshka (512-dim)
      - Reranking: BM25

6️⃣ 동일 데이터 동기화
   사용자 → POST /api/v1/sync { rag_id: 2, datasource_id: 1 }
   → DataSourceSync(id=2) 생성
   → Qdrant "rag_2" collection에 저장
   
   ⚠️ 중요: 
   - RAG 1: "rag_1" collection (Recursive + BGE-M3 + CrossEncoder)
   - RAG 2: "rag_2" collection (Semantic + Matryoshka + BM25)
   - 완전히 독립적으로 처리됨

7️⃣ 평가 데이터셋 업로드
   사용자 → /evaluate/datasets
   → JSON 파일 업로드
   ```json
   {
     "name": "Q1 평가셋",
     "documents": [...],
     "queries": [
       {
         "query": "RAG의 장점은?",
         "relevant_doc_ids": ["doc1", "doc3"],
         "expected_answer": "...",
         "difficulty": "easy"
       },
       ...
     ]
   }
   ```
   → POST /api/v1/datasets/upload
   → EvaluationDataset(id=1) 생성 ✅

8️⃣ 여러 RAG 비교 평가
   사용자 → /evaluate/compare
   → RAG [1, 2] 선택
   → Dataset(id=1) 선택
   → "Compare" 버튼
   → POST /api/v1/evaluations/compare
   
   Backend (병렬 실행):
   - RAG 1 평가 (rag_1 collection)
   - RAG 2 평가 (rag_2 collection)
   
   → Comparison Result:
   
   | RAG | Chunking | Embedding | Reranking | NDCG | MRR | Precision | Sync Time |
   |-----|----------|-----------|-----------|------|-----|-----------|-----------|
   | RAG 1 | Recursive | BGE-M3 | CrossEncoder | 0.85 | 0.78 | 0.72 | 45s |
   | RAG 2 | Semantic | Matryoshka | BM25 | 0.82 | 0.75 | 0.70 | 120s |
   
   Winner: RAG 1 (NDCG: 0.85) 🏆
   
9️⃣ 결과 시각화
   Frontend:
   - Comparison Table
   - Radar Chart (종합 성능)
   - Bar Chart (메트릭별)
   - Export CSV/JSON

   정량적 평가 완료 ✅
```

### 시나리오 4: 평가 데이터셋으로 정성 확인

```
🔟 평가 쿼리로 검색 테스트
   사용자 → /query
   → RAG(id=1) 선택
   → 평가 데이터셋의 쿼리 복사:
      "RAG의 장점은?"
   → POST /api/v1/query/answer
   
   → 답변과 ground truth 비교 가능
   → 정량 지표(NDCG)와 실제 답변 품질 대조
   
   정량 + 정성 모두 확인 ✅
```

### 시나리오 5: 여러 데이터 소스 통합 검색

```
1️⃣1️⃣ 추가 데이터 소스 동기화
   사용자:
   - DataSource(id=2) 업로드 → RAG(id=1)로 동기화
   - DataSource(id=3) 업로드 → RAG(id=1)로 동기화
   
   모두 "rag_1" collection에 저장
   (payload의 datasource_id로 구분)

1️⃣2️⃣ 통합 검색
   사용자 → /query
   → RAG(id=1) 선택
   → Query: "전체 시스템 아키텍처는?"
   → DataSource: "All" (전체 선택)
   → POST /api/v1/query/answer
   
   Backend:
   - collection: "rag_1"
   - filter: datasource_id in [1, 2, 3]
   - 3개 소스 모두에서 검색
   
   → 답변에 여러 소스의 정보 통합 ✅
```

## 주요 컴포넌트

### 1. RAGFactory (3개 모듈 Factory 통합)

```python
class RAGFactory:
    """RAG 구성의 3가지 모듈을 생성하는 통합 Factory"""
    
    @staticmethod
    def create_chunker(module: str, params: dict):
        """Chunker 생성"""
        if module == "recursive":
            return RecursiveChunker(**params)
        elif module == "hierarchical":
            return HierarchicalChunker(**params)
        elif module == "semantic":
            return SemanticChunker(**params)
        elif module == "late_chunking":
            return LateChunkingChunker(**params)
        else:
            raise ValueError(f"Unknown chunker: {module}")
    
    @staticmethod
    def create_embedder(module: str, params: dict):
        """Embedder 생성 (Singleton)"""
        # 모델 중복 로딩 방지
        if module == "bge_m3":
            return BGEM3Embedder()  # Singleton
        elif module == "matryoshka":
            return MatryoshkaEmbedder(**params)
        elif module == "vllm_http":
            return VLLMHTTPEmbedder(**params)
        elif module == "jina_late_chunking":
            return JinaLateChunkingEmbedder()
        else:
            raise ValueError(f"Unknown embedder: {module}")
    
    @staticmethod
    def create_reranker(module: str, params: dict):
        """Reranker 생성 🆕"""
        if module == "none":
            return NoneReranker()  # Pass-through
        elif module == "cross_encoder":
            return CrossEncoderReranker(**params)
        elif module == "bm25":
            return BM25Reranker(**params)
        elif module == "colbert":
            return ColBERTReranker(**params)
        else:
            raise ValueError(f"Unknown reranker: {module}")
    
    @classmethod
    def create_rag(cls, config: RAGConfiguration):
        """RAG Configuration으로부터 전체 모듈 생성"""
        chunker = cls.create_chunker(
            config.chunking_module,
            config.chunking_params
        )
        embedder = cls.create_embedder(
            config.embedding_module,
            config.embedding_params
        )
        reranker = cls.create_reranker(
            config.reranking_module,
            config.reranking_params
        )
        
        return chunker, embedder, reranker
```

### 2. SyncService (동기화 관리)

```python
class SyncService:
    """데이터 동기화 관리"""
    
    async def sync_datasource(
        self,
        rag_id: int,
        datasource_id: int
    ) -> DataSourceSync:
        """
        DataSource를 RAG로 동기화
        
        1. RAG 로드
        2. DataSource 로드
        3. Chunking
        4. Embedding
        5. Qdrant에 저장 (rag_{id} collection)
        6. DataSourceSync 기록
        """
        # DataSourceSync 생성
        sync = DataSourceSync(
            rag_id=rag_id,
            datasource_id=datasource_id,
            status="pending"
        )
        db.add(sync)
        db.commit()
        
        # Background Task 실행
        background_tasks.add_task(
            self._sync_background,
            sync.id
        )
        
        return sync
    
    async def _sync_background(self, sync_id: int):
        """Background 동기화 작업"""
        sync = db.get(DataSourceSync, sync_id)
        sync.status = "syncing"
        sync.started_at = datetime.utcnow()
        db.commit()
        
        try:
            # 1. RAG 로드
            rag = db.get(RAGConfiguration, sync.rag_id)
            chunker, embedder, reranker = RAGFactory.create_rag(rag)
            
            # 2. DataSource 로드
            datasource = db.get(DataSource, sync.datasource_id)
            content = load_file(datasource.source_uri)
            
            # 3. Chunking
            sync.current_step = "chunking"
            sync.progress = 0.0
            db.commit()
            
            chunks = chunker.chunk(content)
            
            sync.progress = 0.33
            db.commit()
            
            # 4. Embedding
            sync.current_step = "embedding"
            db.commit()
            
            embeddings = embedder.embed_texts([c.content for c in chunks])
            
            sync.progress = 0.66
            db.commit()
            
            # 5. Qdrant 저장
            sync.current_step = "storing"
            db.commit()
            
            collection_name = f"rag_{rag.id}"
            self.qdrant.add_chunks(
                collection_name,
                chunks,
                embeddings,
                payload_extra={"datasource_id": datasource.id}
            )
            
            # 6. 완료
            sync.status = "completed"
            sync.progress = 1.0
            sync.num_chunks = len(chunks)
            sync.completed_at = datetime.utcnow()
            sync.sync_time = (sync.completed_at - sync.started_at).total_seconds()
            db.commit()
            
        except Exception as e:
            sync.status = "failed"
            sync.error_message = str(e)
            db.commit()
            logger.error("sync_failed", sync_id=sync_id, error=str(e))
```

### 3. QueryService (검색/답변)

```python
class QueryService:
    """검색 및 답변 생성"""
    
    async def search(
        self,
        rag_id: int,
        query: str,
        datasource_ids: Optional[List[int]] = None,
        top_k: int = 5
    ) -> List[RetrievedChunk]:
        """
        벡터 검색 (reranking 포함)
        """
        # 1. RAG 로드
        rag = db.get(RAGConfiguration, rag_id)
        _, embedder, reranker = RAGFactory.create_rag(rag)
        
        # 2. Query embedding
        query_embedding = embedder.embed_query(query)
        
        # 3. Qdrant search (reranking 전 더 많이 검색)
        collection_name = f"rag_{rag_id}"
        
        # Filter by datasource_ids if specified
        filter_conditions = None
        if datasource_ids:
            filter_conditions = {
                "datasource_id": {"$in": datasource_ids}
            }
        
        # Top-K * 4 검색 (reranking 위해 여유있게)
        initial_k = top_k * 4
        results = self.qdrant.search(
            collection_name,
            query_embedding,
            top_k=initial_k,
            filter_conditions=filter_conditions
        )
        
        # 4. Reranking
        if rag.reranking_module != "none":
            results = reranker.rerank(
                query=query,
                documents=results,
                top_k=top_k
            )
        else:
            results = results[:top_k]
        
        return results
    
    async def answer(
        self,
        rag_id: int,
        query: str,
        datasource_ids: Optional[List[int]] = None,
        top_k: int = 5
    ) -> AnswerResponse:
        """
        검색 + LLM 답변 생성
        """
        # 1. 검색
        search_results = await self.search(
            rag_id, query, datasource_ids, top_k
        )
        
        # 2. Context 조립
        context = "\n\n".join([
            f"[{i+1}] {r.content}"
            for i, r in enumerate(search_results)
        ])
        
        # 3. LLM 답변 생성
        generator = ClaudeGenerator()
        answer, tokens = generator.generate(
            question=query,
            context=context
        )
        
        return AnswerResponse(
            answer=answer,
            sources=search_results,
            tokens_used=tokens
        )
```

### 4. EvaluationService (평가 실행)

```python
class EvaluationService:
    """RAG 평가 실행"""
    
    async def evaluate_rag(
        self,
        rag_id: int,
        dataset_id: int
    ) -> EvaluationResult:
        """
        단일 RAG 평가
        """
        # 1. Evaluation 생성
        evaluation = Evaluation(
            rag_id=rag_id,
            dataset_id=dataset_id,
            status="pending"
        )
        db.add(evaluation)
        db.commit()
        
        # 2. Background Task
        background_tasks.add_task(
            self._evaluate_background,
            evaluation.id
        )
        
        return evaluation
    
    async def _evaluate_background(self, evaluation_id: int):
        """Background 평가 작업"""
        evaluation = db.get(Evaluation, evaluation_id)
        evaluation.status = "running"
        evaluation.started_at = datetime.utcnow()
        db.commit()
        
        try:
            # 1. RAG & Dataset 로드
            rag = db.get(RAGConfiguration, evaluation.rag_id)
            dataset = EvaluationDataset.load(evaluation.dataset_id)
            
            chunker, embedder, reranker = RAGFactory.create_rag(rag)
            
            # 2. RAGEvaluator 생성 (tkai-agents)
            evaluator = RAGEvaluator(
                chunker=chunker,
                embedder=embedder,
                vector_store=QdrantStore(),
                config=EvaluationConfig(top_k=10)
            )
            
            # 3. 평가 실행
            result = await evaluator.evaluate(
                dataset=dataset,
                strategy_name=rag.name
            )
            
            # 4. 결과 저장
            eval_result = EvaluationResult(
                evaluation_id=evaluation.id,
                ndcg_at_k=result.metrics.retrieval.ndcg_at_k,
                mrr=result.metrics.retrieval.mrr,
                precision_at_k=result.metrics.retrieval.precision_at_k,
                recall_at_k=result.metrics.retrieval.recall_at_k,
                # ... 나머지 메트릭
            )
            db.add(eval_result)
            
            evaluation.status = "completed"
            evaluation.completed_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            evaluation.status = "failed"
            evaluation.error_message = str(e)
            db.commit()
    
    async def compare_rags(
        self,
        rag_ids: List[int],
        dataset_id: int
    ) -> ComparisonResult:
        """
        여러 RAG 비교 (병렬 실행)
        """
        # 각 RAG에 대해 평가 실행
        evaluations = []
        for rag_id in rag_ids:
            eval = await self.evaluate_rag(rag_id, dataset_id)
            evaluations.append(eval)
        
        # 모든 평가 완료 대기...
        # 결과 집계 및 비교 테이블 생성
        # ...
        
        return comparison_result
```

## 기술적 고려사항

### 1. Async Processing
- FastAPI Background Tasks로 동기화/평가 실행
- Progress 업데이트 (polling 1초 간격)
- 취소 기능 (status 체크)

### 2. Qdrant Collection 관리
- RAG별 독립 collection: `rag_{id}`
- Payload에 datasource_id 포함
- 동기화 삭제 시 해당 chunk만 삭제

### 3. 모듈 캐싱
- Embedder Singleton (모델 중복 로딩 방지)
- Reranker 모델 캐싱
- GPU 메모리 최적화

### 4. 에러 핸들링
- 동기화 실패 시 롤백
- 부분 완료 지원 (재시작)
- 상세 에러 메시지

### 5. 성능 최적화
- Batch embedding
- Parallel evaluation
- Collection pre-warming

## 다음 단계

1. ✅ Feature 브랜치 생성
2. ✅ Spec 문서 작성 (plan-v2.md, tasks-v2.md)
3. ⬜ Reranking 모듈 구현
4. ⬜ 용어 변경 (Strategy→RAG, Document→DataSource 등)
5. ⬜ SyncService 구현
6. ⬜ 통합 테스트
7. ⬜ Frontend UI 개발


