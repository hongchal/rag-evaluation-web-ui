# Feature Specification: Retrieve & Generation Tabs Separation

**Feature Branch**: `001-retrieve-generation-tabs`  
**Created**: 2025-10-28  
**Status**: Draft  
**Input**: User description: "기존 Query탭의 이름을 Retrieve으로 바꿔서 검색 성능을 측정하는 탭으로 바꾸고, 새롭게 Generation이라는 탭을 만들어서 생성 모듈까지 붙여서 채팅 형태로 사용할 수 있도록 함. 생성 모듈은 기존 파이프라인의 청킹들을 이용하여 Claude 또는 vLLM HTTP 모델로 답변 생성. Evaluation은 같은 데이터셋을 선택한 파이프라인끼리 노출하고 1개 이상 선택하여 평가 가능"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retrieve Tab for Search Performance Testing (Priority: P1)

연구자가 RAG 시스템의 검색 성능을 평가하기 위해 파이프라인을 선택하고 쿼리를 입력하여 검색된 문서와 관련 메트릭을 확인합니다.

**Why this priority**: 기존 Query 탭의 핵심 기능을 유지하면서 명확한 목적(검색 성능 측정)을 가진 탭으로 리네이밍하는 것은 사용자 경험의 기초가 되며, 다른 기능들의 전제 조건입니다.

**Independent Test**: 사용자가 Retrieve 탭에서 파이프라인을 선택하고 쿼리를 입력하면 검색 결과와 성능 지표가 표시되는지 확인할 수 있습니다.

**Acceptance Scenarios**:

1. **Given** 사용자가 Retrieve 탭을 열었을 때, **When** 파이프라인 목록이 표시되고, **Then** 기존 Query 탭과 동일한 기능을 사용할 수 있다
2. **Given** 사용자가 파이프라인을 선택하고 쿼리를 입력했을 때, **When** 검색을 실행하면, **Then** 검색된 문서 목록과 관련도 점수가 표시된다
3. **Given** 검색 결과가 표시되었을 때, **When** 사용자가 결과를 확인하면, **Then** 검색 시간, 문서 개수 등 성능 메트릭이 함께 표시된다

---

### User Story 2 - Generation Tab for Chat-based RAG Testing (Priority: P1)

연구자가 Generation 탭에서 파이프라인과 생성 모델을 선택하여 실제 답변 생성 품질을 채팅 형태로 테스트합니다.

**Why this priority**: 검색과 생성을 분리하여 각각의 성능을 독립적으로 평가할 수 있는 것은 RAG 평가 시스템의 핵심 가치입니다. 이는 Retrieve 탭과 동등한 중요도를 가집니다.

**Independent Test**: 사용자가 Generation 탭에서 파이프라인과 모델을 선택하고 질문을 입력하면 검색된 컨텍스트를 기반으로 생성된 답변이 채팅 형태로 표시되는지 확인할 수 있습니다.

**Acceptance Scenarios**:

1. **Given** 사용자가 Generation 탭을 열었을 때, **When** 파이프라인과 생성 모델을 선택할 수 있는 UI가 표시되고, **Then** 선택 후 채팅 인터페이스가 활성화된다
2. **Given** 사용자가 파이프라인과 모델을 선택하고 질문을 입력했을 때, **When** 전송 버튼을 클릭하면, **Then** 시스템이 파이프라인으로 문서를 검색하고 선택한 모델로 답변을 생성하여 채팅 형태로 표시한다
3. **Given** 답변이 생성되었을 때, **When** 사용자가 답변을 확인하면, **Then** 답변과 함께 참조된 문서 정보가 표시된다
4. **Given** 채팅 세션이 진행 중일 때, **When** 사용자가 추가 질문을 입력하면, **Then** 이전 대화 맥락이 유지되면서 새로운 답변이 생성된다

---

### User Story 3 - Claude Model Integration for Answer Generation (Priority: P2)

연구자가 Generation 탭에서 Claude API를 사용하여 답변을 생성합니다.

