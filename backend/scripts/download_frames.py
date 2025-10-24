#!/usr/bin/env python3
"""
Download and convert FRAMES dataset for RAG evaluation.

FRAMES (Factual RAG Multi-hop Evaluation System) is a benchmark dataset
designed specifically for evaluating RAG systems with multi-hop reasoning.

Dataset: google/frames-benchmark
Paper: https://arxiv.org/abs/2409.12941
Size: 824 question-answer pairs
Domain: Wikipedia (multi-hop reasoning)

Usage:
    # Download full dataset with Wikipedia content
    python scripts/download_frames.py --fetch-wikipedia

    # Quick sample for testing (100 queries, no Wikipedia fetch)
    python scripts/download_frames.py --sample --no-fetch-wikipedia

    # Custom output path
    python scripts/download_frames.py --output datasets/my_frames.json --max-queries 200
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog

logger = structlog.get_logger(__name__)


def download_frames():
    """Download FRAMES dataset from HuggingFace."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("❌ Error: 'datasets' library not installed")
        print("   Install with: pip install datasets")
        sys.exit(1)

    print("\n📥 Downloading FRAMES benchmark from HuggingFace...")
    try:
        dataset = load_dataset('google/frames-benchmark', split='test')
        print(f"✓ Downloaded {len(dataset)} examples")
        return dataset
    except Exception as e:
        print(f"❌ Failed to download FRAMES: {e}")
        print("\nTrying alternative approach...")
        # Fallback: Try without split specification
        try:
            dataset = load_dataset('google/frames-benchmark')
            if hasattr(dataset, 'keys'):
                split_name = list(dataset.keys())[0]
                dataset = dataset[split_name]
                print(f"✓ Downloaded {len(dataset)} examples from '{split_name}' split")
                return dataset
        except Exception as e2:
            print(f"❌ Alternative also failed: {e2}")
            sys.exit(1)


def fetch_wikipedia_content(wiki_url: str) -> tuple:
    """
    Fetch actual Wikipedia content using Wikipedia API.

    Returns:
        Tuple of (content, title)
    """
    import requests
    from time import sleep

    try:
        # Extract article title from URL
        title = wiki_url.split('/')[-1].replace('_', ' ')

        # Use Wikipedia REST API for summary (fast, no rate limits)
        api_title = wiki_url.split('/')[-1]
        api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{api_title}"

        response = requests.get(api_url, timeout=10, headers={
            'User-Agent': 'RAG-Evaluation/1.0 (Educational; Contact: your@email.com)'
        })

        if response.ok:
            data = response.json()
            content = data.get('extract', '')

            # If we need more content, fetch the full article
            if len(content) < 200:
                # Fallback to full content API
                full_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={api_title}&format=json"
                full_response = requests.get(full_url, timeout=10)
                if full_response.ok:
                    pages = full_response.json().get('query', {}).get('pages', {})
                    page_id = list(pages.keys())[0]
                    content = pages[page_id].get('extract', content)

            return content, title
        else:
            logger.warning(f"Failed to fetch {wiki_url}: {response.status_code}")
            return "", title

    except Exception as e:
        logger.error(f"Error fetching {wiki_url}: {e}")
        return "", wiki_url.split('/')[-1].replace('_', ' ')


