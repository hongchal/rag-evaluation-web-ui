# Developer Quickstart Guide

**Feature**: Retrieve & Generation Tabs Separation
**Date**: 2025-10-28
**For**: Developers implementing this feature

## Overview

이 가이드는 Retrieve/Generation 탭 분리 기능을 구현하는 개발자를 위한 빠른 시작 문서입니다. 코드 구조, 개발 환경 설정, 그리고 구현 순서를 제공합니다.

## Prerequisites

### Required Tools
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (Qdrant, PostgreSQL)
- Git

### Required Knowledge
- FastAPI (Backend)
- React 19 + TypeScript (Frontend)
- TanStack Router (Routing)
- SQLAlchemy (ORM)

### Existing System Understanding
- **Current State**: `/query` 탭이 검색 기능만 제공
- **Goal**: 검색 전용 `/retrieve` 탭 + 생성 포함 `/generation` 탭 분리

## Quick Setup

### 1. Branch Setup

```bash
# Clone and checkout feature branch (already done)
cd /Users/chohongcheol/rag-evaluation-web-ui
git checkout 001-retrieve-generation-tabs

# Verify branch
git branch --show-current
# Output: 001-retrieve-generation-tabs
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment (if not exists)
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Verify key dependencies
pip list | grep anthropic  # anthropic==0.69.0
pip list | grep httpx      # httpx==0.27.2

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Backend runs at**: `http://localhost:8001`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Verify key dependencies
npm list @tanstack/react-router  # 1.133.22
npm list react                    # 19.1.1

# Start frontend
npm run dev
```

**Frontend runs at**: `http://localhost:5174`

### 4. Infrastructure (Docker Compose)

```bash
# From project root
docker-compose up -d

# Verify services
docker-compose ps
# qdrant: port 6333
# postgres: port 5432
```

## File Structure Overview

### New Files to Create

```
backend/app/services/generation/
├── __init__.py              # Package init
├── base.py                  # AbstractGenerator interface
├── claude.py                # ClaudeGenerator implementation
├── vllm_http.py             # VLLMHttpGenerator implementation
└── factory.py               # GeneratorFactory

backend/app/schemas/query.py  # [MODIFY] Add AnswerRequest, ModelConfigRequest

frontend/src/routes/
├── retrieve.tsx             # [NEW] Renamed from query.tsx
└── generation.tsx           # [NEW] Chat-based generation UI

frontend/src/components/
├── ChatMessage.tsx          # [NEW] Message bubble component
├── ModelSelector.tsx        # [NEW] Model config component
└── SourceViewer.tsx         # [NEW] Retrieved chunks display

frontend/src/hooks/
└── useChatSession.ts        # [NEW] Chat state management hook
```

### Files to Modify

```
backend/app/api/routes/query.py         # Implement /answer endpoint
backend/app/services/query_service.py   # Implement answer() method
backend/app/api/routes/pipelines.py     # Add dataset_id filter
backend/app/core/config.py              # Add model configs

frontend/src/routes/__root.tsx          # Update navigation
frontend/src/lib/api.ts                 # Add generation API calls
frontend/src/routes/evaluate.tsx        # Add dataset filtering
```

## Development Workflow

### Phase 1: Retrieve Tab (Low Risk)

**Goal**: Rename Query → Retrieve without breaking functionality

1. **Rename Route File**
   ```bash
   cd frontend/src/routes
   git mv query.tsx retrieve.tsx
   ```

2. **Update Route Definition**
   ```typescript
   // retrieve.tsx
   export const Route = createFileRoute('/retrieve')({
     component: RetrieveTab,  // Rename function
     // ... rest unchanged
   })
   ```

3. **Update Navigation**
   ```typescript
   // __root.tsx
   const navigation = [
     // ...
     { name: 'Retrieve', path: '/retrieve' },  // Changed from 'Query'
     // ...
   ]
   ```

4. **Test**
   - Visit `http://localhost:5174/retrieve`
   - Verify search works
   - Check navigation links

**Estimated Time**: 30 minutes

---

### Phase 2: Generation Backend (Foundation)

**Goal**: Implement answer generation service

#### Step 1: Abstract Generator Interface

Create `backend/app/services/generation/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class GenerationConfig:
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 0.9
    stop_sequences: Optional[List[str]] = None

@dataclass
class GenerationResult:
    answer: str
    tokens_used: int
    generation_time: float
    model_name: str

class AbstractGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        query: str,
        context: str,
        config: GenerationConfig = None,
    ) -> GenerationResult:
        """Generate answer based on query and context"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if generator is available"""
        pass
```

**Estimated Time**: 15 minutes

#### Step 2: Claude Implementation

Create `backend/app/services/generation/claude.py`:

