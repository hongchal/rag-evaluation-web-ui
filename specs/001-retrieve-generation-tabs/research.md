# Research & Technical Decisions

**Feature**: Retrieve & Generation Tabs Separation
**Date**: 2025-10-28
**Status**: Complete

## Overview

이 문서는 Retrieve/Generation 탭 분리 기능 구현에 필요한 기술적 의사결정과 그 근거를 정리합니다. 각 결정은 기존 코드베이스 분석, 베스트 프랙티스 조사, 그리고 프로젝트 요구사항을 기반으로 합니다.

## 1. Chat Context Management

### Decision: In-Memory Session State (Frontend)

채팅 세션의 대화 맥락을 브라우저 메모리(React state)에서 관리합니다.

### Rationale

**장점**:
- 구현 단순성: 별도 세션 저장소 불필요
- 빠른 응답: 네트워크 왕복 없음
- 사용자 프라이버시: 서버에 대화 내용 저장 안 함
- 초기 구현 비용 최소화

**단점**:
- 새로고침 시 세션 손실
- 브라우저 간 세션 공유 불가
- 메모리 제한

**근거**:
1. 명세서의 Assumptions: "채팅 세션의 대화 맥락은 브라우저 세션 내에서만 유지되며, 새로고침 시 초기화됩니다"
2. Out of Scope: "채팅 세션의 영구 저장 및 히스토리 관리"
3. 연구 목적: 사용자는 RAG 파이프라인 테스트가 주 목적이므로 영구 저장 필요성 낮음

### Alternatives Considered

1. **Backend Session Storage (Redis/PostgreSQL)**
   - 장점: 영구 저장, 브라우저 간 공유
   - 단점: 복잡도 증가, 추가 인프라 필요
   - 거부 이유: 현재 범위에서 과도한 설계

2. **Local Storage**
   - 장점: 새로고침 후에도 유지
   - 단점: 보안 이슈 (API 키 저장), 용량 제한 (5-10MB)
   - 거부 이유: API 키 보안 위험, 명세서 가정과 불일치

### Implementation Details

```typescript
// Frontend State Structure
interface ChatSession {
  id: string;  // UUID v4
  pipelineId: number;
  modelConfig: ModelConfig;
  messages: Message[];
  createdAt: Date;
}

interface Message {
  id: string;  // UUID v4
  role: 'user' | 'assistant';
  content: string;
  sources?: RetrievedChunk[];
  timestamp: Date;
}
```

**Context Management Strategy**:
- 최대 메시지 수: 50개 (초과 시 자동 정리)
- 메모리 사용량 추정: ~1MB per session (텍스트 + 메타데이터)
- 10개 동시 세션 = ~10MB (성능 목표 충족)

---

## 2. Generation Model Abstraction

### Decision: Strategy Pattern with Abstract Base Class

Claude와 vLLM을 통합하기 위해 Abstract Generator 인터페이스를 정의합니다.

### Rationale

**패턴 선택 이유**:
- 확장성: 향후 OpenAI, Gemini 등 추가 모델 지원 용이
- 테스트 용이성: Mock Generator로 단위 테스트 가능
- 의존성 역전: Query Service가 구체적인 구현에 의존하지 않음

**근거**:
1. 명세서의 Out of Scope에 "OpenAI, Gemini 등 다른 생성 모델 제공자 지원"이 명시되어 있어 향후 확장 가능성 존재
2. Claude와 vLLM의 API 인터페이스가 다르므로 추상화 필요
3. 기존 코드베이스의 Embedder/Reranker 패턴과 일관성 유지

### Alternatives Considered

1. **Adapter Pattern**
   - 장점: 기존 인터페이스 재사용
   - 단점: Claude/vLLM이 표준 인터페이스가 없음
   - 거부 이유: 우리가 인터페이스를 정의해야 하므로 Strategy가 더 적합

2. **Direct Implementation (No Abstraction)**
   - 장점: 단순함
   - 단점: 코드 중복, 확장 어려움
   - 거부 이유: 이미 2개 모델이므로 추상화 정당화됨

### Implementation Details

```python
# backend/app/services/generation/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class GenerationConfig:
    """Configuration for text generation"""
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 0.9
    stop_sequences: List[str] = None

@dataclass
class GenerationResult:
    """Result of text generation"""
    answer: str
    tokens_used: int
    generation_time: float
    model_name: str

class AbstractGenerator(ABC):
    """Abstract base class for text generation models"""
    
    @abstractmethod
    def generate(
        self,
        query: str,
        context: str,
        config: GenerationConfig = None,
    ) -> GenerationResult:
        """
        Generate answer based on query and context.
        
        Args:
            query: User question
            context: Retrieved chunks formatted as context
            config: Generation parameters
            
        Returns:
            GenerationResult with answer and metadata
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the generator is available (API key valid, server reachable, etc.)"""
        pass
```