**Why this priority**: 생성 모델의 첫 번째 구현으로, 검증된 상용 API를 사용하여 빠르게 기능을 구현하고 사용자 피드백을 받을 수 있습니다.

**Independent Test**: 사용자가 Claude API 토큰을 설정하고 Claude 모델을 선택하여 답변을 생성할 수 있는지 확인할 수 있습니다.

**Acceptance Scenarios**:

1. **Given** 사용자가 Generation 탭에서 모델 선택 드롭다운을 열었을 때, **When** Claude 모델 옵션들이 표시되고, **Then** 사용 가능한 Claude 모델 목록(예: claude-3-opus, claude-3-sonnet)을 선택할 수 있다
2. **Given** 사용자가 Claude API 토큰을 설정하지 않았을 때, **When** Claude 모델을 선택하면, **Then** API 토큰 입력을 요청하는 메시지가 표시된다
3. **Given** 유효한 Claude API 토큰이 설정되었을 때, **When** 질문을 입력하고 전송하면, **Then** Claude API를 통해 답변이 생성되어 표시된다
4. **Given** API 호출 중 오류가 발생했을 때, **When** 시스템이 오류를 감지하면, **Then** 사용자에게 명확한 오류 메시지와 해결 방법이 표시된다

---

### User Story 4 - vLLM HTTP Integration for Custom Model Support (Priority: P2)

연구자가 자체 호스팅한 vLLM 서버를 통해 커스텀 모델로 답변을 생성합니다.

**Why this priority**: Claude와 함께 vLLM 지원을 추가하여 사용자가 자체 모델을 사용할 수 있는 유연성을 제공합니다. Claude 구현 이후 독립적으로 추가 가능합니다.

**Independent Test**: 사용자가 vLLM 서버 엔드포인트를 설정하고 커스텀 모델로 답변을 생성할 수 있는지 확인할 수 있습니다.

**Acceptance Scenarios**:

1. **Given** 사용자가 Generation 탭에서 모델 선택 드롭다운을 열었을 때, **When** vLLM HTTP 옵션을 선택하고, **Then** vLLM 서버 엔드포인트와 모델 이름을 입력할 수 있는 설정 화면이 표시된다
2. **Given** vLLM 서버 정보가 입력되었을 때, **When** 연결 테스트 버튼을 클릭하면, **Then** 서버 연결 상태와 사용 가능한 모델 목록이 확인된다
3. **Given** vLLM 서버가 정상적으로 연결되었을 때, **When** 질문을 입력하고 전송하면, **Then** vLLM 서버를 통해 답변이 생성되어 표시된다
4. **Given** vLLM 서버 연결이 실패했을 때, **When** 시스템이 오류를 감지하면, **Then** 연결 설정을 확인하라는 메시지가 표시된다

---

### User Story 5 - Dataset-filtered Pipeline Selection in Evaluation (Priority: P3)

연구자가 Evaluation 탭에서 특정 데이터셋을 선택하면 해당 데이터셋을 사용하는 파이프라인만 표시되어 비교 평가를 수행합니다.

**Why this priority**: 평가 기능의 개선으로, 기본적인 Retrieve와 Generation 기능이 구현된 후에 추가하는 것이 자연스러운 흐름입니다.

**Independent Test**: 사용자가 Evaluation 탭에서 데이터셋을 선택하면 해당 데이터셋을 사용하는 파이프라인만 필터링되어 표시되는지 확인할 수 있습니다.

**Acceptance Scenarios**:

1. **Given** 사용자가 Evaluation 탭을 열었을 때, **When** 데이터셋 선택 드롭다운을 열면, **Then** 사용 가능한 평가 데이터셋 목록이 표시된다
2. **Given** 사용자가 특정 데이터셋을 선택했을 때, **When** 파이프라인 목록이 업데이트되면, **Then** 해당 데이터셋을 사용하는 파이프라인만 표시된다
3. **Given** 필터링된 파이프라인 목록이 표시되었을 때, **When** 사용자가 1개 이상의 파이프라인을 선택하고 평가를 시작하면, **Then** 선택한 파이프라인들에 대한 평가가 실행된다
4. **Given** 2개 이상의 파이프라인이 선택되었을 때, **When** 평가 결과가 표시되면, **Then** 파이프라인 간 성능 비교 결과가 시각적으로 표시된다