```python
import anthropic
import structlog
import time

logger = structlog.get_logger(__name__)

class ClaudeGenerator(AbstractGenerator):
    def __init__(self, api_key: str, model_name: str = "claude-3-sonnet-20240229"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = model_name
    
    def generate(
        self,
        query: str,
        context: str,
        config: GenerationConfig = None,
    ) -> GenerationResult:
        config = config or GenerationConfig()
        
        system_prompt = """You are a helpful AI assistant..."""
        user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        
        start_time = time.time()
        
        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            
            generation_time = time.time() - start_time
            
            return GenerationResult(
                answer=message.content[0].text,
                tokens_used=message.usage.input_tokens + message.usage.output_tokens,
                generation_time=generation_time,
                model_name=self.model_name,
            )
        except Exception as e:
            logger.error("claude_generation_failed", error=str(e))
            raise
    
    def is_available(self) -> bool:
        try:
            # Simple availability check
            self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False
```

**Estimated Time**: 45 minutes

#### Step 3: QueryService Integration

Modify `backend/app/services/query_service.py`:

```python
def answer(
    self,
    pipeline_id: int,
    query: str,
    top_k: int,
    model_config: dict,
) -> dict:
    """
    Generate answer using RAG pipeline and LLM.
    
    Returns:
        dict with keys: query, answer, sources, tokens_used, total_time, search_time, llm_time
    """
    import time
    from app.services.generation.factory import GeneratorFactory
    
    # Step 1: Search for relevant chunks
    search_start = time.time()
    search_result = self.search(pipeline_id, query, top_k)
    search_time = time.time() - search_start
    
    # Step 2: Format context
    context = self._format_context(search_result.chunks)
    
    # Step 3: Create generator
    generator = GeneratorFactory.create(
        model_type=model_config["type"],
        **model_config
    )
    
    # Step 4: Generate answer
    from app.services.generation.base import GenerationConfig
    gen_config = GenerationConfig(
        temperature=model_config.get("parameters", {}).get("temperature", 0.7),
        max_tokens=model_config.get("parameters", {}).get("max_tokens", 1000),
        top_p=model_config.get("parameters", {}).get("top_p", 0.9),
    )
    
    gen_result = generator.generate(query, context, gen_config)
    
    return {
        "query": query,
        "answer": gen_result.answer,
        "sources": search_result.chunks,
        "tokens_used": gen_result.tokens_used,
        "total_time": search_time + gen_result.generation_time,
        "search_time": search_time,
        "llm_time": gen_result.generation_time,
    }

def _format_context(self, chunks: List[dict]) -> str:
    """Format chunks as context for LLM"""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Document {i}]")
        parts.append(chunk["content"])
        parts.append("")
    return "\n".join(parts)
```

**Estimated Time**: 30 minutes

#### Step 4: API Endpoint

Modify `backend/app/api/routes/query.py` (already has `/answer` endpoint skeleton):

```python
@router.post("/answer", response_model=AnswerResponse)
def answer(
    answer_request: AnswerRequest,
    query_service: QueryService = Depends(get_query_service),
):
    """Generate answer using LLM with RAG"""
    try:
        result = query_service.answer(
            pipeline_id=answer_request.pipeline_id,
            query=answer_request.query,
            top_k=answer_request.top_k,
            model_config=answer_request.model_config.dict(),
        )
        
        return AnswerResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("answer_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {str(e)}")
```

**Estimated Time**: 20 minutes

---

### Phase 3: Generation Frontend (User-Facing)

**Goal**: Create chat UI for generation

#### Step 1: Chat State Hook

Create `frontend/src/hooks/useChatSession.ts`:

```typescript
import { useState, useCallback } from 'react';

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
    id: crypto.randomUUID(),
    pipelineId,
    modelConfig,
    messages: [],
    createdAt: new Date(),
  });

  const addMessage = useCallback((message: Omit<Message, 'id' | 'timestamp'>) => {
    setSession(prev => ({
      ...prev,
      messages: [
        ...prev.messages,
        {
          ...message,
          id: crypto.randomUUID(),
          timestamp: new Date(),
        },
      ],
    }));
  }, []);

  const clearSession = useCallback(() => {
    setSession({
      id: crypto.randomUUID(),
      pipelineId,
      modelConfig,
      messages: [],
      createdAt: new Date(),
    });
  }, [pipelineId, modelConfig]);

  return { session, addMessage, clearSession };
}
```

**Estimated Time**: 20 minutes

#### Step 2: Generation Route

Create `frontend/src/routes/generation.tsx` (simplified):

```typescript
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useChatSession } from '../hooks/useChatSession'
import { api } from '../lib/api'

export const Route = createFileRoute('/generation')({
  component: GenerationTab,
})

function GenerationTab() {
  const [pipelineId, setPipelineId] = useState<number | null>(null)
  const [modelConfig, setModelConfig] = useState<ModelConfig>({
    type: 'claude',
    modelName: 'claude-3-sonnet-20240229',
    apiKey: '',
    parameters: { temperature: 0.7, maxTokens: 1000, topP: 0.9 },
  })
  
  const { session, addMessage, clearSession } = useChatSession(pipelineId, modelConfig)
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSend = async () => {
    if (!inputValue.trim() || !pipelineId) return

    // Add user message
    addMessage({ role: 'user', content: inputValue })
    setInputValue('')
    setLoading(true)

    try {
      const response = await api.generateAnswer({
        pipeline_id: pipelineId,
        query: inputValue,
        top_k: 5,
        model_config: modelConfig,
      })

      // Add assistant message
      addMessage({
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      })
    } catch (error) {
      console.error('Failed to generate answer:', error)
      // Show error message
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Generation</h1>
      
      {/* Pipeline & Model Selection */}
      <div className="mb-4">
        {/* Pipeline selector */}
        {/* Model selector */}
      </div>

      {/* Chat Messages */}
      <div className="space-y-4 mb-4">
        {session.messages.map(msg => (
          <div key={msg.id}>
            <strong>{msg.role}:</strong> {msg.content}
            {/* Render sources if assistant */}
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && handleSend()}
          disabled={loading}
          placeholder="Type your question..."
        />
        <button onClick={handleSend} disabled={loading}>
          {loading ? 'Generating...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
```

