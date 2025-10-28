#!/usr/bin/env python3
"""
Sample dataset registration script.
Registers the sample test dataset to the database.
"""
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.evaluation_dataset import EvaluationDataset
from app.models.evaluation_query import EvaluationQuery
from app.models.evaluation_document import EvaluationDocument
import json


def register_sample_dataset():
    """Register sample FRAMES dataset to database."""
    
    db = SessionLocal()
    
    try:
        # Check if already exists
        existing = db.query(EvaluationDataset).filter(
            EvaluationDataset.name == "Sample FRAMES (30 queries)"
        ).first()
        
        if existing:
            print(f"⚠️  Dataset 'Sample FRAMES (30 queries)' already exists (ID: {existing.id})")
            print("   Deleting and recreating...")
            db.delete(existing)
            db.commit()
        
        # Load dataset JSON
        dataset_path = backend_dir / "datasets" / "sample_frames_eval.json"
        
        if not dataset_path.exists():
            print(f"❌ Dataset file not found: {dataset_path}")
            return
        
        with open(dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create dataset
        dataset = EvaluationDataset(
            name=data["name"],
            description=data["description"],
            dataset_uri=f"local://datasets/sample_test_eval.json",
            num_queries=data["num_queries"],
            num_documents=data["num_documents"],
            status='ready',
        )
        
        db.add(dataset)
        db.flush()  # Get dataset.id
        
        print(f"✅ Created dataset: {dataset.name} (ID: {dataset.id})")
        
        # Add queries
        for query_data in data["queries"]:
            query = EvaluationQuery(
                dataset_id=dataset.id,
                query=query_data["query"],
                relevant_doc_ids=query_data["relevant_doc_ids"],
            )
            db.add(query)
        
        print(f"✅ Added {len(data['queries'])} queries")
        
        # Add documents
        for doc_data in data["documents"]:
            document = EvaluationDocument(
                dataset_id=dataset.id,
                doc_id=doc_data["id"],
                title=doc_data.get("title", ""),
                content=doc_data["content"],
                extra_metadata=doc_data.get("metadata", {}),
            )
            db.add(document)
        
        print(f"✅ Added {len(data['documents'])} documents")
        
        db.commit()
        
        print("\n🎉 Successfully registered sample dataset!")
        print(f"   Dataset ID: {dataset.id}")
        print(f"   Name: {dataset.name}")
        print(f"   Queries: {dataset.num_queries}")
        print(f"   Documents: {dataset.num_documents}")
        print("\n📋 Next steps:")
        print("   1. Go to http://localhost:5174/pipelines")
        print("   2. Create a 'Test Pipeline' with this dataset")
        print("   3. Go to http://localhost:5174/evaluate")
        print("   4. Select the dataset and pipeline to run evaluation")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Registering Sample FRAMES Dataset (30 queries)...\n")
    register_sample_dataset()

