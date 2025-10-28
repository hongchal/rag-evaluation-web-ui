#!/usr/bin/env python3
"""
Create a sample dataset from FRAMES with 30 queries.
"""
import json
from pathlib import Path


def create_frames_sample():
    """Extract 30 queries and their documents from FRAMES dataset."""
    
    backend_dir = Path(__file__).parent.parent
    frames_path = backend_dir / "datasets" / "frames_eval.json"
    output_path = backend_dir / "datasets" / "sample_frames_eval.json"
    
    if not frames_path.exists():
        print(f"❌ FRAMES dataset not found: {frames_path}")
        return
    
    print("📖 Loading FRAMES dataset...")
    with open(frames_path, 'r', encoding='utf-8') as f:
        frames_data = json.load(f)
    
    print(f"✅ Loaded {len(frames_data['queries'])} queries")
    print(f"✅ Loaded {len(frames_data['documents'])} documents")
    
    # Take first 30 queries
    sample_queries = frames_data['queries'][:30]
    
    # Collect all document IDs referenced by these queries
    doc_ids_needed = set()
    for query in sample_queries:
        doc_ids_needed.update(query['relevant_doc_ids'])
    
    print(f"📋 Selected {len(sample_queries)} queries")
    print(f"📄 Need {len(doc_ids_needed)} unique documents")
    
    # Extract only the needed documents
    doc_map = {doc['id']: doc for doc in frames_data['documents']}
    sample_documents = [doc_map[doc_id] for doc_id in doc_ids_needed if doc_id in doc_map]
    
    # Create sample dataset
    sample_data = {
        "name": "Sample FRAMES (30 queries)",
        "description": "Sample dataset from Google FRAMES benchmark - 30 queries for testing RAG evaluation",
        "num_queries": len(sample_queries),
        "num_documents": len(sample_documents),
        "queries": sample_queries,
        "documents": sample_documents
    }
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Created sample dataset: {output_path}")
    print(f"   Queries: {len(sample_queries)}")
    print(f"   Documents: {len(sample_documents)}")
    print(f"\n📊 Sample queries:")
    for i, query in enumerate(sample_queries[:5]):
        print(f"   {i+1}. {query['query'][:80]}...")
    print(f"   ... and {len(sample_queries) - 5} more queries")
    

if __name__ == "__main__":
    print("🚀 Creating FRAMES sample dataset...\n")
    create_frames_sample()

