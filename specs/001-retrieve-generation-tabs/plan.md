# Implementation Plan: Retrieve & Generation Tabs Separation

**Branch**: `001-retrieve-generation-tabs` | **Date**: 2025-10-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-retrieve-generation-tabs/spec.md`

## Summary

이 기능은 기존 Query 탭을 검색 전용 Retrieve 탭으로 리네이밍하고, 새로운 Generation 탭을 추가하여 RAG 시스템의 검색과 생성 단계를 독립적으로 평가할 수 있도록 합니다. Generation 탭은 채팅 인터페이스를 제공하며 Claude API 또는 vLLM HTTP 엔드포인트를 통한 답변 생성을 지원합니다. 또한 Evaluation 탭에서 데이터셋 기반 파이프라인 필터링을 추가하여 동일 데이터셋을 사용하는 파이프라인 간의 비교 평가를 지원합니다.

**Technical Approach**: 
- Frontend: React 19 + TanStack Router로 라우트 리네이밍 및 새 라우트 추가
- Backend: 기존 `/api/query/answer` 엔드포인트 구현 완료 및 생성 모델 추상화
- Generation Models: Claude Anthropic SDK 및 vLLM HTTP 클라이언트 구현
- Evaluation: 파이프라인과 데이터셋 간의 관계를 활용한 필터링 로직 추가

## Technical Context

**Language/Version**: 
- Backend: Python 3.11
- Frontend: TypeScript 5.9, React 19

**Primary Dependencies**: 
- Backend: FastAPI 0.115, SQLAlchemy 2.0, Anthropic SDK 0.69, httpx 0.27
- Frontend: TanStack Router 1.133, Recharts 2.15

**Storage**: PostgreSQL (Pipeline/RAG metadata), Qdrant (Vector storage)

**Testing**: pytest (Backend), React Testing Library (Frontend)

**Target Platform**: Web Application (Docker containers)

**Project Type**: Web (Frontend + Backend)

**Performance Goals**: 
- Retrieve 검색: 3초 이내
- Generation 답변: 30초 이내
- 동시 채팅 세션: 10개

**Constraints**: 
- Claude API rate limits (사용자 토큰 기반)
- vLLM 서버 가용성 (외부 의존)
- 브라우저 세션 기반 채팅 컨텍스트 (영구 저장 없음)

**Scale/Scope**: 
- 중소규모 연구팀 (동시 사용자 10-20명)
- 파이프라인 수십~수백 개
- 데이터셋 수십 개

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Architecture Principles

✅ **Web Application Pattern**: Frontend/Backend 분리 아키텍처 준수
- Frontend: 사용자 인터페이스 및 상태 관리
- Backend: 비즈니스 로직 및 데이터 처리

✅ **API Contract Design**: RESTful API 패턴 사용
- `/api/query/search`: 검색 전용 (기존)
- `/api/query/answer`: 생성 포함 (구현 필요)
- `/api/pipelines`: 파이프라인 목록 및 필터링

✅ **Separation of Concerns**: 
- Query Service: 검색 로직
- Generation Service: 답변 생성 로직 (새로 추가)
- Pipeline Service: 파이프라인 관리 및 필터링

✅ **Error Handling**: 
- API 레벨: HTTP 상태 코드 및 명확한 에러 메시지
- Frontend: 사용자 친화적 에러 표시

### Testing Requirements

✅ **Unit Testing**: 
- Generation Service 단위 테스트
- Claude/vLLM 클라이언트 모킹

✅ **Integration Testing**: 
- Pipeline 필터링 로직 테스트
- End-to-end 검색 및 생성 플로우 테스트

✅ **User Acceptance Testing**: 
- 각 User Story별 Acceptance Scenario 테스트

**Constitution Check Status**: ✅ PASSED

## Project Structure

### Documentation (this feature)

```text
specs/001-retrieve-generation-tabs/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── query-api.yaml   # OpenAPI spec for query endpoints
│   └── pipeline-api.yaml # OpenAPI spec for pipeline filtering
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/routes/
│   │   ├── query.py              # [MODIFY] Implement answer endpoint
│   │   └── pipelines.py          # [MODIFY] Add dataset filtering
│   ├── models/
│   │   ├── pipeline.py           # [READ] Existing model
│   │   └── evaluation_dataset.py # [READ] Existing model
│   ├── schemas/
│   │   ├── query.py              # [MODIFY] Add generation schemas
│   │   └── pipeline.py           # [MODIFY] Add filter schemas
│   ├── services/
│   │   ├── query_service.py      # [MODIFY] Implement answer method
│   │   ├── generation/           # [NEW] Generation service package
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Abstract generator interface
│   │   │   ├── claude.py         # Claude implementation
│   │   │   └── vllm_http.py      # vLLM HTTP implementation
│   │   └── pipeline_service.py   # [MODIFY] Add filtering by dataset
│   └── core/
│       └── config.py             # [MODIFY] Add Claude/vLLM config
└── tests/
    ├── test_generation_service.py  # [NEW]
    ├── test_pipeline_filtering.py  # [NEW]
    └── test_query_api.py           # [MODIFY]

