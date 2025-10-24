"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.core.database import init_db

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting up RAG Evaluation API")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create upload directory
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory created", path=str(settings.upload_path))

    yield

    # Shutdown
    logger.info("Shutting down RAG Evaluation API")


# Create FastAPI app
app = FastAPI(
    title="RAG Evaluation API",
    description="API for evaluating and comparing RAG strategies",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG Evaluation API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
# TODO: Add routers when implemented
# from app.api import files, strategies, evaluations
# app.include_router(files.router, prefix="/api/files", tags=["files"])
# app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
# app.include_router(evaluations.router, prefix="/api/evaluations", tags=["evaluations"])
