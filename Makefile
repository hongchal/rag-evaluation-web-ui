.PHONY: help install dev backend frontend docker docker-down docker-logs test lint format db-migrate db-reset clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev: ## Start development servers (requires Docker services)
	@echo "Starting Docker services..."
	docker compose up -d postgres qdrant
	@echo "Starting backend and frontend..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5174"
	@echo ""
	@echo "Run 'make backend' and 'make frontend' in separate terminals"

backend: ## Start backend server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start frontend server
	cd frontend && npm run dev

docker: ## Start all services with Docker Compose
	docker compose up -d

docker-down: ## Stop all Docker services
	docker compose down

docker-logs: ## View Docker logs
	docker compose logs -f

test: ## Run tests
	@echo "Running backend tests..."
	cd backend && pytest || true
	@echo "Running frontend tests..."
	cd frontend && npm test || true

lint: ## Run linters
	@echo "Linting backend..."
	cd backend && ruff check . || true
	@echo "Linting frontend..."
	cd frontend && npm run lint || true

format: ## Format code
	@echo "Formatting backend..."
	cd backend && ruff format . || true
	@echo "Formatting frontend..."
	cd frontend && npm run format || true

db-migrate: ## Run database migrations
	cd backend && alembic upgrade head

db-reset: ## Reset database
	docker compose down -v
	docker compose up -d postgres qdrant
	@echo "Waiting for database to be ready..."
	sleep 3
	cd backend && alembic upgrade head

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'node_modules' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'dist' -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.venv .venv
	@echo "Clean complete!"

