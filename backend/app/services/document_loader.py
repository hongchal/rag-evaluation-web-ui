"""Document Loader for various file types (txt, pdf, json)."""

import json
import hashlib
from pathlib import Path
from typing import List, Optional
import structlog

from app.models.base_document import BaseDocument

logger = structlog.get_logger(__name__)


class DocumentLoader:
    """
    Load documents from various file types.
    
    Supported formats:
    - TXT: Plain text files
    - PDF: PDF documents (using PyPDF2 or pdfplumber)
    - JSON: JSON files with text content
    """
    
    @staticmethod
    def load_txt(file_path: str, datasource_id: Optional[int] = None) -> BaseDocument:
        """
        Load a text file.
        
        Args:
            file_path: Path to the text file
            datasource_id: Optional datasource ID
            
        Returns:
            BaseDocument with text content
        """
        path = Path(file_path)
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Generate document ID from content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        doc_id = f"txt_{content_hash}"
        
        return BaseDocument(
            id=doc_id,
            content=content,
            source_type="file",
            source_uri=str(path.absolute()),
            metadata={
                "filename": path.name,
                "file_type": "txt",
                "file_size": path.stat().st_size,
                "datasource_id": datasource_id,
            }
        )
    
    @staticmethod
    def load_pdf(file_path: str, datasource_id: Optional[int] = None) -> BaseDocument:
        """
        Load a PDF file.
        
        Args:
            file_path: Path to the PDF file
            datasource_id: Optional datasource ID
            
        Returns:
            BaseDocument with extracted text
        """
        path = Path(file_path)
        
        try:
            # Try pdfplumber first (better quality)
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"[Page {page_num}]\n{page_text}")
            
            content = "\n\n".join(text_parts)
            
        except ImportError:
            # Fallback to PyPDF2
            logger.warning("pdfplumber_not_available_using_pypdf2")
            from PyPDF2 import PdfReader
            
            reader = PdfReader(path)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num}]\n{page_text}")
            
            content = "\n\n".join(text_parts)
        
        # Generate document ID
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        doc_id = f"pdf_{content_hash}"
        
        return BaseDocument(
            id=doc_id,
            content=content,
            source_type="file",
            source_uri=str(path.absolute()),
            metadata={
                "filename": path.name,
                "file_type": "pdf",
                "file_size": path.stat().st_size,
                "num_pages": len(text_parts),
                "datasource_id": datasource_id,
            }
        )
    
    @staticmethod
    def load_json(file_path: str, content_field: str = "content", datasource_id: Optional[int] = None) -> List[BaseDocument]:
        """
        Load a JSON file.
        
        Args:
            file_path: Path to the JSON file
            content_field: Field name containing the text content
            datasource_id: Optional datasource ID
            
        Returns:
            List of BaseDocument (supports both single object and array)
        """
        path = Path(file_path)
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        documents = []
        
        # Handle both single object and array
        if isinstance(data, list):
            items = data
        else:
            items = [data]
        
        for idx, item in enumerate(items):
            # Extract content
            if isinstance(item, dict):
                content = item.get(content_field, "")
                if not content:
                    # Try alternative fields
                    content = item.get("text", item.get("body", str(item)))
                
                # Use other fields as metadata
                metadata = {k: v for k, v in item.items() if k != content_field}
            else:
                content = str(item)
                metadata = {}
            
            # Generate document ID
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            doc_id = f"json_{content_hash}_{idx}"
            
            metadata.update({
                "filename": path.name,
                "file_type": "json",
                "file_size": path.stat().st_size,
                "item_index": idx,
                "datasource_id": datasource_id,
            })
            
            documents.append(BaseDocument(
                id=doc_id,
                content=content,
                source_type="file",
                source_uri=str(path.absolute()),
                metadata=metadata
            ))
        
        return documents
    
    @classmethod
    def load_file(cls, file_path: str, datasource_id: Optional[int] = None, **kwargs) -> List[BaseDocument]:
        """
        Auto-detect file type and load accordingly.
        
        Args:
            file_path: Path to the file
            datasource_id: Optional datasource ID
            **kwargs: Additional arguments for specific loaders
            
        Returns:
            List of BaseDocument
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        logger.info("loading_file", path=str(path), file_type=suffix)
        
        try:
            if suffix == ".txt":
                return [cls.load_txt(file_path, datasource_id)]
            elif suffix == ".pdf":
                return [cls.load_pdf(file_path, datasource_id)]
            elif suffix == ".json":
                return cls.load_json(file_path, datasource_id=datasource_id, **kwargs)
            else:
                # Try to load as text
                logger.warning("unknown_file_type_trying_as_text", suffix=suffix)
                return [cls.load_txt(file_path, datasource_id)]
                
        except Exception as e:
            logger.error("file_load_failed", path=str(path), error=str(e))
            raise ValueError(f"Failed to load file {path}: {e}")