**Factory Pattern for Model Selection**:

```python
# backend/app/services/generation/factory.py
from app.services.generation.base import AbstractGenerator
from app.services.generation.claude import ClaudeGenerator
from app.services.generation.vllm_http import VLLMHttpGenerator

class GeneratorFactory:
    """Factory for creating generation models"""
    
    @staticmethod
    def create(model_type: str, **kwargs) -> AbstractGenerator:
        if model_type == "claude":
            return ClaudeGenerator(
                api_key=kwargs.get("api_key"),
                model_name=kwargs.get("model_name", "claude-3-sonnet-20240229")
            )
        elif model_type == "vllm":
            return VLLMHttpGenerator(
                endpoint=kwargs.get("endpoint"),
                model_name=kwargs.get("model_name")
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
```

---

## 3. Prompt Engineering

### Decision: System Prompt + User Prompt with Context Injection

RAG 컨텍스트를 포함한 구조화된 프롬프트 템플릿을 사용합니다.

### Rationale

**프롬프트 구조**:
- System Prompt: 역할 정의 및 지침
- Context: 검색된 문서들
- User Question: 실제 질문

**근거**:
1. Claude/vLLM 모두 System/User 역할 구분 지원
2. 명확한 컨텍스트 구분으로 hallucination 감소
3. 출처 명시 요구로 답변 검증 가능성 향상

### Implementation Details

```python
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided context.

Instructions:
- Answer the question using ONLY the information from the provided context
- If the context doesn't contain enough information to answer, say "I cannot find enough information in the provided documents to answer this question."
- Cite the source document numbers when you use information from them
- Be concise but complete in your answers
- Use Korean if the question is in Korean, English if in English
"""

def format_prompt(query: str, chunks: List[Dict[str, Any]]) -> str:
    """Format RAG prompt with context and query"""
    
    # Format context from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Document {i}]")
        context_parts.append(chunk["content"])
        context_parts.append("")  # blank line
    
    context = "\n".join(context_parts)
    
    # Build user prompt
    user_prompt = f"""Context:
{context}

Question: {query}

Answer:"""
    
    return user_prompt
```

**Context Length Management**:
- 최대 컨텍스트 토큰: 4000 tokens (Claude 100K 중 여유 있게)
- top_k 기본값: 5 (청크당 ~500 tokens 가정 → 총 2500 tokens + 여유)
- 토큰 초과 시: 청크 자르기 또는 개수 줄이기

### Alternatives Considered

1. **Few-Shot Prompting**
   - 장점: 더 나은 답변 품질
   - 단점: 컨텍스트 길이 증가
   - 거부 이유: 명세서에서 프롬프트 커스터마이징이 Out of Scope

2. **Chain-of-Thought Prompting**
   - 장점: 추론 과정 표시
   - 단점: 답변 길이 증가, 느린 응답
   - 거부 이유: 30초 성능 목표 충족 어려움

---

## 4. Error Handling Strategy

### Decision: Exponential Backoff with Circuit Breaker Pattern

API 호출 실패 시 재시도 로직과 연속 실패 시 서킷 브레이커를 적용합니다.

### Rationale

**전략 선택 이유**:
- Claude API rate limit: 429 에러 시 재시도 필요
- vLLM server down: 빠른 실패로 사용자 경험 개선
- 부분적 장애 대응: Circuit Breaker로 cascading failure 방지

**근거**:
1. 명세서 Edge Cases: "API 할당량 초과", "vLLM 서버 연결 실패"
2. Success Criteria: "5번의 연속적인 대화를 오류 없이 진행" → 높은 가용성 필요
3. 외부 의존성: Claude/vLLM 모두 네트워크 의존적

### Implementation Details