**Estimated Time**: 1 hour

---

### Phase 4: Evaluation Filtering (Enhancement)

**Goal**: Filter pipelines by dataset

#### Backend

Modify `backend/app/api/routes/pipelines.py`:

```python
@router.get("/", response_model=List[PipelineResponse])
def list_pipelines(
    dataset_id: Optional[int] = Query(None, description="Filter by dataset ID"),
    db: Session = Depends(get_db),
):
    query = db.query(Pipeline)
    
    if dataset_id is not None:
        query = query.filter(Pipeline.dataset_id == dataset_id)
    
    pipelines = query.order_by(Pipeline.created_at.desc()).all()
    return pipelines
```

**Estimated Time**: 15 minutes

#### Frontend

Modify `frontend/src/routes/evaluate.tsx`:

```typescript
const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null)

useEffect(() => {
  loadPipelines(selectedDatasetId)
}, [selectedDatasetId])

const loadPipelines = async (datasetId: number | null) => {
  const params = datasetId ? { dataset_id: datasetId } : {}
  const items = await api.listPipelines(params)
  setPipelines(items)
}

// Add dataset selector dropdown
```

**Estimated Time**: 30 minutes

---

## Testing Strategy

### Unit Tests

```bash
# Backend
cd backend
pytest tests/test_generation_service.py
pytest tests/test_query_service.py

# Frontend
cd frontend
npm test
```

### Integration Tests

```bash
# Test answer endpoint
curl -X POST http://localhost:8001/api/query/answer \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_id": 1,
    "query": "Test question",
    "top_k": 5,
    "model_config": {
      "type": "claude",
      "model_name": "claude-3-sonnet-20240229",
      "api_key": "sk-ant-xxxxx",
      "parameters": {"temperature": 0.7, "max_tokens": 1000, "top_p": 0.9}
    }
  }'
```

### Manual Testing Checklist

- [ ] Retrieve tab loads and searches work
- [ ] Generation tab loads with model selector
- [ ] Claude model generates answers with valid API key
- [ ] Chat messages display correctly
- [ ] Source documents are shown
- [ ] Error messages display for invalid config
- [ ] Evaluation tab filters pipelines by dataset
- [ ] Navigation links work

---

## Common Issues & Troubleshooting

### Issue: Claude API 401 Error

**Symptom**: "Invalid API key" error
**Solution**: Check API key format (must start with `sk-ant-`)

### Issue: vLLM Connection Refused

**Symptom**: Cannot connect to model server
**Solution**: Verify vLLM server is running and endpoint URL is correct

### Issue: Frontend Route Not Found

**Symptom**: 404 on `/retrieve` or `/generation`
**Solution**: Run `npm run dev` to regenerate route tree (`routeTree.gen.ts`)

### Issue: CORS Error

**Symptom**: Browser blocks API requests
**Solution**: Verify FastAPI CORS middleware allows frontend origin

---

## Performance Benchmarks

### Target Metrics (from Success Criteria)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Retrieve search time | < 3s | Check `retrieval_time` in response |
| Generation total time | < 30s | Check `generation_time` in response |
| Concurrent sessions | 10+ | Load test with multiple users |
| Dataset filter time | < 1s | Measure pipeline list API response |

### Measuring Performance

```python
# Backend logging
logger.info("answer_generated", 
    retrieval_time=search_time,
    llm_time=gen_result.generation_time,
    total_time=total_time,
)
```

---

## Next Steps

1. ✅ Setup complete
2. 🔄 Implement Phase 1 (Retrieve tab rename)
3. 🔄 Implement Phase 2 (Generation backend)
4. 🔄 Implement Phase 3 (Generation frontend)
5. 🔄 Implement Phase 4 (Evaluation filtering)
6. ⏳ Run `/speckit.tasks` for detailed task breakdown
7. ⏳ Write tests
8. ⏳ Manual testing
9. ⏳ Code review & merge

---

## Resources

- [Spec Document](./spec.md)
- [Research Document](./research.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/)
- [Anthropic Python SDK Docs](https://docs.anthropic.com/claude/reference/client-sdks)
- [TanStack Router Docs](https://tanstack.com/router/latest)

---

## Questions?

For questions or issues:
1. Check [research.md](./research.md) for technical decisions
2. Review [data-model.md](./data-model.md) for entity definitions
3. Check [contracts/](./contracts/) for API specifications
4. Ask the team in Slack/Discord

**Good luck! 화이팅! 🚀**

