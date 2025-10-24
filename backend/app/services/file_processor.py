"""File processing service for PDF and TXT files."""

import hashlib
from pathlib import Path
from typing import Optional

import aiofiles
import PyPDF2
import structlog

logger = structlog.get_logger(__name__)


class FileProcessor:
    """Service for processing uploaded files."""

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    async def save_file(file_content: bytes, filename: str, upload_dir: Path) -> Path:
        """Save file to upload directory."""
        file_path = upload_dir / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        return file_path

    @staticmethod
    def extract_text_from_pdf(file_path: Path) -> tuple[str, int]:
        """
        Extract text from PDF file.

        Returns:
            Tuple of (extracted_text, num_pages)
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

                return "\n\n".join(text_parts), num_pages
        except Exception as e:
            logger.error("pdf_extraction_failed", error=str(e), file=str(file_path))
            raise ValueError(f"Failed to extract text from PDF: {e}")

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
        logger.info("processing_file", filename=filename, file_type=file_type)

        # Compute hash
        content_hash = self.compute_hash(file_content)

        # Save file
        file_path = await self.save_file(file_content, filename, upload_dir)

        # Extract content based on file type
        content: Optional[str] = None
        num_pages: Optional[int] = None

        if file_type == "pdf":
            content, num_pages = self.extract_text_from_pdf(file_path)
        elif file_type == "txt":
            content = await self.extract_text_from_txt(file_path)
            num_pages = None
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        logger.info(
            "file_processed",
            filename=filename,
            content_length=len(content) if content else 0,
            num_pages=num_pages,
        )

        return {
            "file_path": str(file_path),
            "content": content,
            "content_hash": content_hash,
            "num_pages": num_pages,
            "file_size": len(file_content),
        }
