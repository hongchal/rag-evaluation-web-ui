"""Dataset management for evaluation."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, List, Dict


@dataclass
class EvaluationQuery:
    """A single evaluation query with ground truth."""

    query: str
    relevant_doc_ids: List[str]  # IDs of documents that should be retrieved
    expected_answer: Optional[str] = None  # Optional ground truth answer
    context: Optional[str] = None  # Optional: specific context this query relates to
    difficulty: str = "medium"  # easy, medium, hard
    query_type: str = "factual"  # factual, analytical, comparison, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationDocument:
    """A document to be indexed for evaluation."""

    doc_id: str
    content: str
    title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationDataset:
    """Complete evaluation dataset."""

    name: str
    documents: List[EvaluationDocument]
    queries: List[EvaluationQuery]
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        """Save dataset to JSON file."""
        data = {
            "name": self.name,
            "description": self.description,
            "documents": [
                {
                    "doc_id": doc.doc_id,
                    "content": doc.content,
                    "title": doc.title,
                    "metadata": doc.metadata,
                }
                for doc in self.documents
            ],
            "queries": [
                {
                    "query": q.query,
                    "relevant_doc_ids": q.relevant_doc_ids,
                    "expected_answer": q.expected_answer,
                    "context": q.context,
                    "difficulty": q.difficulty,
                    "query_type": q.query_type,
                    "metadata": q.metadata,
                }
                for q in self.queries
            ],
            "metadata": self.metadata,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> "EvaluationDataset":
        """Load dataset from JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        documents = [
            EvaluationDocument(
                doc_id=doc["doc_id"],
                content=doc["content"],
                title=doc.get("title"),
                metadata=doc.get("metadata", {}),
            )
            for doc in data["documents"]
        ]

        queries = [
            EvaluationQuery(
                query=q["query"],
                relevant_doc_ids=q["relevant_doc_ids"],
                expected_answer=q.get("expected_answer"),
                context=q.get("context"),
                difficulty=q.get("difficulty", "medium"),
                query_type=q.get("query_type", "factual"),
                metadata=q.get("metadata", {}),
            )
            for q in data["queries"]
        ]

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            documents=documents,
            queries=queries,
            metadata=data.get("metadata", {}),
        )

    def get_queries_by_type(self, query_type: str) -> List[EvaluationQuery]:
        """Get all queries of a specific type."""
        return [q for q in self.queries if q.query_type == query_type]

    def get_queries_by_difficulty(self, difficulty: str) -> List[EvaluationQuery]:
        """Get all queries of a specific difficulty."""
        return [q for q in self.queries if q.difficulty == difficulty]

    def get_document_by_id(self, doc_id: str) -> Optional[EvaluationDocument]:
        """Get document by ID."""
        for doc in self.documents:
            if doc.doc_id == doc_id:
                return doc
        return None

    def validate(self) -> List[str]:
        """
        Validate dataset consistency.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check for duplicate document IDs
        doc_ids = [doc.doc_id for doc in self.documents]
        if len(doc_ids) != len(set(doc_ids)):
            errors.append("Duplicate document IDs found")

        # Check that all referenced doc_ids exist
        for query in self.queries:
            for doc_id in query.relevant_doc_ids:
                if not self.get_document_by_id(doc_id):
                    errors.append(
                        f"Query '{query.query}' references non-existent doc_id: {doc_id}"
                    )

        # Check that each query has at least one relevant document
        for query in self.queries:
            if not query.relevant_doc_ids:
                errors.append(f"Query '{query.query}' has no relevant documents")

        return errors

    def __len__(self) -> int:
        """Get number of queries in dataset."""
        return len(self.queries)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"EvaluationDataset(name='{self.name}', "
            f"documents={len(self.documents)}, queries={len(self.queries)})"
        )


class DatasetBuilder:
    """Helper class for building evaluation datasets."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.documents: List[EvaluationDocument] = []
        self.queries: List[EvaluationQuery] = []

    def add_document(
        self,
        doc_id: str,
        content: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "DatasetBuilder":
        """Add a document to the dataset."""
        self.documents.append(
            EvaluationDocument(
                doc_id=doc_id,
                content=content,
                title=title,
                metadata=metadata or {},
            )
        )
        return self

    def add_query(
        self,
        query: str,
        relevant_doc_ids: List[str],
        expected_answer: Optional[str] = None,
        difficulty: str = "medium",
        query_type: str = "factual",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "DatasetBuilder":
        """Add a query to the dataset."""
        self.queries.append(
            EvaluationQuery(
                query=query,
                relevant_doc_ids=relevant_doc_ids,
                expected_answer=expected_answer,
                difficulty=difficulty,
                query_type=query_type,
                metadata=metadata or {},
            )
        )
        return self

    def build(self) -> EvaluationDataset:
        """Build the final dataset."""
        dataset = EvaluationDataset(
            name=self.name,
            description=self.description,
            documents=self.documents,
            queries=self.queries,
        )

        # Validate before returning
        errors = dataset.validate()
        if errors:
            raise ValueError(f"Dataset validation failed:\n" + "\n".join(errors))

        return dataset
