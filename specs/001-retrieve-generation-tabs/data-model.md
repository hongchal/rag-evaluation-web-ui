# Data Model

**Feature**: Retrieve & Generation Tabs Separation
**Date**: 2025-10-28
**Status**: Complete

## Overview

이 문서는 Retrieve/Generation 탭 기능에 필요한 데이터 모델을 정의합니다. 각 엔티티는 명세서의 Key Entities와 기능 요구사항을 기반으로 설계되었습니다.

## Storage Classification

| Entity | Storage Location | Persistence | Rationale |
|--------|------------------|-------------|-----------|
| ChatSession | Frontend (React State) | Session-scoped | 명세서 Assumption: 브라우저 세션만 유지 |
| Message | Frontend (React State) | Session-scoped | ChatSession의 일부 |
| ModelConfig | Frontend (React State) | Session-scoped | 사용자별 실시간 설정 |
| GenerationConfig | Backend (Transient) | Request-scoped | API 요청 파라미터 |
| GenerationResult | Backend (Transient) | Request-scoped | API 응답 |
| Pipeline | Backend (PostgreSQL) | Permanent | 기존 모델 (수정 없음) |
| EvaluationDataset | Backend (PostgreSQL) | Permanent | 기존 모델 (수정 없음) |

## Frontend Models (React State)

### 1. ChatSession

채팅 세션의 전체 상태를 관리하는 루트 엔티티입니다.

```typescript
interface ChatSession {
  // Identification
  id: string;  // UUID v4
  
  // Configuration
  pipelineId: number;
  modelConfig: ModelConfig;
  
  // Content
  messages: Message[];
  
  // Metadata
  createdAt: Date;
}
```

**Fields**:
- `id`: 세션의 고유 식별자 (UUID v4 형식)
- `pipelineId`: 사용 중인 파이프라인 ID (검색에 사용)
- `modelConfig`: 생성 모델 설정
- `messages`: 대화 메시지 배열 (시간순 정렬)
- `createdAt`: 세션 생성 시간

**Validation Rules**:
- `id`: UUID v4 형식 (자동 생성)
- `pipelineId`: 양수, 존재하는 Pipeline ID
- `messages`: 최대 50개 (초과 시 오래된 메시지부터 제거)
- `createdAt`: ISO 8601 timestamp

**State Transitions**:
- `CREATED`: 새로운 세션 생성
- `ACTIVE`: 메시지 주고받는 중
- `CLEARED`: 사용자가 명시적으로 초기화

**Relationships**:
- `1 ChatSession` → `N Messages` (composition, cascade delete)
- `1 ChatSession` → `1 ModelConfig` (composition)
- `1 ChatSession` → `1 Pipeline` (reference, external)

---

### 2. Message

개별 대화 메시지를 나타냅니다 (사용자 질문 또는 AI 답변).

```typescript
interface Message {
  // Identification
  id: string;  // UUID v4
  
  // Content
  role: 'user' | 'assistant';
  content: string;
  
  // References (assistant only)
  sources?: RetrievedChunk[];
  
  // Metadata
  timestamp: Date;
}
```

**Fields**:
- `id`: 메시지 고유 식별자 (UUID v4)
- `role`: 메시지 발신자 (`user` = 사용자 질문, `assistant` = AI 답변)
- `content`: 메시지 내용 (텍스트)
- `sources`: 참조된 문서 청크 (assistant 메시지만, optional)
- `timestamp`: 메시지 생성 시간

**Validation Rules**:
- `role`: `'user'` 또는 `'assistant'` 만 허용
- `content`: 1자 이상, 10,000자 이하
- `sources`: assistant 메시지에만 존재, 최대 20개
- `timestamp`: ISO 8601 timestamp

**Examples**:

```typescript
// User message
{
  id: "550e8400-e29b-41d4-a716-446655440000",
  role: "user",
  content: "RAG 시스템이란 무엇인가요?",
  timestamp: new Date("2025-10-28T10:30:00Z")
}

// Assistant message
{
  id: "550e8400-e29b-41d4-a716-446655440001",
  role: "assistant",
  content: "RAG(Retrieval-Augmented Generation)는 검색 기반 생성 모델입니다...",
  sources: [
    {
      chunk_id: "doc1_chunk1",
      content: "RAG는 ...",
      score: 0.92,
      ...
    }
  ],
  timestamp: new Date("2025-10-28T10:30:15Z")
}
```

---

### 3. ModelConfig

생성 모델의 설정을 정의합니다.

