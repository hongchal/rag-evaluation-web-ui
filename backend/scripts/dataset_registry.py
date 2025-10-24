"""Dataset Registry - Register downloaded datasets to database."""

import json
import sys
from pathlib import Path
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, sync_engine, Base
from app.models.evaluation_dataset import EvaluationDataset
from app.models.evaluation_query import EvaluationQuery
from app.models.evaluation_document import EvaluationDocument
import structlog

logger = structlog.get_logger(__name__)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=sync_engine)


def register_dataset(dataset_path: Path, db: Session, load_content: bool = True) -> EvaluationDataset:
    """
    Register a dataset to the database.
    
    Args:
        dataset_path: Path to the dataset JSON file
        db: Database session
        load_content: If True, also load queries and documents into DB
        
    Returns:
        Created EvaluationDataset instance
    """
    # Load dataset JSON
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset_data = json.load(f)
    
    name = dataset_data.get('name', dataset_path.stem)
    description = dataset_data.get('description', '')
    queries_data = dataset_data.get('queries', [])
    documents_data = dataset_data.get('documents', [])
    num_queries = len(queries_data)
    num_documents = len(documents_data)
    
    # Check if dataset already exists
    existing = db.query(EvaluationDataset).filter(
        EvaluationDataset.name == name
    ).first()
    
    if existing:
        logger.info("dataset_already_exists", name=name, id=existing.id)
        print(f"⚠️  Dataset '{name}' already exists (ID: {existing.id})")
        print(f"   Updating dataset...")
        
        # Update existing dataset
        existing.description = description
        existing.dataset_uri = str(dataset_path.absolute())
        existing.num_queries = num_queries
        existing.num_documents = num_documents
        
        if load_content:
            # Delete existing queries and documents
            print(f"   Clearing old queries and documents...")
            db.query(EvaluationQuery).filter(EvaluationQuery.dataset_id == existing.id).delete()
            db.query(EvaluationDocument).filter(EvaluationDocument.dataset_id == existing.id).delete()
        
        db.commit()
        db.refresh(existing)
        dataset = existing
        
    else:
        # Create new dataset
        dataset = EvaluationDataset(
            name=name,
            description=description,
            dataset_uri=str(dataset_path.absolute()),
            num_queries=num_queries,
            num_documents=num_documents
        )
        
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        logger.info("dataset_registered", name=name, id=dataset.id)
    
    # Load content if requested
    if load_content:
        print(f"   Loading documents... ({num_documents} total)")
        
        # Load documents
        for doc_data in documents_data:
            doc = EvaluationDocument(
                dataset_id=dataset.id,
                doc_id=doc_data['id'],
                content=doc_data['content'],
                title=doc_data.get('title'),
                extra_metadata=doc_data.get('metadata', {})
            )
            db.add(doc)
        
        print(f"   Loading queries... ({num_queries} total)")
        
        # Load queries
        for idx, query_data in enumerate(queries_data):
            query = EvaluationQuery(
                dataset_id=dataset.id,
                query=query_data['query'],
                expected_answer=query_data.get('expected_answer'),
                relevant_doc_ids=query_data.get('relevant_doc_ids', []),
                difficulty=query_data.get('difficulty'),
                query_type=query_data.get('query_type'),
                extra_metadata=query_data.get('metadata', {}),
                query_idx=idx
            )
            db.add(query)
        
        db.commit()
        print(f"✅ Loaded {num_documents} documents and {num_queries} queries into DB")
    
    print(f"✅ {'Updated' if existing else 'Registered'} dataset '{name}' (ID: {dataset.id})")
    
    return dataset


def list_datasets(db: Session):
    """List all registered datasets."""
    datasets = db.query(EvaluationDataset).all()
    
    if not datasets:
        print("No datasets registered yet.")
        return
    
    print(f"\n{'='*70}")
    print(f"Registered Datasets ({len(datasets)})")
    print(f"{'='*70}\n")
    
    for dataset in datasets:
        print(f"ID: {dataset.id}")
        print(f"Name: {dataset.name}")
        print(f"Description: {dataset.description or 'N/A'}")
        print(f"Queries: {dataset.num_queries:,}")
        print(f"Documents: {dataset.num_documents:,}")
        print(f"URI: {dataset.dataset_uri}")
        print(f"Created: {dataset.created_at}")
        print("-" * 70)


def auto_register_all(datasets_dir: Path, db: Session):
    """
    Auto-register all JSON datasets in the datasets directory.
    
    Args:
        datasets_dir: Directory containing dataset JSON files
        db: Database session
    """
    if not datasets_dir.exists():
        print(f"❌ Datasets directory not found: {datasets_dir}")
        return
    
    json_files = list(datasets_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON datasets found in {datasets_dir}")
        return
    
    print(f"\n{'='*70}")
    print(f"Auto-registering datasets from {datasets_dir}")
    print(f"{'='*70}\n")
    
    registered = 0
    updated = 0
    failed = 0
    
    for json_file in json_files:
        try:
            # Check if it's a valid dataset
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate dataset structure
            if 'documents' not in data or 'queries' not in data:
                print(f"⏭️  Skipping {json_file.name} (not a valid dataset)")
                continue
            
            # Check if already registered
            name = data.get('name', json_file.stem)
            existing = db.query(EvaluationDataset).filter(
                EvaluationDataset.name == name
            ).first()
            
            if existing:
                register_dataset(json_file, db)
                updated += 1
            else:
                register_dataset(json_file, db)
                registered += 1
                
        except Exception as e:
            print(f"❌ Failed to register {json_file.name}: {e}")
            failed += 1
    
    print(f"\n{'='*70}")
    print(f"Summary:")
    print(f"  ✅ Newly registered: {registered}")
    print(f"  🔄 Updated: {updated}")
    print(f"  ❌ Failed: {failed}")
    print(f"{'='*70}\n")


def main():
    """Main CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Dataset Registry - Register datasets to database"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a dataset")
    register_parser.add_argument(
        "dataset_path",
        type=Path,
        help="Path to dataset JSON file"
    )
    
    # List command
    subparsers.add_parser("list", help="List all registered datasets")
    
    # Auto-register command
    auto_parser = subparsers.add_parser(
        "auto-register",
        help="Auto-register all datasets in directory"
    )
    auto_parser.add_argument(
        "--dir",
        type=Path,
        default=Path("backend/datasets"),
        help="Datasets directory (default: backend/datasets)"
    )
    
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    # Create database session
    db = SessionLocal()
    
    try:
        if args.command == "register":
            if not args.dataset_path.exists():
                print(f"❌ File not found: {args.dataset_path}")
                sys.exit(1)
            
            register_dataset(args.dataset_path, db)
            
        elif args.command == "list":
            list_datasets(db)
            
        elif args.command == "auto-register":
            auto_register_all(args.dir, db)
            
        else:
            parser.print_help()
            
    finally:
        db.close()


if __name__ == "__main__":
    main()

