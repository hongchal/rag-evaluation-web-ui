#!/usr/bin/env python3
"""
Clean up old sample datasets from database.
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.evaluation_dataset import EvaluationDataset


def cleanup_old_samples():
    """Remove old sample datasets."""
    
    db = SessionLocal()
    
    try:
        # Find all sample datasets
        samples = db.query(EvaluationDataset).filter(
            EvaluationDataset.name.like("%Sample%")
        ).all()
        
        print(f"Found {len(samples)} sample datasets:\n")
        
        for sample in samples:
            print(f"  ID: {sample.id}")
            print(f"  Name: {sample.name}")
            print(f"  URI: {sample.dataset_uri}")
            print()
        
        # Ask for confirmation
        if samples:
            response = input("Delete all sample datasets except 'Sample FRAMES (30 queries)'? (y/N): ")
            
            if response.lower() == 'y':
                deleted_count = 0
                for sample in samples:
                    if sample.name != "Sample FRAMES (30 queries)":
                        print(f"Deleting: {sample.name} (ID: {sample.id})")
                        db.delete(sample)
                        deleted_count += 1
                
                db.commit()
                print(f"\n✅ Deleted {deleted_count} old sample dataset(s)")
                
                # Show remaining
                remaining = db.query(EvaluationDataset).filter(
                    EvaluationDataset.name.like("%Sample%")
                ).all()
                
                if remaining:
                    print("\n📋 Remaining sample datasets:")
                    for sample in remaining:
                        print(f"  - {sample.name} (ID: {sample.id})")
            else:
                print("Cancelled.")
        else:
            print("No sample datasets found.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("🧹 Sample Dataset Cleanup Tool\n")
    cleanup_old_samples()

