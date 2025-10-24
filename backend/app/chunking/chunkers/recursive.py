"""Recursive Character Text Chunker for general documents."""

from typing import List
import structlog
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.chunking.chunkers.base_chunker import BaseChunker
from app.models.base_chunk import BaseChunk
from app.models.base_document import BaseDocument

logger = structlog.get_logger(__name__)


class RecursiveChunker(BaseChunker):
    """
    Recursive Character Text Splitter for chunking documents.
    
    Features:
    - Token-based splitting
    - Configurable overlap
    - Markdown-aware separators
    - Supports txt, pdf, json files
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            separators: Custom separators (default: markdown-aware)
        """
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        # Initialize tiktoken encoder
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning("tiktoken_init_failed", error=str(e))
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Token-based length function
        def token_length(text: str) -> int:
            return len(self.tokenizer.encode(text))
        
        # Default markdown-aware separators
        if separators is None:
            separators = [
                "\n\n## ",  # H2 headers
                "\n\n### ",  # H3 headers
                "\n\n",  # Paragraphs
                "\n",  # Lines
                ". ",  # Sentences
                " ",  # Words
                ""  # Characters
            ]
        
        self.separators = separators
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=token_length,
            separators=separators
        )
        
        logger.info(
            "recursive_chunker_initialized",
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
            num_separators=len(separators)
        )
    
    def chunk_document(self, document: BaseDocument) -> List[BaseChunk]:
        """
        Chunk document into smaller pieces.
        
        Args:
            document: Document to chunk
            
        Returns:
            List of BaseChunk
        """
        logger.info(
            "chunking_document",
            document_id=document.id,
            content_length=len(document.content),
            source_type=document.source_type
        )
        
        # Split text
        texts = self.splitter.split_text(document.content)
        
        # Create chunks with position tracking
        chunks = []
        current_pos = 0
        
        for i, text in enumerate(texts):
            # Find start position in original content
            start_char = document.content.find(text, current_pos)
            if start_char == -1:
                start_char = current_pos
            end_char = start_char + len(text)
            current_pos = end_char
            
            # Count tokens
            num_tokens = len(self.tokenizer.encode(text))
            
            # Create chunk (ID will be auto-generated)
            chunk = BaseChunk(
                document_id=document.id,
                content=text,
                chunk_index=i,
                start_char=start_char,
                end_char=end_char,
                metadata={
                    "chunk_method": "recursive",
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "num_tokens": num_tokens,
                    "source_type": document.source_type,
                    "filename": document.filename,
                    "file_type": document.file_type,
                }
            )
            chunks.append(chunk)
        
        logger.info(
            "document_chunked",
            document_id=document.id,
            num_chunks=len(chunks),
            avg_chunk_size=sum(len(c.content) for c in chunks) / len(chunks) if chunks else 0
        )
        
        return chunks
