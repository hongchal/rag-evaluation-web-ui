"""Claude Generator for answer generation."""

from typing import Dict, List

import structlog
from anthropic import Anthropic
from app.config import settings
from app.models.query import Source

logger = structlog.get_logger(__name__)


class ClaudeGenerator:
    """
    Claude Sonnet 4 Generator for RAG answer generation.

    Features:
    - Contextual answer generation
    - Source-based responses
    - Configurable temperature
    - Document-centric context building
    """

    def __init__(self):
        """Initialize Claude client."""
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model
        self.max_tokens = settings.llm_max_tokens
        self.temperature = settings.llm_temperature

        logger.info(
            "claude_generator_initialized",
            model=self.model,
            max_tokens=self.max_tokens
        )

    def _build_context_from_sources(self, sources: List[Source]) -> tuple[str, List[Source]]:
        """
        Build context string from sources (backup style: document-centric).

        Groups chunks by document to preserve continuity (tables, lists, etc.)
        and orders by position for natural flow.

        Args:
            sources: List of Source objects

        Returns:
            Tuple of (formatted context string, list of representative sources per document group)
        """
        if not sources:
            return "No relevant sources found.", []

        # Group chunks by document to preserve table/list continuity
        docs: Dict[str, List[Source]] = {}
        for src in sources:
            docs.setdefault(src.document_id, []).append(src)

        # Stable order by first appearance in sources
        ordered_doc_ids = []
        seen = set()
        for src in sources:
            if src.document_id not in seen:
                ordered_doc_ids.append(src.document_id)
                seen.add(src.document_id)

        context_parts: List[str] = []
        grouped_sources: List[Source] = []  # Representative source for each document group

        for idx, doc_id in enumerate(ordered_doc_ids, start=1):
            doc_chunks = docs.get(doc_id, [])
            # Order by position if available so that tables read in sequence
            doc_chunks.sort(key=lambda s: (s.position or 0))
            joined = "\n".join(c.content or c.content_snippet for c in doc_chunks)
            title = doc_chunks[0].title if doc_chunks else "Untitled"
            url = doc_chunks[0].url if doc_chunks else ""
            context_parts.append(
                f"[{idx}] {title}\nURL: {url}\nContent:\n{joined}\n"
            )
            # Use first chunk as representative with aggregated content
            representative = doc_chunks[0]
            grouped_sources.append(Source(
                chunk_id=representative.chunk_id,
                document_id=representative.document_id,
                datasource_id=representative.datasource_id,
                title=title,
                url=url,
                path=representative.path,
                relevance_score=max(c.relevance_score for c in doc_chunks if c.relevance_score),
                content_snippet=joined[:500] + "..." if len(joined) > 500 else joined,  # Aggregated snippet
                content=joined,
                position=representative.position
            ))

        return "\n\n".join(context_parts), grouped_sources

    def generate(
        self,
        question: str,
        context: str = None,
        sources: List[Source] = None
    ) -> tuple[str, List[Source]]:
        """
        Generate answer from question and sources.

        Args:
            question: User question
            context: (Deprecated) Pre-built context string
            sources: List[Source] references (preferred)

        Returns:
            Tuple of (generated answer string, list of grouped sources)
        """
        logger.info("generating_answer", question_length=len(question), source_count=len(sources) if sources else 0)

        grouped_sources: List[Source] = []
        try:
            # Build context from sources (backup style)
            if sources:
                context, grouped_sources = self._build_context_from_sources(sources)
            elif not context:
                raise ValueError("Either context or sources must be provided")

            # System prompt (backup style)
            system_prompt = (
                "You are a helpful AI assistant. "
                "Use the provided sources to answer the user's question. "
                "Cite sources using [1], [2], etc. notation. "
                "If the sources don't contain relevant information, say so."
            )

            # Build user message (backup style)
            user_message = f"""Context from relevant sources:

{context}

---

User Question: {question}

Please provide a comprehensive answer based on the sources above. Cite sources using [1], [2], etc."""

            # Call Claude API with system prompt
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            answer = response.content[0].text

            logger.info(
                "answer_generated",
                answer_length=len(answer),
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                grouped_source_count=len(grouped_sources)
            )

            return answer, grouped_sources

        except Exception as e:
            logger.error("generation_failed", error=str(e))
            raise

    def generate_stream(
        self,
        question: str,
        context: str = None,
        sources: List[Source] = None
    ):
        """
        Generate answer with streaming (yields text chunks as they're generated).

        Args:
            question: User question
            context: (Deprecated) Pre-built context string
            sources: List[Source] references (preferred)

        Yields:
            Text chunks from Claude API
        """
        logger.info("generating_answer_stream", question_length=len(question), source_count=len(sources) if sources else 0)

        try:
            # Build context from sources (backup style)
            if sources:
                context, grouped_sources = self._build_context_from_sources(sources)
            elif not context:
                raise ValueError("Either context or sources must be provided")

            # System prompt (backup style)
            system_prompt = (
                "You are a helpful AI assistant. "
                "Use the provided sources to answer the user's question. "
                "Cite sources using [1], [2], etc. notation. "
                "If the sources don't contain relevant information, say so."
            )

            # Build user message (backup style)
            user_message = f"""Context from relevant sources:

{context}

---

User Question: {question}

Please provide a comprehensive answer based on the sources above. Cite sources using [1], [2], etc."""

            # Stream response from Claude API
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            ) as stream:
                for text in stream.text_stream:
                    yield text

            logger.info("answer_stream_completed")

        except Exception as e:
            logger.error("generation_stream_failed", error=str(e))
            raise