```python
# backend/app/services/generation/retry.py
import asyncio
from typing import Callable, TypeVar, Any
import structlog

logger = structlog.get_logger(__name__)
T = TypeVar('T')

class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 10.0  # seconds
    exponential_base: float = 2.0

async def retry_with_backoff(
    func: Callable[..., T],
    config: RetryConfig = None,
    retryable_errors: tuple = (TimeoutError, ConnectionError),
) -> T:
    """
    Retry function with exponential backoff.
    
    Args:
        func: Async function to retry
        config: Retry configuration
        retryable_errors: Tuple of exceptions to retry on
    
    Returns:
        Function result
        
    Raises:
        Last exception if all retries exhausted
    """
    config = config or RetryConfig()
    
    for attempt in range(config.max_attempts):
        try:
            return await func()
        except retryable_errors as e:
            if attempt == config.max_attempts - 1:
                logger.error("retry_exhausted", attempts=config.max_attempts, error=str(e))
                raise
            
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            logger.warning("retry_attempt", attempt=attempt+1, delay=delay, error=str(e))
            await asyncio.sleep(delay)

# Circuit Breaker (Simple Implementation)
class CircuitBreaker:
    """Simple circuit breaker for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
    
    def call_succeeded(self):
        """Record successful call"""
        self.failures = 0
        self.is_open = False
    
    def call_failed(self):
        """Record failed call"""
        self.failures += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        
        if self.failures >= self.failure_threshold:
            self.is_open = True
            logger.error("circuit_breaker_opened", failures=self.failures)
    
    def can_attempt(self) -> bool:
        """Check if call should be attempted"""
        if not self.is_open:
            return True
        
        # Check if timeout has passed
        if self.last_failure_time:
            elapsed = asyncio.get_event_loop().time() - self.last_failure_time
            if elapsed >= self.timeout:
                logger.info("circuit_breaker_half_open", elapsed=elapsed)
                self.is_open = False
                self.failures = 0
                return True
        
        return False
```

**Error Classification**:

| Error Type | Retry | User Message |
|------------|-------|--------------|
| Claude 429 (Rate Limit) | Yes (3x) | "API rate limit reached. Please wait a moment." |
| Claude 401 (Invalid Key) | No | "Invalid API key. Please check your settings." |
| vLLM Connection Error | Yes (2x) | "Cannot connect to model server. Please check the endpoint." |
| vLLM Timeout | Yes (2x) | "Model server is taking too long. Please try again." |
| Context Too Long | No | "Query context is too long. Please use fewer documents." |
| Unknown Error | No | "An unexpected error occurred. Please try again." |

### Alternatives Considered

1. **No Retry (Fail Fast)**
   - 장점: 단순함, 빠른 피드백
   - 단점: 일시적 오류에도 실패
   - 거부 이유: 네트워크 불안정성 대응 불가

2. **Infinite Retry**
   - 장점: 결국 성공
   - 단점: 사용자 대기 시간 증가
   - 거부 이유: 30초 성능 목표 위배

---

## 5. Dataset-Pipeline Relationship

### Decision: Existing Foreign Key Relationship

Pipeline 모델의 기존 `dataset_id` foreign key를 활용합니다.

### Rationale

**기존 데이터 모델**:
```python
# backend/app/models/pipeline.py
class Pipeline(Base):
    ...
    dataset_id = Column(Integer, ForeignKey("evaluation_datasets.id"), nullable=True)
    dataset = relationship("EvaluationDataset", backref="pipelines")
```

**근거**:
1. 이미 구현된 관계: Pipeline과 EvaluationDataset 간의 many-to-one 관계 존재
2. 단순한 쿼리: `db.query(Pipeline).filter(Pipeline.dataset_id == dataset_id)`
3. 일관성: 기존 아키텍처와 일치

### Implementation Details

```python
# backend/app/api/routes/pipelines.py
from fastapi import APIRouter, Query

@router.get("/", response_model=List[PipelineResponse])
def list_pipelines(
    dataset_id: Optional[int] = Query(None, description="Filter by evaluation dataset ID"),
    db: Session = Depends(get_db),
):
    """
    List all pipelines, optionally filtered by dataset.
    
    Query Parameters:
        dataset_id: If provided, only return pipelines using this dataset
    """
    query = db.query(Pipeline)
    
    if dataset_id is not None:
        query = query.filter(Pipeline.dataset_id == dataset_id)
    
    pipelines = query.order_by(Pipeline.created_at.desc()).all()
    
    return [
        PipelineResponse(
            id=p.id,
            name=p.name,
            pipeline_type=p.pipeline_type,
            dataset=DatasetSummary(**p.dataset.__dict__) if p.dataset else None,
            ...
        )
        for p in pipelines
    ]
```

**Frontend Implementation**:
```typescript
// frontend/src/routes/evaluate.tsx
const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null);
const [pipelines, setPipelines] = useState<Pipeline[]>([]);

useEffect(() => {
  loadPipelines(selectedDatasetId);
}, [selectedDatasetId]);

const loadPipelines = async (datasetId: number | null) => {
  const params = datasetId ? { dataset_id: datasetId } : {};
  const items = await api.listPipelines(params);
  setPipelines(items);
};
```

### Alternatives Considered

1. **Tags or Categories**
   - 장점: 더 유연한 분류
   - 단점: 기존 모델 변경 필요
   - 거부 이유: Dataset 관계로 충분, 불필요한 복잡도

2. **Join Table (Many-to-Many)**
   - 장점: 파이프라인이 여러 데이터셋 참조 가능
   - 단점: 현재 요구사항에 과도함
   - 거부 이유: 명세서에서 1:N 관계만 필요

