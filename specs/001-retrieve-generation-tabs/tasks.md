# Tasks: Retrieve & Generation Tabs Separation

**Input**: Design documents from `/specs/001-retrieve-generation-tabs/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are NOT explicitly requested in the specification. Test tasks are excluded from this plan per the specification's scope.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app structure**: `backend/app/`, `frontend/src/`
- Backend API routes: `backend/app/api/routes/`
- Backend services: `backend/app/services/`
- Backend schemas: `backend/app/schemas/`
- Frontend routes: `frontend/src/routes/`
- Frontend components: `frontend/src/components/`
- Frontend hooks: `frontend/src/hooks/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Verify development environment (Python 3.11+, Node.js 18+, Docker)
- [ ] T002 Ensure backend dependencies include anthropic==0.69.0 and httpx==0.27.2 in requirements.txt
- [ ] T003 [P] Verify frontend has required dependencies (@tanstack/react-router, react 19)
- [ ] T004 [P] Start Docker services (Qdrant on 6333, PostgreSQL on 5432)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core generation infrastructure that MUST be complete before Generation tab implementation

**⚠️ CRITICAL**: Generation tab (US2) cannot begin until this phase is complete. Retrieve tab (US1) can proceed independently.

- [ ] T005 [P] Create generation service package structure at backend/app/services/generation/
- [ ] T006 [P] Implement AbstractGenerator base class in backend/app/services/generation/base.py
- [ ] T007 [P] Create GenerationConfig and GenerationResult dataclasses in backend/app/services/generation/base.py
- [ ] T008 [P] Add generation-related schemas (ModelConfigRequest, GenerationParamsRequest, AnswerRequest, AnswerResponse) to backend/app/schemas/query.py
- [ ] T009 Create prompt formatting utilities in backend/app/services/generation/base.py

**Checkpoint**: Foundation ready - US1 can proceed immediately, US2-US4 can begin after this phase

---

## Phase 3: User Story 1 - Retrieve Tab for Search Performance Testing (Priority: P1) 🎯 MVP

**Goal**: Rename Query tab to Retrieve without breaking existing search functionality

**Independent Test**: 
- Navigate to `/retrieve` route
- Select a pipeline and enter a query
- Verify search results and performance metrics display correctly
- All existing Query tab functionality works identically

**Acceptance Criteria**:
- ✅ Retrieve tab shows same functionality as old Query tab
- ✅ Search results display with performance metrics (time, count, scores)
- ✅ Navigation links updated throughout the application

### Implementation for User Story 1

- [ ] T010 [P] [US1] Rename frontend/src/routes/query.tsx to frontend/src/routes/retrieve.tsx
- [ ] T011 [US1] Update route definition in frontend/src/routes/retrieve.tsx (change createFileRoute from '/query' to '/retrieve')
- [ ] T012 [US1] Rename component function from QueryTest to RetrieveTab in frontend/src/routes/retrieve.tsx
- [ ] T013 [US1] Update page title from "Query Test" to "Retrieve" in frontend/src/routes/retrieve.tsx
- [ ] T014 [US1] Update navigation links in frontend/src/routes/__root.tsx (change Query to Retrieve, /query to /retrieve)
- [ ] T015 [P] [US1] Regenerate route tree by running npm run dev in frontend directory
- [ ] T016 [US1] Manual test: Navigate to /retrieve, perform search, verify all functionality works

**Checkpoint**: Retrieve tab fully functional. Users can test search performance independently.

---

## Phase 4: User Story 2 - Generation Tab for Chat-based RAG Testing (Priority: P1)

**Goal**: Create Generation tab with chat interface for answer generation using LLM

**Independent Test**:
- Navigate to `/generation` route
- Select a pipeline and configure a generation model (placeholder config)
- Enter a question and receive a generated answer
- Verify answer displays with source documents
- Send multiple messages to test conversation context

**Acceptance Criteria**:
- ✅ Generation tab accessible with chat UI
- ✅ Pipeline selection interface works
- ✅ Model configuration UI (Claude/vLLM selection)
- ✅ Chat messages render (user questions + assistant answers)
- ✅ Source documents display with answers
- ✅ Conversation context maintained across messages

**Dependencies**: Requires Phase 2 (Foundational) completion

### Backend Implementation for User Story 2

