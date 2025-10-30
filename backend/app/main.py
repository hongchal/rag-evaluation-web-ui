"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.core.database import init_db

# Configure Python's standard logging first
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# Configure structured logging to work WITH standard logging
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

    # Seed default RAG configurations
    from app.core.database import SessionLocal
    from app.services.rag_service import RAGService
    from app.models.evaluation_dataset import EvaluationDataset
    
    db = SessionLocal()
    try:
        default_rags = RAGService.seed_default_rags(db)
        logger.info("Default RAGs seeded", count=len(default_rags))
        
        # Clean up orphaned downloading datasets (from server crashes/restarts)
        orphaned = db.query(EvaluationDataset).filter(
            EvaluationDataset.status == "downloading"
        ).all()
        
        if orphaned:
            for dataset in orphaned:
                dataset.status = "failed"
                dataset.download_error = "Download interrupted by server restart"
                logger.warning(
                    "cleaned_orphaned_download", 
                    dataset_id=dataset.id, 
                    name=dataset.name
                )
            db.commit()
            logger.info("Cleaned up orphaned downloads", count=len(orphaned))
    except Exception as e:
        logger.error("Failed to seed default RAGs", error=str(e))
    finally:
        db.close()

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
from app.api.routes import rags, datasources, datasets, evaluate, query, pipelines, models, chat, prompts

app.include_router(rags.router)
app.include_router(datasources.router)
app.include_router(datasets.router)
app.include_router(evaluate.router)
app.include_router(models.router)
app.include_router(query.router)
app.include_router(pipelines.router)
app.include_router(chat.router)
app.include_router(prompts.router)
