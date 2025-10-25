"""
Database migration script - 동기적으로 테이블 생성

새로운 Pipeline 모델 테이블을 생성합니다.
"""
from sqlalchemy import create_engine
from app.core.config import settings
from app.core.database import Base

# Import all models to register them
from app.models import (
    Document,
    Evaluation,
    EvaluationResult,
    Strategy,
    RAGConfiguration,
    DataSource,
    EvaluationDataset,
    EvaluationQuery,
    EvaluationDocument,
    Pipeline,
)

def migrate():
    """Create all tables"""
    # PostgreSQL 동기 엔진 생성
    sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_database_url)
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")
    
    # Show created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n📊 Total tables: {len(tables)}")
    for table in sorted(tables):
        print(f"  - {table}")

if __name__ == "__main__":
    migrate()

