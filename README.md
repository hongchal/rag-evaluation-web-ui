# RAG Evaluation Web UI

A comprehensive web application for evaluating and comparing different RAG (Retrieval-Augmented Generation) strategies.

## Features

- **Document Upload**: Support for PDF and TXT file uploads
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
- Qdrant for vector storage
- SQLAlchemy ORM

## Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone or navigate to the project
cd rag-evaluation-web-ui

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:5174
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
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