def convert_to_evaluation_format(
    frames_dataset, 
    max_queries: int = None, 
    fetch_wikipedia: bool = True
):
    """
    Convert FRAMES dataset to evaluation format.

    FRAMES format:
    - Prompt: The question to answer
    - Answer: Ground truth answer
    - wikipedia_link_1 to wikipedia_link_11+: Related Wikipedia URLs
    - reasoning_types: Type of reasoning required

    Evaluation format:
    - documents: List of documents with id, content, title, metadata
    - queries: List of queries with query, relevant_doc_ids, expected_answer
    """
    print("\n🔄 Converting to evaluation format...")
    print(f"   Fetch Wikipedia content: {fetch_wikipedia}")

    if not fetch_wikipedia:
        print("   ⚠️  WARNING: Not fetching Wikipedia content!")
        print("   ⚠️  This will use placeholder content only!")
        print("   ⚠️  Set --fetch-wikipedia for proper evaluation")

    documents = []
    queries = []
    doc_id_map = {}

    total_examples = len(frames_dataset)
    if max_queries:
        total_examples = min(total_examples, max_queries)
        frames_dataset = frames_dataset.select(range(total_examples))

    for idx, example in enumerate(frames_dataset):
        if (idx + 1) % 50 == 0:
            print(f"  Processing {idx + 1}/{total_examples}...")

        # Extract question and answer
        question = example.get('Prompt', '')
        answer = example.get('Answer', '')

        # Skip if no valid question or answer
        if not question or not question.strip():
            logger.warning(f"Skipping {idx}: no valid question")
            continue

        if not answer or not answer.strip():
            logger.warning(f"Skipping {idx}: no valid answer")
            continue

        # Extract Wikipedia links
        wiki_links = []
        for i in range(1, 12):
            link_key = f'wikipedia_link_{i}' if i <= 10 else 'wikipedia_link_11+'
            link = example.get(link_key)
            if link and isinstance(link, str) and link.startswith('http'):
                wiki_links.append(link)

        if not wiki_links:
            logger.warning(f"Skipping {idx}: no Wikipedia links")
            continue

        # Create documents from Wikipedia links
        relevant_doc_ids = []
        for doc_idx, wiki_url in enumerate(wiki_links):
            doc_id = f"frames_q{idx}_doc{doc_idx}"

            if fetch_wikipedia:
                # Fetch actual Wikipedia content
                from time import sleep
                content, title = fetch_wikipedia_content(wiki_url)

                if not content:
                    logger.warning(f"Empty content for {wiki_url}, skipping document")
                    continue

                # Rate limiting
                sleep(0.1)
            else:
                # Placeholder content
                title = wiki_url.split('/')[-1].replace('_', ' ')
                content = f"[PLACEHOLDER]\nWikipedia URL: {wiki_url}\n\nEnable --fetch-wikipedia for actual content."

            if doc_id not in doc_id_map:
                documents.append({
                    "id": doc_id,
                    "content": content,
                    "title": title,
                    "metadata": {
                        "source": "frames",
                        "wikipedia_url": wiki_url,
                        "question_idx": idx,
                        "content_length": len(content)
                    }
                })
                doc_id_map[doc_id] = True
                relevant_doc_ids.append(doc_id)

        # Create query
        queries.append({
            "query": question,
            "relevant_doc_ids": relevant_doc_ids,
            "expected_answer": answer,
            "difficulty": "hard",  # FRAMES is designed for multi-hop reasoning
            "query_type": example.get('reasoning_types', 'multi-hop'),
            "metadata": {
                "source": "frames",
                "question_idx": idx,
                "reasoning_type": example.get('reasoning_types', ''),
                "num_wikipedia_links": len(wiki_links)
            }
        })

    print(f"✓ Converted {len(queries)} queries and {len(documents)} documents")

    if len(queries) == 0:
        print("⚠️  Warning: No queries converted!")
        print("   This might indicate a dataset format issue.")

    return {
        "name": "FRAMES-RAG",
        "description": "Google FRAMES benchmark for RAG evaluation with multi-hop reasoning",
        "documents": documents,
        "queries": queries,
        "metadata": {
            "source": "google/frames-benchmark",
            "version": "2024",
            "total_examples": total_examples,
            "converted_queries": len(queries),
            "converted_documents": len(documents),
            "fetched_wikipedia": fetch_wikipedia
        }
    }


def save_dataset(dataset: Dict, output_path: Path):
    """Save dataset to JSON file."""
    print(f"\n💾 Saving to {output_path}...")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved successfully")