- [ ] T017 [US2] Implement answer() method in backend/app/services/query_service.py (search + context formatting + generation call)
- [ ] T018 [US2] Add _format_context() helper method in backend/app/services/query_service.py
- [ ] T019 [US2] Create GeneratorFactory class in backend/app/services/generation/factory.py
- [ ] T020 [US2] Implement POST /api/query/answer endpoint in backend/app/api/routes/query.py (handle AnswerRequest, call query_service.answer())
- [ ] T021 [US2] Add error handling for generation failures in backend/app/api/routes/query.py

### Frontend Implementation for User Story 2

- [ ] T022 [P] [US2] Create useChatSession custom hook in frontend/src/hooks/useChatSession.ts (ChatSession, Message interfaces, state management)
- [ ] T023 [P] [US2] Create ChatMessage component in frontend/src/components/ChatMessage.tsx (render user/assistant messages)
- [ ] T024 [P] [US2] Create ModelSelector component in frontend/src/components/ModelSelector.tsx (select Claude/vLLM, configure parameters)
- [ ] T025 [P] [US2] Create SourceViewer component in frontend/src/components/SourceViewer.tsx (display retrieved chunks)
- [ ] T026 [US2] Create generation.tsx route in frontend/src/routes/generation.tsx (chat UI, pipeline selector, model selector, message list, input box)
- [ ] T027 [US2] Add generateAnswer() API function to frontend/src/lib/api.ts (call POST /api/query/answer)
- [ ] T028 [US2] Implement message sending in frontend/src/routes/generation.tsx (add user message, call API, add assistant message)
- [ ] T029 [US2] Add loading state and error handling in frontend/src/routes/generation.tsx
- [ ] T030 [US2] Update navigation to include Generation tab in frontend/src/routes/__root.tsx
- [ ] T031 [US2] Manual test: Send question, verify answer generated, check sources displayed, test multiple messages

**Checkpoint**: Generation tab functional with chat interface. Answer generation works (will need actual model in US3/US4).

---

## Phase 5: User Story 3 - Claude Model Integration for Answer Generation (Priority: P2)

**Goal**: Integrate Claude API to enable answer generation with Claude models

**Independent Test**:
- In Generation tab, select Claude as model type
- Enter valid Claude API key (starts with sk-ant-)
- Select a Claude model (e.g., claude-3-sonnet-20240229)
- Send a question and verify answer is generated via Claude API
- Test error handling with invalid API key
- Test multiple consecutive messages (5+) to verify stable operation

**Acceptance Criteria**:
- ✅ Claude models available in model selector dropdown
- ✅ API key input interface with validation
- ✅ Answer generation via Claude API works
- ✅ Error messages for invalid key/rate limits
- ✅ 5 consecutive messages work without errors

**Dependencies**: Requires Phase 2 (Foundational) and US2 backend implementation

### Implementation for User Story 3

- [ ] T032 [P] [US3] Implement ClaudeGenerator class in backend/app/services/generation/claude.py (inherit AbstractGenerator)
- [ ] T033 [US3] Add generate() method to ClaudeGenerator (format prompt, call Claude API, return GenerationResult)
- [ ] T034 [US3] Add is_available() method to ClaudeGenerator (test API key validity)
- [ ] T035 [US3] Implement retry logic with exponential backoff in backend/app/services/generation/claude.py
- [ ] T036 [US3] Add Claude model creation to GeneratorFactory in backend/app/services/generation/factory.py
- [ ] T037 [US3] Add Claude model options to ModelSelector component in frontend/src/components/ModelSelector.tsx
- [ ] T038 [US3] Add API key input field for Claude in frontend/src/components/ModelSelector.tsx
- [ ] T039 [US3] Add API key validation (format check: sk-ant-*) in frontend/src/components/ModelSelector.tsx
- [ ] T040 [US3] Add error handling for Claude API errors in backend/app/api/routes/query.py (401, 429, 500)
- [ ] T041 [US3] Manual test: Use Claude with valid key, generate 5 consecutive answers, test invalid key error

**Checkpoint**: Claude integration complete. Users can generate answers using Claude models.

---

## Phase 6: User Story 4 - vLLM HTTP Integration for Custom Model Support (Priority: P2)

**Goal**: Integrate vLLM HTTP server to enable answer generation with custom models