---

## 6. Frontend Routing Strategy

### Decision: TanStack Router File-based Routing

기존 프로젝트의 TanStack Router 패턴을 유지합니다.

### Rationale

**기존 패턴**:
- `src/routes/query.tsx` → `/query` 경로
- File-based routing으로 경로와 파일이 1:1 매칭

**변경 사항**:
1. `query.tsx` → `retrieve.tsx` (파일 이름 변경)
2. `generation.tsx` 추가 (새 파일)

**근거**:
1. 일관성: 기존 프로젝트 구조 유지
2. 명시성: 파일 이름으로 경로 직관적 파악
3. TanStack Router 베스트 프랙티스

### Implementation Details

```typescript
// frontend/src/routes/retrieve.tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/retrieve')({
  component: RetrieveTab,
  validateSearch: (search: Record<string, unknown>) => ({
    pipelineId: search.pipelineId as number | undefined,
  }),
})

// frontend/src/routes/generation.tsx
export const Route = createFileRoute('/generation')({
  component: GenerationTab,
  validateSearch: (search: Record<string, unknown>) => ({
    pipelineId: search.pipelineId as number | undefined,
  }),
})
```

**Navigation Update**:
```typescript
// frontend/src/routes/__root.tsx
const navigation = [
  { name: 'Home', path: '/' },
  { name: 'Retrieve', path: '/retrieve' },  // Changed from 'Query'
  { name: 'Generation', path: '/generation' },  // New
  { name: 'Evaluate', path: '/evaluate' },
  ...
]
```

---

## 7. State Management for Chat UI

### Decision: Local Component State with Custom Hooks

React useState + useEffect로 채팅 상태를 관리하고, 재사용 가능한 커스텀 훅으로 추상화합니다.

### Rationale

**복잡도 평가**:
- 전역 상태 필요 없음: 채팅 세션은 Generation 탭 내부에서만 사용
- 컴포넌트 간 공유 없음: 단일 페이지 내 상태
- 서버 동기화 불필요: 세션이 서버에 저장되지 않음

**근거**:
1. YAGNI 원칙: Redux/Zustand 등 불필요
2. React 19 기본 기능으로 충분
3. 테스트 용이성: 커스텀 훅 단위 테스트 가능

### Implementation Details

```typescript
// frontend/src/hooks/useChatSession.ts
import { useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: RetrievedChunk[];
  timestamp: Date;
}

export interface ChatSession {
  id: string;
  pipelineId: number;
  modelConfig: ModelConfig;
  messages: Message[];
  createdAt: Date;
}

export function useChatSession(pipelineId: number, modelConfig: ModelConfig) {
  const [session, setSession] = useState<ChatSession>({
    id: uuidv4(),
    pipelineId,
    modelConfig,
    messages: [],
    createdAt: new Date(),
  });

  const addMessage = useCallback((message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: uuidv4(),
      timestamp: new Date(),
    };
    
    setSession(prev => ({
      ...prev,
      messages: [...prev.messages, newMessage],
    }));
  }, []);

  const clearSession = useCallback(() => {
    setSession({
      id: uuidv4(),
      pipelineId,
      modelConfig,
      messages: [],
      createdAt: new Date(),
    });
  }, [pipelineId, modelConfig]);

  return { session, addMessage, clearSession };
}
```

### Alternatives Considered

1. **Redux/Zustand (Global State)**
   - 장점: 컴포넌트 간 공유 용이
   - 단점: 보일러플레이트 증가, 현재 불필요
   - 거부 이유: Over-engineering

2. **Context API**
   - 장점: Props drilling 방지
   - 단점: 현재 컴포넌트 깊이가 얕음
   - 거부 이유: 복잡도 대비 이점 없음

---

## Summary Table

| Decision Area | Chosen Solution | Key Rationale |
|---------------|-----------------|---------------|
| Chat Context | In-Memory (Frontend State) | 명세서 가정, 단순성, 프라이버시 |
| Model Abstraction | Strategy Pattern | 확장성, 테스트 용이성, 일관성 |
| Prompt Template | System + Context + User | Hallucination 감소, 출처 명시 |
| Error Handling | Exponential Backoff + Circuit Breaker | 가용성, 사용자 경험 |
| Dataset Filtering | Existing FK Relationship | 이미 구현됨, 단순성 |
| Frontend Routing | TanStack File-based | 기존 패턴 유지, 일관성 |
| Chat State | Local State + Custom Hooks | YAGNI, 단순성, 테스트 용이성 |

## Next Steps

1. ✅ Research completed
2. 🔄 Create data-model.md with entity definitions
3. 🔄 Create API contracts (OpenAPI specs)
4. 🔄 Create quickstart.md for developers
5. ⏳ Begin Phase 2 implementation

