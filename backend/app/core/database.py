"""Database connection and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=True if settings.log_level == "DEBUG" else False,
    future=True,
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create sync engine for non-async operations
sync_engine = create_engine(
    settings.database_url,
    echo=True if settings.log_level == "DEBUG" else False,
    future=True,
)

# Create sync session maker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency for getting async database sessions.

    Usage:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    # Import all models to ensure they are registered with Base
    # This must happen before create_all is called
    from app.models import (  # noqa: F401
        Document,
        Evaluation,
        EvaluationResult,
        Strategy,
        RAGConfiguration,
        DataSource,
        EvaluationDataset,
        EvaluationQuery,
        EvaluationDocument,
        BaseDocument,
        BaseChunk,
        Pipeline,
        Chunk,
    )
    
    logger.info("Creating database tables...")
    
    # Log all registered models
    table_names = [table.name for table in Base.metadata.sorted_tables]
    logger.info("Registered models", tables=table_names)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully", count=len(table_names))
        
        # Run migrations
        await run_migrations(conn)


async def run_migrations(conn):
    """Run database migrations."""
    try:
        # Migration: Add processor_type column to datasources
        logger.info("Running database migrations...")
        
        # Check if processor_type column exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='datasources' AND column_name='processor_type'
        """))
        
        exists = result.fetchone() is not None
        
        if not exists:
            logger.info("Adding processor_type column to datasources table...")
            
            # Add processor_type column
            await conn.execute(text("""
                ALTER TABLE datasources 
                ADD COLUMN processor_type VARCHAR(20) DEFAULT 'pdfplumber'
            """))
            
            # Create index
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_datasources_processor_type 
                ON datasources(processor_type)
            """))
            
            logger.info("Migration completed: processor_type column added")
        else:
            logger.info("Migration skipped: processor_type column already exists")
            
    except Exception as e:
        logger.error("Migration failed", error=str(e))
        # Don't raise - let the app continue even if migration fails
