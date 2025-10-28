# RAG Evaluation Web UI

A comprehensive web application for evaluating and comparing different RAG (Retrieval-Augmented Generation) strategies.

## Features

- **Document Upload**: Support for TXT, PDF, and JSON file uploads
- **Dataset Preparation**: Built-in scripts for downloading benchmark datasets (FRAMES, BEIR, Wikipedia, MS MARCO)
- **Strategy Selection**: Choose from various chunking, embedding, and reranking strategies
- **Real-time Monitoring**: Live progress tracking during evaluation
- **Performance Comparison**: Visual dashboards comparing different RAG configurations
- **Metrics**: NDCG@K, MRR, Precision, Recall, and more

## Tech Stack

### Frontend
- React 19 with Vite
- TanStack Router for file-based routing
- shadcn/ui components
- Tailwind CSS v4

### Backend
- Python FastAPI
- PostgreSQL for metadata storage
- Qdrant for vector storage (하이브리드 서치 지원)
- SQLAlchemy ORM
- **Embeddings**: BGE-M3 (Dense + Sparse), Matryoshka, vLLM HTTP
- **Reranking**: CrossEncoder, BM25, vLLM HTTP
- **Chunking**: Recursive, Hierarchical, Semantic, Late Chunking (Jina v3)

## Prerequisites

- [mise](https://mise.jdx.dev/) (권장) 또는:
  - Node.js 20+
  - Python 3.11+
- Docker & Docker Compose

## Environment Setup

### 환경변수 설정

모든 환경변수는 **프로젝트 루트의 `.env` 파일 하나에서 관리**합니다.

```bash
# 1. 템플릿 복사
cp .env.example .env

# 2. 필요한 값 수정 (API 키, 포트 등)
vim .env
```

#### 주요 설정 항목

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/rag_evaluation

# Qdrant
QDRANT_URL=http://localhost:6335

# AI Services
ANTHROPIC_API_KEY=your-api-key-here

# 기타 설정들...
```

**장점**:
- ✅ 한 곳에서만 관리 (`.env` 파일 하나)
- ✅ `docker-compose`와 로컬 실행 모두 같은 설정 사용
- ✅ 포트 변경 시 한 번만 수정하면 됨

## Quick Start

### Using mise (권장) 또는 Make

#### mise 사용

```bash
# mise 설치 (macOS)
brew install mise

# 또는 (Linux/macOS)
curl https://mise.run | sh

# 프로젝트 디렉토리로 이동
cd rag-evaluation-web-ui

# mise 활성화 (shell에 따라 다름)
# bash
echo 'eval "$(mise activate bash)"' >> ~/.bashrc
source ~/.bashrc

# zsh
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc
source ~/.zshrc

# fish
echo 'mise activate fish | source' >> ~/.config/fish/config.fish

# 🚀 원클릭 셋업 (권장!)
mise trust                    # .mise.toml 신뢰
mise run dev:all              # 모든 환경 자동 설정 및 Docker 시작

# 그 다음 별도 터미널에서:
mise run backend              # Backend 서버 시작
mise run frontend             # Frontend 서버 시작

# 또는 한 번에 실행 (백그라운드):
mise run dev:serve            # Backend + Frontend 동시 실행
```

**`mise run dev:all`이 하는 일:**
1. ✅ Python 3.11, Node 20 자동 설치
2. ✅ Backend 의존성 설치 (pip)
3. ✅ Frontend 의존성 설치 (npm)
4. ✅ Docker 서비스 시작 (Postgres, Qdrant)
5. ✅ 환경 파일 복사 (.env)

**수동 설정 (단계별):**
```bash
# 도구 설치 (Python 3.11, Node 20)
mise install

# 의존성 설치
mise run install

# Docker 서비스 시작 (Postgres, Qdrant)
mise run docker

# 개발 서버 시작
mise run dev
# 또는 개별 실행
mise run backend  # Backend만
mise run frontend # Frontend만
```

**유용한 mise 명령어:**
```bash
# 셋업 & 실행
mise run dev:all       # 🚀 원클릭 전체 셋업 (처음 시작할 때)
mise run dev:serve     # Backend + Frontend 동시 실행
mise run backend       # Backend만 실행
mise run frontend      # Frontend만 실행

# Docker 관리
mise run docker        # Docker 서비스 시작
mise run docker-down   # Docker 서비스 중지
mise run docker-logs   # Docker 로그 보기

# 개발 도구
mise run test          # 테스트 실행
mise run lint          # Lint 실행
mise run format        # 코드 포맷팅

# 데이터베이스
mise run db-migrate    # DB 마이그레이션
mise run db-reset      # DB 초기화

# 유틸리티
mise run install       # 의존성만 설치
mise run clean         # 빌드 아티팩트 정리
```

#### Make 사용 (mise 없이)

```bash
# 사용 가능한 명령어 확인
make help

# 의존성 설치
make install

# Docker 서비스 시작
make docker

# 개발 서버 시작 (별도 터미널에서)
make backend   # 터미널 1
make frontend  # 터미널 2

# 기타 유용한 명령어
make test           # 테스트 실행
make lint           # Lint 실행
make format         # 코드 포맷팅
make db-migrate     # DB 마이그레이션
make db-reset       # DB 초기화
make clean          # 빌드 아티팩트 정리
make docker-down    # Docker 서비스 중지
make docker-logs    # Docker 로그 보기
```

### Using Docker Compose

```bash
# Clone or navigate to the project
cd rag-evaluation-web-ui

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:5174
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# PostgreSQL: localhost:5433 (포트 충돌 방지)
# Qdrant: localhost:6335 (포트 충돌 방지)
```

**포트 설정:**
- PostgreSQL: `5433:5432` (호스트:컨테이너)
- Qdrant: `6335:6333`, `6336:6334`
- 다른 서비스와 포트 충돌을 피하기 위해 기본 포트에서 변경되었습니다

### Local Development (mise 없이)

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp env.example .env
# Edit .env with your configuration

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Project Structure

```
rag-evaluation-web-ui/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Core configurations
│   │   ├── models/        # Database models
│   │   ├── services/      # Business logic
│   │   └── main.py        # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/        # TanStack Router routes
│   │   ├── components/    # React components
│   │   └── lib/           # Utilities
│   └── package.json
└── docker-compose.yml
```

## Usage

1. **Upload Documents**: Navigate to the upload page and drag-drop your PDF or TXT files
2. **Configure Evaluation**: Select your desired chunking, embedding, and reranking strategies
3. **Run Evaluation**: Start the evaluation and monitor progress in real-time
4. **View Results**: Analyze performance metrics and compare different strategies

## Available Strategies

### Chunking
- Recursive Character Text Splitter
- Hierarchical Chunker
- Semantic Chunker

### Embedding
- BGE-M3
- Matryoshka Embeddings
- Custom embeddings

### Reranking
- Cross-encoder reranking
- Semantic similarity reranking

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

## License

MIT