**Independent Test**:
- In Generation tab, select vLLM as model type
- Enter vLLM server endpoint URL (e.g., http://localhost:8001/v1/completions)
- Enter model name
- Click connection test button and verify server is reachable
- Send a question and verify answer is generated via vLLM
- Test error handling with invalid endpoint

**Acceptance Criteria**:
- ✅ vLLM option available in model selector
- ✅ Endpoint URL and model name input fields
- ✅ Connection test functionality
- ✅ Answer generation via vLLM HTTP works
- ✅ Error messages for connection failures

**Dependencies**: Requires Phase 2 (Foundational) and US2 backend implementation. Can be developed in parallel with US3.

### Implementation for User Story 4

- [ ] T042 [P] [US4] Implement VLLMHttpGenerator class in backend/app/services/generation/vllm_http.py (inherit AbstractGenerator)
- [ ] T043 [US4] Add generate() method to VLLMHttpGenerator (format request, HTTP call with httpx, parse response)
- [ ] T044 [US4] Add is_available() method to VLLMHttpGenerator (test server connection)
- [ ] T045 [US4] Implement retry logic and timeout handling in backend/app/services/generation/vllm_http.py
- [ ] T046 [US4] Add vLLM model creation to GeneratorFactory in backend/app/services/generation/factory.py
- [ ] T047 [US4] Add vLLM option to ModelSelector component in frontend/src/components/ModelSelector.tsx
- [ ] T048 [US4] Add endpoint URL and model name inputs for vLLM in frontend/src/components/ModelSelector.tsx
- [ ] T049 [US4] Add connection test button and handler in frontend/src/components/ModelSelector.tsx
- [ ] T050 [US4] Add vLLM error handling in backend/app/api/routes/query.py (connection errors, timeouts)
- [ ] T051 [US4] Manual test: Configure vLLM endpoint, test connection, generate answer, test connection error

**Checkpoint**: vLLM integration complete. Users can use custom models via vLLM HTTP server.

---

## Phase 7: User Story 5 - Dataset-filtered Pipeline Selection in Evaluation (Priority: P3)

**Goal**: Filter pipelines by evaluation dataset in Evaluation tab for fair comparison

**Independent Test**:
- Navigate to Evaluation tab
- Select a dataset from dropdown
- Verify only pipelines using that dataset are displayed
- Select multiple filtered pipelines and run evaluation
- Verify comparison results display correctly
- Test with dataset that has no pipelines (empty result)

**Acceptance Criteria**:
- ✅ Dataset selector dropdown in Evaluation tab
- ✅ Pipeline list filters by selected dataset
- ✅ Multiple pipelines can be selected from filtered list
- ✅ Evaluation runs on selected pipelines
- ✅ Empty state message when no pipelines match dataset

**Dependencies**: None (can run independently after Phase 1)

### Backend Implementation for User Story 5

- [ ] T052 [US5] Add dataset_id query parameter to GET /api/pipelines endpoint in backend/app/api/routes/pipelines.py
- [ ] T053 [US5] Implement filtering logic by dataset_id in backend/app/api/routes/pipelines.py
- [ ] T054 [US5] Add parameter validation for dataset_id in backend/app/api/routes/pipelines.py

### Frontend Implementation for User Story 5

- [ ] T055 [P] [US5] Add dataset selector dropdown to frontend/src/routes/evaluate.tsx (fetch available datasets)
- [ ] T056 [US5] Add state management for selected dataset ID in frontend/src/routes/evaluate.tsx
- [ ] T057 [US5] Update loadPipelines() to include dataset_id parameter in frontend/src/routes/evaluate.tsx
- [ ] T058 [US5] Add useEffect to reload pipelines when dataset selection changes in frontend/src/routes/evaluate.tsx
- [ ] T059 [US5] Add empty state UI when no pipelines match selected dataset in frontend/src/routes/evaluate.tsx
- [ ] T060 [US5] Update api.listPipelines() to support dataset_id query parameter in frontend/src/lib/api.ts
- [ ] T061 [US5] Manual test: Select dataset, verify filtering, test empty dataset, run evaluation on filtered pipelines

**Checkpoint**: Evaluation filtering complete. Users can compare pipelines using the same dataset.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T062 [P] Add comprehensive logging for all generation operations in backend/app/services/generation/
- [ ] T063 [P] Add performance tracking (retrieval_time, llm_time) to all answer endpoints
- [ ] T064 [P] Improve error messages across all API endpoints for better user experience
- [ ] T065 [P] Add input validation and sanitization for all user inputs
- [ ] T066 [P] Update UI styling for consistent look across Retrieve and Generation tabs
- [ ] T067 [P] Add loading indicators and progress feedback for long operations
- [ ] T068 [P] Add tooltips and help text for model configuration options
- [ ] T069 Code review and refactoring for consistency
- [ ] T070 Run through quickstart.md validation scenarios
- [ ] T071 Update README.md with new features (Retrieve/Generation tabs)
- [ ] T072 [P] Add security headers and CORS configuration review
- [ ] T073 Performance testing: Verify 10 concurrent chat sessions work smoothly
- [ ] T074 Manual end-to-end test: Complete user journey for all 5 user stories

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS US2, US3, US4 (does NOT block US1)
- **User Story 1 (Phase 3)**: Can start after Setup (Phase 1) - No dependencies on other stories
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) - Foundation for US3, US4
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) and US2 backend - Can run parallel with US4
- **User Story 4 (Phase 6)**: Depends on Foundational (Phase 2) and US2 backend - Can run parallel with US3
- **User Story 5 (Phase 7)**: Depends only on Setup (Phase 1) - Completely independent
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Setup (Phase 1)
    ├─→ US1 (Phase 3) ─────────────────────────┐
    ├─→ Foundational (Phase 2)                  │
    │       ├─→ US2 (Phase 4)                   │
    │       │       ├─→ US3 (Phase 5) ─────────→ Polish (Phase 8)
    │       │       └─→ US4 (Phase 6) ─────────→ Polish (Phase 8)
    │       └─────────────────────────────────→ Polish (Phase 8)
    └─→ US5 (Phase 7) ─────────────────────────┘
