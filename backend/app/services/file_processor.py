"""File processing service for PDF and TXT files."""

import hashlib
from pathlib import Path
from typing import Optional, Literal
from enum import Enum

import aiofiles
import PyPDF2
import structlog

logger = structlog.get_logger(__name__)


class ProcessorType(str, Enum):
    """Available document processor types."""
    PYPDF2 = "pypdf2"
    PDFPLUMBER = "pdfplumber"
    DOCLING = "docling"


class FileProcessor:
    """
    Service for processing uploaded files.
    
    Supports multiple processing backends:
    - pypdf2: Fast, basic text extraction
    - pdfplumber: Better quality, table-aware
    - docling: Advanced layout understanding, structure preservation
    """
    
    def __init__(self, processor_type: ProcessorType = ProcessorType.PDFPLUMBER):
        """
        Initialize file processor.
        
        Args:
            processor_type: Type of processor to use for PDFs
        """
        self.processor_type = processor_type
        self._docling_processor = None
        
        logger.info("file_processor_initialized", processor_type=processor_type)

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    @property
    def docling_processor(self):
        """Lazy load Docling processor."""
        if self._docling_processor is None:
            from app.services.docling_processor import DoclingProcessor
            self._docling_processor = DoclingProcessor()
        return self._docling_processor
    
    @staticmethod
    async def save_file(file_content: bytes, filename: str, upload_dir: Path) -> Path:
        """Save file to upload directory."""
        file_path = upload_dir / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        return file_path
    
    def extract_text_from_pdf_pypdf2(self, file_path: Path) -> tuple[str, int, dict]:
        """
        Extract text from PDF using PyPDF2 (fast, basic).

        Returns:
            Tuple of (extracted_text, num_pages, metadata)
        """
        try:
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                num_pages = len(pdf_reader.pages)

                text_parts = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

                content = "\n\n".join(text_parts)
                metadata = {
                    "processor": "pypdf2",
                    "num_pages": num_pages,
                    "content_length": len(content)
                }
                
                return content, num_pages, metadata
        except Exception as e:
            logger.error("pypdf2_extraction_failed", error=str(e), file=str(file_path))
            raise ValueError(f"PyPDF2 extraction failed: {e}")
    
    def extract_text_from_pdf_pdfplumber(self, file_path: Path) -> tuple[str, int, dict]:
        """
        Extract text from PDF using pdfplumber (better quality).

        Returns:
            Tuple of (extracted_text, num_pages, metadata)
        """
        try:
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                num_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"[Page {page_num}]\n{page_text}")
            
            content = "\n\n".join(text_parts)
            metadata = {
                "processor": "pdfplumber",
                "num_pages": num_pages,
                "content_length": len(content)
            }
            
            return content, num_pages, metadata
            
        except ImportError:
            logger.warning("pdfplumber_not_available_fallback_to_pypdf2")
            return self.extract_text_from_pdf_pypdf2(file_path)
        except Exception as e:
            logger.error("pdfplumber_extraction_failed", error=str(e), file=str(file_path))
            raise ValueError(f"pdfplumber extraction failed: {e}")
    
    def extract_text_from_pdf_docling(self, file_path: Path) -> tuple[str, int, dict]:
        """
        Extract text from PDF using Docling (advanced layout understanding).

        Returns:
            Tuple of (extracted_text, num_pages, metadata)
        """
        try:
            result = self.docling_processor.extract_from_pdf(file_path, export_format="markdown")
            
            content = result["content"]
            metadata = result["metadata"]
            num_pages = metadata.get("num_pages", 0)
            
            return content, num_pages, metadata
            
        except Exception as e:
            logger.error("docling_extraction_failed", error=str(e), file=str(file_path))
            logger.warning("falling_back_to_pdfplumber")
            return self.extract_text_from_pdf_pdfplumber(file_path)
    
    def extract_text_from_pdf(self, file_path: Path) -> tuple[str, int, dict]:
        """
        Extract text from PDF file using configured processor.

        Returns:
            Tuple of (extracted_text, num_pages, metadata)
        """
        logger.info(
            "extracting_pdf",
            processor=self.processor_type,
            file=str(file_path)
        )
        
        if self.processor_type == ProcessorType.PYPDF2:
            return self.extract_text_from_pdf_pypdf2(file_path)
        elif self.processor_type == ProcessorType.PDFPLUMBER:
            return self.extract_text_from_pdf_pdfplumber(file_path)
        elif self.processor_type == ProcessorType.DOCLING:
            return self.extract_text_from_pdf_docling(file_path)
        else:
            # Default to pdfplumber
            logger.warning(
                "unknown_processor_type_using_default",
                processor=self.processor_type
            )
            return self.extract_text_from_pdf_pdfplumber(file_path)

    @staticmethod
    async def extract_text_from_txt(file_path: Path) -> str:
        """Extract text from TXT file."""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                return await f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            async with aiofiles.open(file_path, "r", encoding="latin-1") as f:
                return await f.read()
        except Exception as e:
            logger.error("txt_extraction_failed", error=str(e), file=str(file_path))
            raise ValueError(f"Failed to extract text from TXT: {e}")

    async def process_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: str,
        upload_dir: Path,
    ) -> dict:
        """
        Process uploaded file and extract content.

        Returns:
            Dictionary with file metadata and extracted content
        """
        logger.info(
            "processing_file",
            filename=filename,
            file_type=file_type,
            processor=self.processor_type
        )

        # Compute hash
        content_hash = self.compute_hash(file_content)

        # Save file
        file_path = await self.save_file(file_content, filename, upload_dir)

        # Extract content based on file type
        content: Optional[str] = None
        num_pages: Optional[int] = None
        extraction_metadata: dict = {}

        if file_type == "pdf":
            content, num_pages, extraction_metadata = self.extract_text_from_pdf(file_path)
        elif file_type == "txt":
            content = await self.extract_text_from_txt(file_path)
            num_pages = None
            extraction_metadata = {
                "processor": "text",
                "content_length": len(content) if content else 0
            }
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        logger.info(
            "file_processed",
            filename=filename,
            content_length=len(content) if content else 0,
            num_pages=num_pages,
            processor=self.processor_type,
        )

        return {
            "file_path": str(file_path),
            "content": content,
            "content_hash": content_hash,
            "num_pages": num_pages,
            "file_size": len(file_content),
            "processor_type": self.processor_type.value,
            "extraction_metadata": extraction_metadata,
        }
