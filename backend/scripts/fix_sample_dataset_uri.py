#!/usr/bin/env python3
"""
Fix Sample FRAMES dataset URI.
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.evaluation_dataset import EvaluationDataset


def fix_sample_dataset_uri():
    """Update Sample FRAMES dataset URI to correct file."""
    
    db = SessionLocal()
    
    try:
        # Find Sample FRAMES dataset
        sample = db.query(EvaluationDataset).filter(
            EvaluationDataset.name == "Sample FRAMES (30 queries)"
        ).first()
        
        if not sample:
            print("❌ Sample FRAMES dataset not found")
            return
        
        print(f"Found dataset: {sample.name} (ID: {sample.id})")
        print(f"Current URI: {sample.dataset_uri}")
        
        # Update URI
        new_uri = "local://datasets/sample_frames_eval.json"
        sample.dataset_uri = new_uri
        
        db.commit()
        
        print(f"✅ Updated URI to: {new_uri}")
        
        # Verify file exists
        dataset_file = backend_dir / "datasets" / "sample_frames_eval.json"
        if dataset_file.exists():
            print(f"✅ File exists: {dataset_file}")
        else:
            print(f"⚠️  File not found: {dataset_file}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("🔧 Fixing Sample FRAMES Dataset URI...\n")
    fix_sample_dataset_uri()