```

**Key Insights**:
- **US1** (Retrieve Tab) is completely independent - can be first MVP
- **US5** (Evaluation Filtering) is independent - can be done anytime after Setup
- **US3** and **US4** (Claude/vLLM) can run in parallel after US2 backend is ready
- **US2** (Generation Tab) is the foundation for US3 and US4

### Within Each User Story

- Backend implementation before frontend integration
- Core services before API endpoints
- Components before route assembly
- Story complete and tested before moving to next priority

### Parallel Opportunities

**Within Phases**:
- Setup: T002, T003, T004 can run in parallel
- Foundational: T005, T006, T007, T008 can run in parallel
- US1: T010, T015 can overlap with T011-T014
- US2 Backend: None (sequential dependencies)
- US2 Frontend: T022, T023, T024, T025 can run in parallel
- US3: T032, T037-T039 can run in parallel (backend vs frontend)
- US4: T042-T045, T047-T049 can run in parallel (backend vs frontend)
- US5 Backend: T052, T053, T054 are sequential
- US5 Frontend: T055, T060 can start while backend is in progress
- Polish: Most tasks (T062-T068, T071, T072) can run in parallel

**Across Phases** (if team capacity allows):
- US1 and Foundational can run in parallel (different systems)
- US3 and US4 can run in parallel (different generators)
- US5 can run in parallel with US2-US4 (different feature area)

---

## Parallel Example: User Story 2 Frontend

```bash
# Launch all frontend components for User Story 2 together:
Task T022: "Create useChatSession custom hook in frontend/src/hooks/useChatSession.ts"
Task T023: "Create ChatMessage component in frontend/src/components/ChatMessage.tsx"
Task T024: "Create ModelSelector component in frontend/src/components/ModelSelector.tsx"
Task T025: "Create SourceViewer component in frontend/src/components/SourceViewer.tsx"

# These can be developed simultaneously by different developers or in parallel sessions
```

---

## Parallel Example: Claude (US3) + vLLM (US4)

```bash
# Once US2 backend is complete, both generators can be built in parallel:

# Developer/Session A: Claude Integration
Task T032: "Implement ClaudeGenerator in backend/app/services/generation/claude.py"
Task T037: "Add Claude options to ModelSelector"

# Developer/Session B: vLLM Integration  
Task T042: "Implement VLLMHttpGenerator in backend/app/services/generation/vllm_http.py"
Task T047: "Add vLLM option to ModelSelector"