def verify_dataset(dataset: Dict):
    """Verify dataset has required fields."""
    print("\n🔍 Verifying dataset...")

    required_fields = ['name', 'description', 'documents', 'queries']
    for field in required_fields:
        if field not in dataset:
            print(f"❌ Missing required field: {field}")
            return False

    # Check queries have expected_answer
    queries_with_answer = sum(
        1 for q in dataset['queries']
        if q.get('expected_answer')
    )

    print(f"✓ Dataset structure valid")
    print(f"✓ Queries: {len(dataset['queries'])}")
    print(f"✓ Documents: {len(dataset['documents'])}")
    print(f"✓ Queries with expected_answer: {queries_with_answer}/{len(dataset['queries'])}")

    if queries_with_answer == 0:
        print("❌ Warning: No queries have expected_answer!")
        return False

    # Show sample
    if dataset['queries']:
        print(f"\n📋 Sample query:")
        sample = dataset['queries'][0]
        print(f"  Query: {sample['query'][:80]}...")
        print(f"  Expected Answer: {sample['expected_answer'][:80]}...")
        print(f"  Relevant Docs: {len(sample['relevant_doc_ids'])}")

    return True


def register_to_db(dataset_path: Path):
    """Register dataset to database."""
    try:
        # Add scripts directory to path for importing dataset_registry
        scripts_dir = Path(__file__).parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        
        from dataset_registry import register_dataset, init_db
        from app.core.database import SessionLocal
        
        print(f"\n📝 Registering dataset to database...")
        
        # Initialize database
        init_db()
        
        # Create session
        db = SessionLocal()
        
        try:
            register_dataset(dataset_path, db)
            print(f"✅ Dataset registered successfully!")
        finally:
            db.close()
            
    except Exception as e:
        print(f"⚠️  Failed to register dataset to database: {e}")
        print(f"   You can manually register later with:")
        print(f"   python backend/scripts/dataset_registry.py register {dataset_path}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Download and convert FRAMES dataset for RAG evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('backend/datasets/frames_eval.json'),
        help='Output path for converted dataset'
    )
    parser.add_argument(
        '--max-queries',
        type=int,
        default=None,
        help='Maximum number of queries to convert (default: all)'
    )
    parser.add_argument(
        '--sample',
        action='store_true',
        help='Create small sample (100 queries) for testing'
    )
    parser.add_argument(
        '--fetch-wikipedia',
        action='store_true',
        default=False,
        help='Fetch actual Wikipedia content (recommended for proper evaluation)'
    )
    parser.add_argument(
        '--no-fetch-wikipedia',
        action='store_true',
        help='Do not fetch Wikipedia content (faster, but placeholder only)'
    )
    parser.add_argument(
        '--no-register',
        action='store_true',
        help='Do not register dataset to database automatically'
    )

    args = parser.parse_args()

    if args.sample:
        args.max_queries = 100

    # Determine whether to fetch Wikipedia
    fetch_wikipedia = args.fetch_wikipedia and not args.no_fetch_wikipedia

    print("="*70)
    print("FRAMES Dataset Downloader for RAG Evaluation")
    print("="*70)

    # Download
    frames_data = download_frames()

    # Convert
    dataset = convert_to_evaluation_format(
        frames_data, 
        args.max_queries,
        fetch_wikipedia=fetch_wikipedia
    )

    # Verify
    if not verify_dataset(dataset):
        print("\n❌ Dataset verification failed!")
        sys.exit(1)

    # Save
    save_dataset(dataset, args.output)

    print("\n" + "="*70)
    print("✅ FRAMES Dataset Ready!")
    print("="*70)
    print(f"\n📁 Dataset saved to: {args.output}")
    print(f"📊 Queries: {len(dataset['queries'])}")
    print(f"📚 Documents: {len(dataset['documents'])}")
    
    if fetch_wikipedia:
        print(f"✅ Wikipedia content fetched")
    else:
        print(f"⚠️  Using placeholder content (run with --fetch-wikipedia for real content)")
    
    # Auto-register to database
    if not args.no_register:
        register_to_db(args.output)
    
    print(f"\n💡 Next steps:")
    print(f"   1. Create a RAG configuration via API")
    print(f"   2. Run evaluation with this dataset")
    print(f"   3. Compare results")
    print()


if __name__ == '__main__':
    main()