```typescript
type ModelType = 'claude' | 'vllm';

interface ModelConfig {
  // Model Selection
  type: ModelType;
  modelName: string;
  
  // Authentication (type-specific)
  apiKey?: string;      // Claude only
  endpoint?: string;    // vLLM only
  
  // Generation Parameters
  parameters: GenerationParams;
}
```

**Fields**:
- `type`: 모델 타입 (`'claude'` 또는 `'vllm'`)
- `modelName`: 모델 이름 (e.g., "claude-3-sonnet-20240229", "llama-2-70b")
- `apiKey`: Claude API 키 (Claude 타입만)
- `endpoint`: vLLM 서버 URL (vLLM 타입만)
- `parameters`: 생성 파라미터

**Validation Rules**:
- `type`: `'claude'` 또는 `'vllm'` 만 허용
- `modelName`: 비어있지 않은 문자열
- `apiKey`: Claude 타입일 때 필수, sk-ant-로 시작
- `endpoint`: vLLM 타입일 때 필수, http(s):// URL 형식
- `parameters`: GenerationParams 검증 규칙 적용

**Type-Specific Validation**:

```typescript
// Claude
if (config.type === 'claude') {
  assert(config.apiKey !== undefined, "API key required for Claude");
  assert(config.apiKey.startsWith('sk-ant-'), "Invalid Claude API key format");
  assert(config.endpoint === undefined, "Endpoint not used for Claude");
}

// vLLM
if (config.type === 'vllm') {
  assert(config.endpoint !== undefined, "Endpoint required for vLLM");
  assert(config.endpoint.match(/^https?:\/\//), "Invalid endpoint URL");
  assert(config.apiKey === undefined, "API key not used for vLLM");
}
```

---

### 4. GenerationParams

모델 생성 파라미터를 정의합니다.

```typescript
interface GenerationParams {
  temperature: number;    // 0.0 ~ 1.0
  maxTokens: number;      // 100 ~ 4000
  topP: number;           // 0.0 ~ 1.0
}
```

**Fields**:
- `temperature`: 생성 다양성 제어 (0 = deterministic, 1 = creative)
- `maxTokens`: 최대 생성 토큰 수
- `topP`: Nucleus sampling 파라미터

**Validation Rules**:
- `temperature`: 0.0 이상 1.0 이하
- `maxTokens`: 100 이상 4000 이하
- `topP`: 0.0 이상 1.0 이하

**Default Values**:
```typescript
const DEFAULT_GENERATION_PARAMS: GenerationParams = {
  temperature: 0.7,
  maxTokens: 1000,
  topP: 0.9,
};
```

---

### 5. RetrievedChunk (Reference)

검색된 문서 청크 (기존 API 스키마 재사용).

```typescript
interface RetrievedChunk {
  chunk_id: string;
  datasource_id: number;
  content: string;
  score: number;
  metadata?: Record<string, any>;
  is_golden?: boolean;  // Test pipeline only
}
```

**Fields**:
- `chunk_id`: Qdrant의 청크 ID
- `datasource_id`: 원본 데이터소스 ID
- `content`: 청크 내용 (텍스트)
- `score`: 검색 관련도 점수 (0.0 ~ 1.0)
- `metadata`: 추가 메타데이터 (페이지 번호, 제목 등)
- `is_golden`: 정답 청크 여부 (test pipeline만)

**Note**: 이 모델은 기존 `/api/query/search` 응답에서 정의되어 있으므로 수정 없이 재사용합니다.

---

## Backend Models (API Request/Response)

### 6. AnswerRequest (Backend API)

답변 생성 요청을 나타냅니다.

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class GenerationParamsRequest(BaseModel):
    """Generation parameters for answer generation"""
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1000, ge=100, le=4000)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)

class ModelConfigRequest(BaseModel):
    """Model configuration for answer generation"""
    type: str = Field(..., description="Model type: 'claude' or 'vllm'")
    model_name: str = Field(..., description="Model name")
    api_key: Optional[str] = Field(None, description="API key for Claude")
    endpoint: Optional[str] = Field(None, description="Endpoint URL for vLLM")
    parameters: GenerationParamsRequest = Field(default_factory=GenerationParamsRequest)
    
    @validator('type')
    def validate_type(cls, v):
        if v not in ['claude', 'vllm']:
            raise ValueError("type must be 'claude' or 'vllm'")
        return v
    
    @validator('api_key')
    def validate_api_key(cls, v, values):
        if values.get('type') == 'claude' and not v:
            raise ValueError("api_key is required for Claude")
        if values.get('type') == 'claude' and v and not v.startswith('sk-ant-'):
            raise ValueError("Invalid Claude API key format")
        return v
    
    @validator('endpoint')
    def validate_endpoint(cls, v, values):
        if values.get('type') == 'vllm' and not v:
            raise ValueError("endpoint is required for vLLM")
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("endpoint must be a valid HTTP(S) URL")
        return v