# These are completely independent and can run simultaneously
```

---

## Implementation Strategy

### Strategy 1: MVP First (Recommended)

**Goal**: Get working Retrieve tab as fast as possible for user feedback

1. Complete Phase 1: Setup (10 min)
2. Complete Phase 3: User Story 1 - Retrieve Tab (30 min)
3. **STOP and VALIDATE**: Test Retrieve tab independently
4. Demo to users, gather feedback
5. **Total MVP Time**: ~40 minutes 🎯

**Why this works**: US1 is a simple rename with no new functionality. Lowest risk, fastest feedback.

### Strategy 2: Full Feature Set (P1 Stories)

**Goal**: Deliver both Retrieve and Generation tabs with Claude support

1. Complete Phase 1: Setup (10 min)
2. Complete Phase 3: User Story 1 - Retrieve Tab (30 min)
3. Complete Phase 2: Foundational (45 min)
4. Complete Phase 4: User Story 2 - Generation Tab (2 hours)
5. Complete Phase 5: User Story 3 - Claude Integration (1 hour)
6. **STOP and VALIDATE**: Test end-to-end
7. Demo complete RAG evaluation system
8. **Total Time**: ~4.5 hours

### Strategy 3: Parallel Team Strategy

**Goal**: Maximize throughput with multiple developers

1. **All Together**: Setup (Phase 1) - 10 min
2. **Team Split**:
   - Developer A: US1 (Retrieve) - 30 min
   - Developer B: Foundational (Phase 2) - 45 min
   - Developer C: US5 (Evaluation Filtering) - 45 min
3. **After Foundational**:
   - Developer A: US2 (Generation Tab) - 2 hours
4. **After US2 Backend**:
   - Developer B: US3 (Claude) - 1 hour
   - Developer C: US4 (vLLM) - 1 hour
5. **All Together**: Polish (Phase 8) - 30 min
6. **Total Wall-Clock Time**: ~4.5 hours (vs 7+ hours sequential)

### Incremental Delivery Milestones

| Milestone | Includes | User Value | Time |
|-----------|----------|------------|------|
| **M1: MVP** | US1 | Search performance testing with renamed tab | 40 min |
| **M2: Basic Generation** | US1 + US2 | Chat interface (placeholder models) | 3 hours |
| **M3: Claude Support** | US1 + US2 + US3 | Full RAG with Claude models | 4.5 hours |
| **M4: vLLM Support** | US1 + US2 + US3 + US4 | Custom model support | 5.5 hours |
| **M5: Complete** | All | Dataset filtering + polished UX | 7 hours |

---

## Success Criteria Validation

Map each Success Criterion from spec.md to validation tasks:

- **SC-001** (Retrieve < 3s): Validate in T016 (US1 manual test)
- **SC-002** (Generation < 30s): Validate in T031, T041, T051 (US2, US3, US4 manual tests)
- **SC-003** (5 consecutive messages): Validate in T041 (US3 manual test)
- **SC-004** (Dataset filter < 1s): Validate in T061 (US5 manual test)
- **SC-005** (Multi-pipeline evaluation): Validate in T061 (US5 manual test)
- **SC-006** (10 concurrent sessions): Validate in T073 (Polish phase)
- **SC-007** (Source verification): Validate in T031 (US2 manual test)

---

## Task Summary

**Total Tasks**: 74

**Task Breakdown by Phase**:
- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 5 tasks
- Phase 3 (US1 - Retrieve): 7 tasks
- Phase 4 (US2 - Generation): 15 tasks
- Phase 5 (US3 - Claude): 10 tasks
- Phase 6 (US4 - vLLM): 10 tasks
- Phase 7 (US5 - Evaluation): 10 tasks
- Phase 8 (Polish): 13 tasks

**Parallel Opportunities**: 26 tasks marked [P] can run in parallel within their phase

**Independent User Stories**: 
- US1 can be deployed alone (MVP)
- US5 can be deployed alone
- US3 and US4 are independent of each other

**Suggested MVP Scope**: Phase 1 + Phase 3 (US1 only) = 11 tasks, ~40 minutes

---

## Format Validation

✅ All tasks follow checklist format: `- [ ] [TaskID] [P?] [Story?] Description`
✅ All task IDs sequential (T001-T074)
✅ All user story tasks labeled ([US1], [US2], [US3], [US4], [US5])
✅ All parallelizable tasks marked [P]
✅ All tasks include file paths or clear scope
✅ Independent test criteria defined for each user story
✅ Dependency graph shows user story completion order

**Ready for implementation!** 🚀