---

### Edge Cases

- **빈 검색 결과**: Retrieve 탭에서 쿼리에 대한 검색 결과가 없을 때, 사용자에게 명확한 메시지가 표시되어야 한다
- **긴 답변 생성 시간**: Generation 탭에서 답변 생성에 오랜 시간이 걸릴 때, 로딩 상태와 진행률이 표시되어야 한다
- **API 할당량 초과**: Claude API 또는 vLLM 서버의 할당량이 초과되었을 때, 사용자에게 적절한 오류 메시지가 표시되어야 한다
- **동시 요청**: 여러 사용자가 동시에 Generation 탭을 사용할 때, 각 세션이 독립적으로 관리되어야 한다
- **대화 컨텍스트 제한**: 채팅 세션이 길어져 컨텍스트 제한에 도달했을 때, 시스템이 적절히 처리하거나 사용자에게 알려야 한다
- **파이프라인 설정 변경**: 평가 중인 파이프라인의 설정이 변경되었을 때, 평가 결과의 유효성이 표시되어야 한다
- **데이터셋이 없는 파이프라인**: Evaluation 탭에서 특정 데이터셋을 선택했을 때 해당 데이터셋을 사용하는 파이프라인이 없으면, 안내 메시지가 표시되어야 한다

## Requirements *(mandatory)*

### Functional Requirements

#### Retrieve Tab

- **FR-001**: 시스템은 기존 Query 탭의 이름을 "Retrieve"로 변경해야 한다
- **FR-002**: Retrieve 탭은 기존 Query 탭의 모든 기능(파이프라인 선택, 쿼리 입력, 검색 실행)을 유지해야 한다
- **FR-003**: Retrieve 탭은 검색 결과와 함께 성능 메트릭(검색 시간, 검색된 문서 개수, 관련도 점수)을 표시해야 한다

#### Generation Tab

- **FR-004**: 시스템은 새로운 "Generation" 탭을 제공해야 한다
- **FR-005**: Generation 탭은 파이프라인 선택 인터페이스를 제공해야 한다
- **FR-006**: Generation 탭은 생성 모델 선택 인터페이스를 제공해야 한다 (Claude 또는 vLLM)
- **FR-007**: Generation 탭은 채팅 형태의 사용자 인터페이스를 제공해야 한다
- **FR-008**: 시스템은 사용자의 질문을 받아 선택된 파이프라인으로 관련 문서를 검색해야 한다
- **FR-009**: 시스템은 검색된 문서를 컨텍스트로 사용하여 선택된 생성 모델로 답변을 생성해야 한다
- **FR-010**: 시스템은 생성된 답변과 함께 참조된 문서 정보를 표시해야 한다
- **FR-011**: 시스템은 채팅 세션 내에서 대화 맥락을 유지해야 한다

#### Claude Integration

- **FR-012**: 시스템은 Claude API를 통한 답변 생성을 지원해야 한다
- **FR-013**: 시스템은 사용자가 Claude API 토큰을 설정할 수 있는 인터페이스를 제공해야 한다
- **FR-014**: 시스템은 사용 가능한 Claude 모델 목록(claude-3-opus, claude-3-sonnet 등)을 제공해야 한다
- **FR-015**: 시스템은 Claude API 호출 오류를 감지하고 사용자에게 알려야 한다

#### vLLM Integration

- **FR-016**: 시스템은 vLLM HTTP 엔드포인트를 통한 답변 생성을 지원해야 한다
- **FR-017**: 시스템은 사용자가 vLLM 서버 엔드포인트와 모델 이름을 설정할 수 있는 인터페이스를 제공해야 한다
- **FR-018**: 시스템은 vLLM 서버 연결 상태를 확인하는 기능을 제공해야 한다
- **FR-019**: 시스템은 vLLM 서버 연결 오류를 감지하고 사용자에게 알려야 한다