class AnswerRequest(BaseModel):
    """Request for answer generation with RAG"""
    pipeline_id: int = Field(..., description="Pipeline ID for retrieval")
    query: str = Field(..., min_length=1, max_length=10000, description="User question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    model_config: ModelConfigRequest = Field(..., description="Model configuration")
```

**Validation Rules**:
- `pipeline_id`: 양수
- `query`: 1자 이상 10,000자 이하
- `top_k`: 1 이상 20 이하
- `model_config`: ModelConfigRequest 검증 규칙 적용

---

### 7. AnswerResponse (Backend API)

답변 생성 응답을 나타냅니다.

```python
from typing import List

class AnswerResponse(BaseModel):
    """Response from answer generation"""
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    sources: List[RetrievedChunk] = Field(..., description="Retrieved chunks used")
    
    # Performance metrics
    tokens_used: int = Field(..., description="Total tokens used (input + output)")
    generation_time: float = Field(..., description="Total generation time (seconds)")
    retrieval_time: float = Field(..., description="Retrieval time (seconds)")
    llm_time: float = Field(..., description="LLM generation time (seconds)")
```

**Fields**:
- `query`: 원본 질문
- `answer`: 생성된 답변
- `sources`: 참조된 문서 청크 (최대 `top_k`개)
- `tokens_used`: 사용된 총 토큰 수 (입력 + 출력)
- `generation_time`: 전체 생성 시간 (검색 + LLM)
- `retrieval_time`: 검색 시간
- `llm_time`: LLM 생성 시간

**Performance Constraints**:
- `generation_time`: 목표 < 30초 (Success Criteria SC-002)
- `retrieval_time`: 목표 < 3초 (Success Criteria SC-001)
- `llm_time`: 목표 < 27초 (generation_time - retrieval_time)

---

### 8. PipelineFilterRequest (Backend API)

파이프라인 필터링 요청 (Query Parameter).

```python
from typing import Optional
from fastapi import Query

# Used as FastAPI dependency
def get_pipeline_filter(
    dataset_id: Optional[int] = Query(None, description="Filter by evaluation dataset ID"),
    pipeline_type: Optional[str] = Query(None, description="Filter by pipeline type: 'normal' or 'test'"),
) -> dict:
    """Extract pipeline filter parameters from query"""
    filters = {}
    if dataset_id is not None:
        filters['dataset_id'] = dataset_id
    if pipeline_type is not None:
        if pipeline_type not in ['normal', 'test']:
            raise ValueError("pipeline_type must be 'normal' or 'test'")
        filters['pipeline_type'] = pipeline_type
    return filters
```

**Query Parameters**:
- `dataset_id`: 평가 데이터셋 ID (optional)
- `pipeline_type`: 파이프라인 타입 (optional)

**Examples**:
- `/api/pipelines` → 모든 파이프라인
- `/api/pipelines?dataset_id=1` → Dataset 1을 사용하는 파이프라인만
- `/api/pipelines?pipeline_type=test` → Test 파이프라인만
- `/api/pipelines?dataset_id=1&pipeline_type=test` → Dataset 1의 Test 파이프라인만

---

## Backend Internal Models (Service Layer)

### 9. GenerationConfig (Internal)

서비스 계층에서 사용하는 생성 설정 (Python dataclass).

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class GenerationConfig:
    """Configuration for text generation (internal)"""
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 0.9
    stop_sequences: Optional[List[str]] = None
```

**Fields**:
- `temperature`: 0.0 ~ 1.0
- `max_tokens`: 100 ~ 4000
- `top_p`: 0.0 ~ 1.0
- `stop_sequences`: 생성 중단 시퀀스 (optional)

---

### 10. GenerationResult (Internal)

서비스 계층 생성 결과 (Python dataclass).

```python
@dataclass
class GenerationResult:
    """Result of text generation (internal)"""
    answer: str
    tokens_used: int
    generation_time: float
    model_name: str
```

**Fields**:
- `answer`: 생성된 답변 텍스트
- `tokens_used`: 사용된 총 토큰 수
- `generation_time`: LLM 생성 시간 (seconds)
- `model_name`: 사용된 모델 이름

---

## Database Models (No Changes)

기존 PostgreSQL 모델은 수정하지 않습니다.

### Pipeline (Existing)

```python
class Pipeline(Base):
    __tablename__ = "pipelines"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    pipeline_type = Column(Enum(PipelineType), nullable=False)
    rag_id = Column(Integer, ForeignKey("rag_configurations.id"))
    dataset_id = Column(Integer, ForeignKey("evaluation_datasets.id"), nullable=True)
    # ... other fields
```

**Used for**:
- 파이프라인 선택 (Retrieve/Generation 탭)
- Dataset 기반 필터링 (Evaluation 탭)

### EvaluationDataset (Existing)

```python
class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    # ... other fields
```

**Used for**:
- Dataset 선택 드롭다운 (Evaluation 탭)
- Pipeline 필터링 기준

---

## Data Flow Diagrams

### Flow 1: Chat Message Generation

```
User Input (Frontend)
  ↓
[ChatSession State]
  ├─ Add user message
  ├─ Extract: pipelineId, query, modelConfig
  └─ Call API: POST /api/query/answer
      ↓
Backend API Handler
  ├─ Validate AnswerRequest
  └─ Call QueryService.answer()
      ↓
QueryService
  ├─ Call search() → retrieve chunks
  ├─ Format prompt with chunks
  ├─ Call GeneratorFactory.create()
  └─ Call generator.generate()
      ↓
Generator (Claude/vLLM)
  ├─ Make external API call
  └─ Return GenerationResult
      ↓
QueryService
  └─ Build AnswerResponse
      ↓
Frontend
  ├─ Receive response
  ├─ Add assistant message to ChatSession
  └─ Render in UI
```

### Flow 2: Pipeline Filtering by Dataset

```
User Action (Frontend)
  ↓
[Select Dataset from Dropdown]
  ├─ datasetId = selectedValue
  └─ Call API: GET /api/pipelines?dataset_id={id}
      ↓
Backend API Handler
  ├─ Extract query parameter: dataset_id
  └─ Call PipelineService.list_pipelines(dataset_id)
      ↓
PipelineService
  ├─ Query DB: filter by dataset_id
  └─ Return Pipeline[]
      ↓
Frontend
  ├─ Receive filtered pipelines
  └─ Update UI pipeline list
```

---

## Entity Relationship Diagram

```
┌─────────────────────┐
│   ChatSession       │ (Frontend State)
│─────────────────────│
│ id: string          │
│ pipelineId: number  │────┐
│ modelConfig: {}     │    │
│ messages: []        │    │
│ createdAt: Date     │    │
└──────┬──────────────┘    │
       │                   │
       │ 1:N               │ N:1
       │                   │
       ▼                   ▼
┌─────────────────────┐  ┌──────────────────┐
│   Message           │  │   Pipeline       │ (Database)
│─────────────────────│  │──────────────────│
│ id: string          │  │ id: int          │
│ role: enum          │  │ name: string     │
│ content: string     │  │ dataset_id: int  │──┐
│ sources: []         │  │ rag_id: int      │  │
│ timestamp: Date     │  └──────────────────┘  │
└─────────────────────┘                        │
                                               │ N:1
                                               │
                                               ▼
                                        ┌──────────────────────┐
                                        │ EvaluationDataset    │
                                        │──────────────────────│
                                        │ id: int              │
                                        │ name: string         │
                                        └──────────────────────┘
```

---

## Validation Summary

| Entity | Key Validations | Error Messages |
|--------|-----------------|----------------|
| ChatSession | messages.length <= 50 | "Chat session has reached maximum message limit" |
| Message | content.length between 1-10000 | "Message content must be 1-10000 characters" |
| ModelConfig (Claude) | apiKey.startsWith('sk-ant-') | "Invalid Claude API key format" |
| ModelConfig (vLLM) | endpoint matches URL pattern | "Invalid vLLM endpoint URL" |
| GenerationParams | temperature in [0, 1] | "Temperature must be between 0.0 and 1.0" |
| GenerationParams | maxTokens in [100, 4000] | "Max tokens must be between 100 and 4000" |
| AnswerRequest | pipeline_id > 0 | "Invalid pipeline ID" |
| AnswerRequest | query.length between 1-10000 | "Query must be 1-10000 characters" |
| AnswerRequest | top_k in [1, 20] | "Top K must be between 1 and 20" |

---

## Next Steps

1. ✅ Data model definition complete
2. 🔄 Create OpenAPI contracts for API endpoints
3. 🔄 Create quickstart.md for developers
4. ⏳ Implement models in code

