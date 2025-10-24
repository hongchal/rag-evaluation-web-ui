#!/usr/bin/env python3
"""
Universal Dataset Preparation Script

Supports downloading and converting multiple dataset types:
- BEIR (SciFact, HotpotQA, FiQA, etc.)
- Wikipedia (various sizes)
- MS MARCO
- Custom JSON files

Usage:
    # BEIR datasets
    python scripts/prepare_dataset.py beir --name scifact
    python scripts/prepare_dataset.py beir --name hotpotqa --sample 1000

    # Wikipedia
    python scripts/prepare_dataset.py wikipedia --size 1000
    python scripts/prepare_dataset.py wikipedia --size 10000 --queries-per-doc 3

    # MS MARCO
    python scripts/prepare_dataset.py msmarco --size 10000

    # Verify existing dataset
    python scripts/prepare_dataset.py verify --dataset datasets/my_dataset.json

    # List available datasets
    python scripts/prepare_dataset.py list
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# BEIR Dataset Handler
# ============================================================================


class BEIRHandler:
    """Handler for BEIR benchmark datasets."""

    AVAILABLE_DATASETS = [
        "scifact",  # Scientific fact verification (5K docs)
        "nfcorpus",  # Nutrition (3.6K docs)
        "hotpotqa",  # Multi-hop QA (5M docs - recommend sampling)
        "fiqa",  # Financial QA (57K docs)
        "trec-covid",  # COVID-19 research (171K docs)
    ]

    @staticmethod
    def download(
        dataset_name: str, sample_size: Optional[int] = None
    ) -> Tuple[dict, dict, dict]:
        """Download BEIR dataset."""
        try:
            from beir import util
            from beir.datasets.data_loader import GenericDataLoader
        except ImportError:
            raise ImportError("BEIR not installed. Run: pip install beir")

        logger.info("downloading_beir", dataset=dataset_name)
        print(f"📥 Downloading BEIR/{dataset_name}...")

        # Download
        data_path = Path("backend/datasets/.beir")
        url = f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{dataset_name}.zip"
        dataset_path = util.download_and_unzip(url, str(data_path))

        # Load
        corpus, queries, qrels = GenericDataLoader(data_folder=dataset_path).load(
            split="test"
        )

        # Sample if requested
        if sample_size and len(corpus) > sample_size:
            logger.info("sampling_corpus", original=len(corpus), sample=sample_size)
            corpus_ids = list(corpus.keys())[:sample_size]
            corpus = {doc_id: corpus[doc_id] for doc_id in corpus_ids}

        return corpus, queries, qrels

    @staticmethod
    def convert_to_evaluation_format(
        corpus: dict, queries: dict, qrels: dict, dataset_name: str
    ) -> Dict:
        """Convert BEIR format to evaluation dataset."""

        logger.info("converting_beir", dataset=dataset_name)
        print(f"🔄 Converting {dataset_name} to evaluation format...")

        # Convert documents
        documents = []
        doc_id_set = set()

        for doc_id, doc_dict in corpus.items():
            doc_id_set.add(doc_id)
            title = doc_dict.get("title", "")
            text = doc_dict.get("text", "")
            content = f"# {title}\n\n{text}" if title else text

            documents.append({
                "id": doc_id,
                "content": content,
                "title": title,
                "metadata": {"source": f"beir-{dataset_name}"},
            })

        # Build relevance mapping
        query_relevance: Dict[str, List[str]] = {}
        for query_id, doc_scores in qrels.items():
            relevant_docs = [
                doc_id
                for doc_id, score in doc_scores.items()
                if score > 0 and doc_id in doc_id_set
            ]
            if relevant_docs:
                query_relevance[query_id] = relevant_docs

        # Convert queries
        eval_queries = []
        for query_id, query_text in queries.items():
            if query_id not in query_relevance:
                continue

            relevant_docs = query_relevance[query_id]
            num_relevant = len(relevant_docs)
            query_words = len(query_text.split())

            # Determine difficulty
            if num_relevant == 1 and query_words <= 10:
                difficulty = "easy"
            elif num_relevant <= 2 and query_words <= 15:
                difficulty = "medium"
            else:
                difficulty = "hard"

            eval_queries.append({
                "query": query_text,
                "relevant_doc_ids": relevant_docs,
                "difficulty": difficulty,
                "query_type": "factual",
                "metadata": {
                    "source": f"beir-{dataset_name}",
                    "num_relevant": num_relevant,
                },
            })

        return {
            "name": f"BEIR-{dataset_name}",
            "description": f"{dataset_name} dataset from BEIR benchmark",
            "documents": documents,
            "queries": eval_queries,
            "metadata": {
                "source": "beir",
                "dataset": dataset_name,
                "num_documents": len(documents),
                "num_queries": len(eval_queries),
            },
        }


# ============================================================================
# Wikipedia Dataset Handler
# ============================================================================


class WikipediaHandler:
    """Handler for Wikipedia datasets."""

    @staticmethod
    def download(size: int = 1000) -> List[dict]:
        """Download Wikipedia dataset from Hugging Face."""
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError("datasets not installed. Run: pip install datasets")

        logger.info("downloading_wikipedia", size=size)
        print(f"📥 Downloading {size} Wikipedia documents...")

        # Load from Hugging Face
        dataset = load_dataset(
            "wikipedia", "20220301.en", split=f"train[:{size}]", trust_remote_code=True
        )

        documents = []
        for i, item in enumerate(dataset):
            documents.append(
                {
                    "id": f"wiki_{i}",
                    "title": item["title"],
                    "text": item["text"],
                }
            )

        return documents

    @staticmethod
    def convert_to_evaluation_format(
        documents: List[dict], queries_per_doc: int = 2
    ) -> Dict:
        """Convert Wikipedia docs to evaluation dataset with generated queries."""

        logger.info("converting_wikipedia", num_docs=len(documents))
        print(f"🔄 Converting {len(documents)} Wikipedia documents...")

        eval_documents = []
        eval_queries = []

        for doc in documents:
            doc_id = doc["id"]
            title = doc["title"]
            content = doc["text"]

            # Add document
            eval_documents.append({
                "id": doc_id,
                "content": content,
                "title": title,
                "metadata": {"source": "wikipedia"},
            })

            # Generate queries
            queries = WikipediaHandler._generate_queries(
                doc_id, title, content, queries_per_doc
            )
            eval_queries.extend(queries)

        return {
            "name": f"Wikipedia-{len(documents)}",
            "description": f"Wikipedia articles with generated queries",
            "documents": eval_documents,
            "queries": eval_queries,
            "metadata": {
                "source": "wikipedia",
                "num_documents": len(eval_documents),
                "num_queries": len(eval_queries),
                "queries_per_doc": queries_per_doc,
            },
        }

    @staticmethod
    def _generate_queries(
        doc_id: str, title: str, content: str, num_queries: int
    ) -> List[Dict]:
        """Generate queries for a Wikipedia document."""
        queries = []

        # Query 1: Simple factual
        queries.append({
            "query": f"What is {title}?",
            "relevant_doc_ids": [doc_id],
            "difficulty": "easy",
            "query_type": "factual",
            "metadata": {"generated": True},
        })

        if num_queries >= 2:
            # Query 2: Descriptive
            queries.append({
                "query": f"Tell me about {title}",
                "relevant_doc_ids": [doc_id],
                "difficulty": "easy",
                "query_type": "descriptive",
                "metadata": {"generated": True},
            })

        if num_queries >= 3:
            # Query 3: Extract key terms
            words = title.split()
            if len(words) > 1:
                query_text = f"{words[0]} {words[-1]}"
            else:
                query_text = title

            queries.append({
                "query": query_text,
                "relevant_doc_ids": [doc_id],
                "difficulty": "medium",
                "query_type": "keyword",
                "metadata": {"generated": True},
            })

        return queries[:num_queries]


# ============================================================================
# MS MARCO Dataset Handler
# ============================================================================


class MSMARCOHandler:
    """Handler for MS MARCO dataset."""

    @staticmethod
    def download(size: int = 10000) -> List[dict]:
        """Download MS MARCO dataset."""
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError("datasets not installed. Run: pip install datasets")

        logger.info("downloading_msmarco", size=size)
        print(f"📥 Downloading {size} MS MARCO passages...")

        dataset = load_dataset("microsoft/ms_marco", "v1.1", split=f"train[:{size}]")

        documents = []
        for i, item in enumerate(dataset):
            documents.append(
                {
                    "id": f"msmarco_{i}",
                    "text": (
                        item["passages"]["passage_text"][0]
                        if item["passages"]["passage_text"]
                        else ""
                    ),
                    "query": item["query"],
                    "answers": item.get("answers", []),
                }
            )

        return documents

    @staticmethod
    def convert_to_evaluation_format(documents: List[dict]) -> Dict:
        """Convert MS MARCO to evaluation dataset."""

        logger.info("converting_msmarco", num_docs=len(documents))
        print(f"🔄 Converting {len(documents)} MS MARCO passages...")

        eval_documents = []
        eval_queries = []

        # Group by query
        query_docs = {}
        for doc in documents:
            query = doc["query"]
            if query not in query_docs:
                query_docs[query] = []
            query_docs[query].append(doc)

        # Convert
        for query_text, docs in query_docs.items():
            relevant_doc_ids = []

            for doc in docs:
                doc_id = doc["id"]

                # Add document
                eval_documents.append({
                    "id": doc_id,
                    "content": doc["text"],
                    "title": query_text,
                    "metadata": {"source": "msmarco"},
                })

                relevant_doc_ids.append(doc_id)

            # Add query
            answers = docs[0].get("answers", [])
            expected_answer = answers[0] if answers else None

            eval_queries.append({
                "query": query_text,
                "relevant_doc_ids": relevant_doc_ids,
                "expected_answer": expected_answer,
                "difficulty": "medium",
                "query_type": "factual",
                "metadata": {"source": "msmarco"},
            })

        return {
            "name": f"MS-MARCO-{len(documents)}",
            "description": f"MS MARCO passages with queries",
            "documents": eval_documents,
            "queries": eval_queries,
            "metadata": {
                "source": "msmarco",
                "num_documents": len(eval_documents),
                "num_queries": len(eval_queries),
            },
        }


# ============================================================================
# Dataset Verifier
# ============================================================================


class DatasetVerifier:
    """Verify evaluation dataset quality."""

    @staticmethod
    def verify(dataset: Dict) -> Dict:
        """Verify dataset and return statistics."""

        print(f"\n{'='*70}")
        print(f"📊 Verifying Dataset: {dataset.get('name', 'Unknown')}")
        print(f"{'='*70}")

        # Basic stats
        num_docs = len(dataset.get('documents', []))
        num_queries = len(dataset.get('queries', []))

        print(f"\n📄 Documents: {num_docs:,}")
        print(f"❓ Queries: {num_queries:,}")

        if num_docs == 0 or num_queries == 0:
            print("❌ Error: Dataset is empty!")
            return {}

        # Document stats
        doc_lengths = [len(doc.get('content', '')) for doc in dataset['documents']]
        print(f"\n📏 Document Lengths:")
        print(f"   Min: {min(doc_lengths):,} chars")
        print(f"   Max: {max(doc_lengths):,} chars")
        print(f"   Avg: {sum(doc_lengths)/len(doc_lengths):,.0f} chars")

        # Query stats
        difficulties = Counter(q.get('difficulty', 'unknown') for q in dataset['queries'])
        query_types = Counter(q.get('query_type', 'unknown') for q in dataset['queries'])

        print(f"\n🎯 Difficulty Distribution:")
        for diff, count in difficulties.items():
            pct = (count / num_queries) * 100
            print(f"   {diff.capitalize()}: {count} ({pct:.1f}%)")

        print(f"\n📝 Query Types:")
        for qtype, count in query_types.items():
            pct = (count / num_queries) * 100
            print(f"   {qtype.capitalize()}: {count} ({pct:.1f}%)")

        # Relevance stats
        relevant_counts = [len(q.get('relevant_doc_ids', [])) for q in dataset['queries']]
        print(f"\n🔗 Relevant Documents per Query:")
        print(f"   Min: {min(relevant_counts)}")
        print(f"   Max: {max(relevant_counts)}")
        print(f"   Avg: {sum(relevant_counts)/len(relevant_counts):.2f}")

        # Check for expected answers
        queries_with_answer = sum(
            1 for q in dataset['queries']
            if q.get('expected_answer')
        )
        print(f"\n✅ Queries with expected_answer: {queries_with_answer}/{num_queries}")

        print(f"\n{'='*70}")

        return {
            "num_documents": num_docs,
            "num_queries": num_queries,
            "avg_doc_length": sum(doc_lengths) / len(doc_lengths),
            "difficulty_distribution": dict(difficulties),
            "query_types": dict(query_types),
            "avg_relevant_docs": sum(relevant_counts) / len(relevant_counts),
        }


# ============================================================================
# Main CLI
# ============================================================================


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
    parser = argparse.ArgumentParser(
        description="Universal Dataset Preparation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Dataset type")

    # BEIR command
    beir_parser = subparsers.add_parser("beir", help="Download BEIR dataset")
    beir_parser.add_argument(
        "--name", required=True, choices=BEIRHandler.AVAILABLE_DATASETS
    )
    beir_parser.add_argument(
        "--sample", type=int, help="Sample size (for large datasets)"
    )
    beir_parser.add_argument(
        "--output",
        type=Path,
        help="Output path (default: backend/datasets/beir_{name}_eval.json)",
    )
    beir_parser.add_argument(
        "--no-register",
        action='store_true',
        help='Do not register dataset to database automatically'
    )

    # Wikipedia command
    wiki_parser = subparsers.add_parser("wikipedia", help="Download Wikipedia dataset")
    wiki_parser.add_argument(
        "--size", type=int, default=1000, help="Number of documents"
    )
    wiki_parser.add_argument(
        "--queries-per-doc", type=int, default=2, help="Queries per document"
    )
    wiki_parser.add_argument("--output", type=Path, help="Output path")
    wiki_parser.add_argument(
        "--no-register",
        action='store_true',
        help='Do not register dataset to database automatically'
    )

    # MS MARCO command
    msmarco_parser = subparsers.add_parser("msmarco", help="Download MS MARCO dataset")
    msmarco_parser.add_argument(
        "--size", type=int, default=10000, help="Number of passages"
    )
    msmarco_parser.add_argument("--output", type=Path, help="Output path")
    msmarco_parser.add_argument(
        "--no-register",
        action='store_true',
        help='Do not register dataset to database automatically'
    )

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify existing dataset")
    verify_parser.add_argument(
        "--dataset", type=Path, required=True, help="Path to dataset JSON"
    )

    # List command
    subparsers.add_parser("list", help="List available datasets")
    
    # Download all command
    download_all_parser = subparsers.add_parser("download-all", help="Download all BEIR datasets")
    download_all_parser.add_argument(
        "--no-register",
        action='store_true',
        help='Do not register datasets to database automatically'
    )

    args = parser.parse_args()

    # Handle commands
    if args.command == "list":
        print("Available BEIR datasets:")
        for name in BEIRHandler.AVAILABLE_DATASETS:
            print(f"  - {name}")
        return
    
    elif args.command == "download-all":
        print("="*70)
        print("Downloading ALL BEIR Datasets")
        print("="*70)
        print("\n⚠️  This will download all BEIR datasets (may take a while)")
        print("   Datasets: " + ", ".join(BEIRHandler.AVAILABLE_DATASETS))
        print()
        
        for dataset_name in BEIRHandler.AVAILABLE_DATASETS:
            try:
                print(f"\n{'='*70}")
                print(f"Processing: {dataset_name}")
                print(f"{'='*70}")
                
                # Download
                corpus, queries, qrels = BEIRHandler.download(dataset_name, None)
                
                # Convert
                dataset = BEIRHandler.convert_to_evaluation_format(
                    corpus, queries, qrels, dataset_name
                )
                
                # Save
                output_path = Path(f"backend/datasets/beir_{dataset_name}_eval.json")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(dataset, f, indent=2, ensure_ascii=False)
                
                # Verify
                DatasetVerifier.verify(dataset)
                print(f"\n✅ Saved to: {output_path}")
                
                # Register
                if not args.no_register:
                    register_to_db(output_path)
                    
            except Exception as e:
                print(f"❌ Failed to download {dataset_name}: {e}")
                continue
        
        print(f"\n{'='*70}")
        print("✅ All BEIR datasets downloaded!")
        print(f"{'='*70}")

    elif args.command == "beir":
        # Download
        corpus, queries, qrels = BEIRHandler.download(args.name, args.sample)

        # Convert
        dataset = BEIRHandler.convert_to_evaluation_format(
            corpus, queries, qrels, args.name
        )

        # Save
        output_path = args.output or Path(f"backend/datasets/beir_{args.name}_eval.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        # Verify
        DatasetVerifier.verify(dataset)
        print(f"\n✅ Saved to: {output_path}")
        
        # Register
        if not args.no_register:
            register_to_db(output_path)

    elif args.command == "wikipedia":
        # Download
        documents = WikipediaHandler.download(args.size)

        # Convert
        dataset = WikipediaHandler.convert_to_evaluation_format(
            documents, args.queries_per_doc
        )

        # Save
        output_path = args.output or Path(f"backend/datasets/wikipedia_{args.size}_eval.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        # Verify
        DatasetVerifier.verify(dataset)
        print(f"\n✅ Saved to: {output_path}")
        
        # Register
        if not args.no_register:
            register_to_db(output_path)

    elif args.command == "msmarco":
        # Download
        documents = MSMARCOHandler.download(args.size)

        # Convert
        dataset = MSMARCOHandler.convert_to_evaluation_format(documents)

        # Save
        output_path = args.output or Path(f"backend/datasets/msmarco_{args.size}_eval.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        # Verify
        DatasetVerifier.verify(dataset)
        print(f"\n✅ Saved to: {output_path}")
        
        # Register
        if not args.no_register:
            register_to_db(output_path)

    elif args.command == "verify":
        # Load and verify
        with open(args.dataset, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        DatasetVerifier.verify(dataset)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