#### Evaluation Enhancement

- **FR-020**: Evaluation 탭은 평가 데이터셋 선택 인터페이스를 제공해야 한다
- **FR-021**: 시스템은 선택된 데이터셋을 사용하는 파이프라인만 필터링하여 표시해야 한다
- **FR-022**: 시스템은 사용자가 1개 이상의 파이프라인을 선택하여 평가를 실행할 수 있어야 한다
- **FR-023**: 시스템은 2개 이상의 파이프라인이 선택되었을 때 비교 결과를 시각적으로 표시해야 한다
- **FR-024**: 시스템은 선택된 데이터셋에 해당하는 파이프라인이 없을 때 안내 메시지를 표시해야 한다

### Key Entities

- **Retrieve Tab**: 검색 성능 측정을 위한 탭. 파이프라인, 쿼리, 검색 결과, 성능 메트릭을 포함
- **Generation Tab**: 답변 생성 테스트를 위한 탭. 파이프라인, 생성 모델, 채팅 세션, 질문/답변 쌍, 참조 문서를 포함
- **Generation Model**: 답변 생성에 사용되는 모델. 타입(Claude/vLLM), 모델 이름, 설정 정보(API 토큰 또는 엔드포인트)를 포함
- **Chat Session**: Generation 탭의 대화 세션. 메시지 목록(질문/답변), 대화 맥락, 선택된 파이프라인/모델을 포함
- **Evaluation Dataset Filter**: 평가 데이터셋 기반 파이프라인 필터링. 선택된 데이터셋, 필터링된 파이프라인 목록, 비교 대상 파이프라인을 포함

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 사용자는 Retrieve 탭에서 쿼리를 입력하고 3초 이내에 검색 결과와 성능 메트릭을 확인할 수 있다
- **SC-002**: 사용자는 Generation 탭에서 질문을 입력하고 30초 이내에 생성된 답변과 참조 문서를 확인할 수 있다
- **SC-003**: 사용자는 Claude 또는 vLLM 모델을 선택하여 5번의 연속적인 대화를 오류 없이 진행할 수 있다
- **SC-004**: 사용자는 Evaluation 탭에서 데이터셋을 선택하면 1초 이내에 필터링된 파이프라인 목록을 확인할 수 있다
- **SC-005**: 사용자는 Evaluation 탭에서 2개 이상의 파이프라인을 선택하여 비교 평가를 수행하고 결과를 시각적으로 확인할 수 있다
- **SC-006**: 시스템은 Generation 탭에서 10개의 동시 채팅 세션을 성능 저하 없이 처리할 수 있다
- **SC-007**: 사용자는 Generation 탭에서 답변 생성 시 참조된 문서를 즉시 확인하여 답변의 근거를 검증할 수 있다

## Assumptions

- 사용자는 이미 파이프라인을 생성하고 문서를 인덱싱한 상태입니다
- Claude API 사용을 위해서는 사용자가 자체 API 키를 보유하고 있어야 합니다
- vLLM 서버는 사용자가 별도로 호스팅하고 있으며, 표준 vLLM HTTP API를 따릅니다
- 평가 데이터셋은 이미 시스템에 업로드되어 있으며, 파이프라인 생성 시 데이터셋을 선택한 상태입니다
- 채팅 세션의 대화 맥락은 브라우저 세션 내에서만 유지되며, 새로고침 시 초기화됩니다
- 답변 생성 시 사용되는 프롬프트 템플릿은 시스템에서 제공하는 기본 템플릿을 사용합니다

## Out of Scope

- 생성 모델의 프롬프트 템플릿 커스터마이징 기능
- 채팅 세션의 영구 저장 및 히스토리 관리
- 답변 품질에 대한 자동 평가 메트릭 (사용자가 수동으로 평가)
- 실시간 스트리밍 답변 생성 (답변은 전체가 생성된 후 한 번에 표시)
- 다중 턴 대화에서 이전 검색 결과 재사용 최적화
- OpenAI, Gemini 등 다른 생성 모델 제공자 지원
- 파이프라인별 생성 모델 기본값 설정