frontend/
├── src/
│   ├── routes/
│   │   ├── retrieve.tsx          # [NEW] Renamed from query.tsx
│   │   ├── generation.tsx        # [NEW] Chat interface
│   │   └── evaluate.tsx          # [MODIFY] Add dataset filtering
│   ├── components/
│   │   ├── ChatMessage.tsx       # [NEW] Chat message component
│   │   ├── ModelSelector.tsx     # [NEW] Model selection component
│   │   └── SourceViewer.tsx      # [NEW] Source document viewer
│   └── lib/
│       └── api.ts                # [MODIFY] Add generation API calls
└── tests/
    ├── routes/
    │   ├── retrieve.test.tsx     # [NEW]
    │   └── generation.test.tsx   # [NEW]
    └── components/
        └── ChatMessage.test.tsx  # [NEW]
```

**Structure Decision**: 
Web application 구조를 사용합니다. 기존 프로젝트가 frontend/backend로 분리되어 있으며, 이 패턴을 유지합니다. Generation 관련 로직은 `backend/app/services/generation/` 패키지로 분리하여 확장 가능한 구조를 만듭니다.

## Complexity Tracking

> Constitution Check에서 위반 사항이 없으므로 이 섹션은 비어있습니다.

## Phase 0: Research & Technical Decisions

### Research Questions

다음 research.md에서 다룰 주요 질문들:

1. **Chat Context Management**: 브라우저 세션에서 대화 맥락을 어떻게 관리할 것인가?
2. **Generation Model Abstraction**: Claude와 vLLM을 통합하기 위한 추상화 패턴은?
3. **Prompt Engineering**: RAG 컨텍스트를 포함한 기본 프롬프트 템플릿은?
4. **Error Handling Strategy**: API 호출 실패 시 재시도 및 폴백 전략은?
5. **Dataset-Pipeline Relationship**: 파이프라인 필터링을 위한 데이터 모델 활용 방법은?

### Known Technical Decisions

1. **Frontend Router**: TanStack Router 사용 (기존 프로젝트 일관성)
2. **HTTP Client**: httpx 사용 (기존 Backend 표준)
3. **Claude SDK**: Anthropic 공식 SDK (requirements.txt에 이미 포함)
4. **State Management**: React useState + useEffect (복잡도 낮음)

**Output**: [research.md](./research.md) - Phase 0 완료 후 생성

## Phase 1: Data Model & API Contracts

### Data Model Requirements

1. **ChatSession** (Frontend State):
   - id: string (UUID)
   - pipeline_id: number
   - model_config: ModelConfig
   - messages: Message[]
   - created_at: timestamp

2. **Message** (Frontend State):
   - id: string
   - role: 'user' | 'assistant'
   - content: string
   - sources?: RetrievedChunk[]
   - timestamp: timestamp

3. **ModelConfig** (Frontend/Backend):
   - type: 'claude' | 'vllm'
   - model_name: string
   - api_key?: string (Claude)
   - endpoint?: string (vLLM)
   - parameters?: GenerationParams

4. **GenerationParams**:
   - temperature: number (0-1)
   - max_tokens: number
   - top_p: number

5. **PipelineFilterRequest** (Backend):
   - dataset_id?: number
   - pipeline_type?: 'normal' | 'test'

### API Contract Requirements

1. **POST /api/query/answer**:
   - Request: AnswerRequest (pipeline_id, query, top_k, model_config)
   - Response: AnswerResponse (answer, sources, tokens_used, timings)

2. **GET /api/pipelines**:
   - Query params: dataset_id (optional)
   - Response: Pipeline[] (filtered by dataset)

3. **POST /api/query/chat** (Optional for future):
   - Request: ChatRequest (pipeline_id, messages, model_config)
   - Response: ChatResponse (streaming or complete)

**Output**: 
- [data-model.md](./data-model.md) - Entity definitions
- [contracts/query-api.yaml](./contracts/query-api.yaml) - OpenAPI spec
- [contracts/pipeline-api.yaml](./contracts/pipeline-api.yaml) - OpenAPI spec

### Implementation Sequence

#### P1: Core Retrieve Tab (Lowest Risk)
1. Rename `query.tsx` → `retrieve.tsx`
2. Update route registration
3. Update navigation links
4. Test existing functionality

#### P1: Core Generation Backend (Foundation)
1. Implement `generation/base.py` (Abstract Generator)
2. Implement `generation/claude.py` (Claude client)
3. Implement `query_service.answer()` method
4. Unit tests for generation service

#### P1: Core Generation Frontend (User-Facing)
1. Create `generation.tsx` with chat UI
2. Implement model selector component
3. Implement chat message rendering
4. Connect to `/api/query/answer` endpoint

#### P2: Claude Integration (Quick Win)
1. Add Claude API configuration
2. Implement error handling
3. Add API key validation
4. User documentation

#### P2: vLLM Integration (Parallel to Claude)
1. Implement `generation/vllm_http.py`
2. Add endpoint configuration
3. Connection testing feature
4. Error handling

#### P3: Evaluation Filtering (Enhancement)
1. Add dataset filter to `/api/pipelines`
2. Update `evaluate.tsx` with dataset selector
3. Filter pipeline list by dataset
4. Display comparison UI

**Output**: [quickstart.md](./quickstart.md) - Developer setup guide

## Phase 2: Task Breakdown

Phase 2는 `/speckit.tasks` 명령어로 별도로 생성됩니다.

각 구현 단계는 다음과 같이 태스크로 분해됩니다:
- 기능별 독립 실행 가능한 작은 단위
- 명확한 입력/출력 정의
- 테스트 가능한 단위

## Dependencies & Integration Points

### External Dependencies
- Claude Anthropic API (사용자 제공 API 키)
- vLLM Server (사용자 호스팅)
- Qdrant Vector DB (기존 인프라)

### Internal Dependencies
- Pipeline Model (기존)
- RAG Configuration (기존)
- Query Service (수정 필요)
- Qdrant Service (기존)

### Integration Risks
1. **Claude API Rate Limits**: 사용자별 토큰 관리 필요
2. **vLLM Server Availability**: 연결 실패 시 적절한 에러 처리
3. **Browser Session Limits**: 메모리 사용량 모니터링
4. **Concurrent Requests**: Backend 동시 요청 처리 능력

## Validation & Acceptance

각 User Story의 Acceptance Scenario를 기반으로 다음을 검증합니다:

### P1 Validation (Retrieve Tab)
- [ ] 기존 Query 탭 기능이 Retrieve 탭에서 동일하게 작동
- [ ] 검색 결과 및 성능 메트릭 표시
- [ ] 네비게이션 링크 업데이트

### P1 Validation (Generation Tab)
- [ ] 파이프라인 및 모델 선택 UI
- [ ] 채팅 메시지 전송 및 답변 수신
- [ ] 참조 문서 표시
- [ ] 대화 맥락 유지 (5번 연속 대화)

### P2 Validation (Claude Integration)
- [ ] API 토큰 설정 UI
- [ ] Claude 모델 선택
- [ ] 답변 생성 성공
- [ ] 에러 처리 (잘못된 토큰, rate limit)

### P2 Validation (vLLM Integration)
- [ ] 엔드포인트 설정 UI
- [ ] 연결 테스트 기능
- [ ] 답변 생성 성공
- [ ] 에러 처리 (연결 실패)

### P3 Validation (Evaluation Filtering)
- [ ] 데이터셋 선택 드롭다운
- [ ] 파이프라인 필터링 작동
- [ ] 1개 이상 파이프라인 선택 및 평가
- [ ] 비교 결과 시각화

## Next Steps

1. ✅ Complete this plan.md
2. 🔄 Create research.md (Phase 0)
3. 🔄 Create data-model.md (Phase 1)
4. 🔄 Create API contracts (Phase 1)
5. 🔄 Create quickstart.md (Phase 1)
6. 🔄 Update agent context
7. ⏳ Run `/speckit.tasks` for Phase 2 breakdown
