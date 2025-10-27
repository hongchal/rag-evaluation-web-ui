"""Docling-based document processor for advanced PDF understanding."""

from pathlib import Path
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class DoclingProcessor:
    """
    Advanced document processor using Docling.
    
    Features:
    - Layout understanding (headers, paragraphs, tables, etc.)
    - Reading order detection
    - Table structure preservation
    - Code block recognition
    - Formula extraction
    - Image classification
    """
    
    def __init__(self):
        """Initialize Docling converter with smart OCR."""
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.datamodel.base_models import InputFormat
            
            # Store converter classes for dynamic initialization
            self.DocumentConverter = DocumentConverter
            self.PdfFormatOption = PdfFormatOption
            self.PdfPipelineOptions = PdfPipelineOptions
            self.InputFormat = InputFormat
            
            # Create default converter (text-based, no OCR - faster)
            self.converter = DocumentConverter()
            
            self._available = True
            logger.info("docling_initialized", smart_ocr=True)
        except ImportError as e:
            self._available = False
            logger.warning("docling_not_available", error=str(e))
    
    def _get_converter_for_pdf_type(self, pdf_type: str):
        """
        Get appropriate converter based on PDF type.
        
        Args:
            pdf_type: "text" or "image"
            
        Returns:
            DocumentConverter instance
        """
        if pdf_type == "text":
            # Fast converter without OCR for text-based PDFs
            return self.DocumentConverter()
        else:
            # OCR-enabled converter for image-based PDFs with Korean support
            from docling.datamodel.pipeline_options import (
                EasyOcrOptions,
                TesseractCliOcrOptions,
                TesseractOcrOptions
            )
            
            pipeline_options = self.PdfPipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.do_table_structure = True
            pipeline_options.images_scale = 3.0  # Higher resolution for better OCR
            pipeline_options.generate_page_images = True
            pipeline_options.generate_picture_images = False
            
            # Try to configure OCR with Korean language support
            try:
                # Prefer EasyOCR for better multilingual support
                ocr_options = EasyOcrOptions(
                    lang=["ko", "en"],  # Korean + English
                    force_full_page_ocr=True  # Force OCR on all pages
                )
                pipeline_options.ocr_options = ocr_options
                logger.info("ocr_configured", engine="easyocr", languages=["ko", "en"])
            except Exception as e:
                # Fallback: try Tesseract
                logger.warning("easyocr_config_failed", error=str(e))
                try:
                    ocr_options = TesseractOcrOptions(
                        lang="kor+eng",  # Korean + English for Tesseract
                        force_full_page_ocr=True
                    )
                    pipeline_options.ocr_options = ocr_options
                    logger.info("ocr_configured", engine="tesseract", languages=["kor", "eng"])
                except Exception as e2:
                    logger.warning("tesseract_config_failed", error=str(e2))
                    logger.info("using_default_ocr")
            
            converter = self.DocumentConverter(
                format_options={
                    self.InputFormat.PDF: self.PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
            logger.info("ocr_converter_created", pdf_type="image")
            return converter
    
    @property
    def is_available(self) -> bool:
        """Check if Docling is available."""
        return self._available
    
    def _detect_pdf_type(self, file_path: Path) -> str:
        """
        Detect if PDF is text-based or image-based.
        
        Returns:
            "text" if PDF has text layer, "image" if scanned/image-based
        """
        try:
            import pdfplumber
            
            # Check first 3 pages for text content
            with pdfplumber.open(file_path) as pdf:
                total_text_length = 0
                pages_to_check = min(3, len(pdf.pages))
                
                for i in range(pages_to_check):
                    text = pdf.pages[i].extract_text()
                    if text:
                        total_text_length += len(text.strip())
                
                # If we have more than 100 chars in first 3 pages, it's text-based
                if total_text_length > 100:
                    logger.info("pdf_type_detected", type="text", text_length=total_text_length)
                    return "text"
                else:
                    logger.info("pdf_type_detected", type="image", text_length=total_text_length)
                    return "image"
        except Exception as e:
            logger.warning("pdf_type_detection_failed", error=str(e))
            # Default to text-based processing if detection fails
            return "text"
    
    def extract_from_pdf(
        self, 
        file_path: Path,
        export_format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Extract content from PDF using Docling with smart OCR detection.
        
        Automatically detects if PDF is text-based or image-based:
        - Text-based: Fast processing without OCR
        - Image-based: Enables OCR for scanned documents
        
        Args:
            file_path: Path to PDF file
            export_format: Output format (markdown, html, doctags, json)
            
        Returns:
            Dictionary containing:
            - content: Extracted content in specified format
            - metadata: Document metadata (pages, tables, images, etc.)
            
        Raises:
            ValueError: If Docling is not available or extraction fails
        """
        if not self.is_available:
            raise ValueError(
                "Docling is not available. Install with: pip install docling"
            )
        
        # Detect PDF type
        pdf_type = self._detect_pdf_type(file_path)
        
        # Get appropriate converter for PDF type
        converter = self._get_converter_for_pdf_type(pdf_type)
        
        logger.info(
            "extracting_with_docling",
            file=str(file_path),
            format=export_format,
            pdf_type=pdf_type,
            ocr_enabled=(pdf_type == "image")
        )
        
        try:
            # Convert document with appropriate converter
            result = converter.convert(str(file_path))
            
            # Export to desired format
            if export_format == "markdown":
                content = result.document.export_to_markdown()
            elif export_format == "html":
                content = result.document.export_to_html()
            elif export_format == "doctags":
                content = result.document.export_to_doctags()
            elif export_format == "json":
                content = result.document.export_to_dict()
            else:
                # Default to markdown
                content = result.document.export_to_markdown()
            
            # Extract metadata
            doc = result.document
            
            # Count elements safely
            num_tables = 0
            num_images = 0
            num_code_blocks = 0
            
            if hasattr(doc, 'body') and doc.body:
                try:
                    for item in doc.body:
                        # Handle different item formats (object vs tuple)
                        if hasattr(item, 'type'):
                            item_type = item.type
                        elif isinstance(item, tuple) and len(item) > 0:
                            item_type = item[0] if isinstance(item[0], str) else None
                        else:
                            item_type = None
                        
                        if item_type == "table":
                            num_tables += 1
                        elif item_type == "picture":
                            num_images += 1
                        elif item_type == "code":
                            num_code_blocks += 1
                except Exception as e:
                    logger.warning("failed_to_count_elements", error=str(e))
            
            # Get num_pages - handle both property and method
            num_pages_attr = getattr(doc, 'num_pages', None)
            if callable(num_pages_attr):
                num_pages = num_pages_attr()
            elif num_pages_attr is not None:
                num_pages = num_pages_attr
            else:
                num_pages = len(getattr(doc, 'pages', []))
            
            metadata = {
                "processor": "docling",
                "export_format": export_format,
                "pdf_type": pdf_type,  # "text" or "image"
                "ocr_used": (pdf_type == "image"),  # True if OCR was used
                "num_pages": num_pages,
                "num_tables": num_tables,
                "num_images": num_images,
                "num_code_blocks": num_code_blocks,
                "has_layout_info": hasattr(doc, 'layout'),
                "content_length": len(str(content)),
            }
            
            logger.info(
                "docling_extraction_complete",
                metadata=metadata
            )
            
            return {
                "content": content,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(
                "docling_extraction_failed",
                error=str(e),
                file=str(file_path)
            )
            raise ValueError(f"Docling extraction failed: {e}")
    
    def extract_from_docx(self, file_path: Path) -> Dict[str, Any]:
        """Extract content from DOCX file."""
        if not self.is_available:
            raise ValueError("Docling is not available")
        
        try:
            result = self.converter.convert(str(file_path))
            content = result.document.export_to_markdown()
            
            metadata = {
                "processor": "docling",
                "file_type": "docx",
                "content_length": len(content),
            }
            
            return {
                "content": content,
                "metadata": metadata
            }
        except Exception as e:
            logger.error("docling_docx_failed", error=str(e))
            raise ValueError(f"DOCX extraction failed: {e}")
    
    def extract_from_pptx(self, file_path: Path) -> Dict[str, Any]:
        """Extract content from PPTX file."""
        if not self.is_available:
            raise ValueError("Docling is not available")
        
        try:
            result = self.converter.convert(str(file_path))
            content = result.document.export_to_markdown()
            
            metadata = {
                "processor": "docling",
                "file_type": "pptx",
                "content_length": len(content),
            }
            
            return {
                "content": content,
                "metadata": metadata
            }
        except Exception as e:
            logger.error("docling_pptx_failed", error=str(e))
            raise ValueError(f"PPTX extraction failed: {e}")
    
    def extract_from_image(self, file_path: Path) -> Dict[str, Any]:
        """Extract content from image file (PNG, JPEG, TIFF, etc.)."""
        if not self.is_available:
            raise ValueError("Docling is not available")
        
        try:
            result = self.converter.convert(str(file_path))
            content = result.document.export_to_markdown()
            
            metadata = {
                "processor": "docling",
                "file_type": "image",
                "content_length": len(content),
            }
            
            return {
                "content": content,
                "metadata": metadata
            }
        except Exception as e:
            logger.error("docling_image_failed", error=str(e))
            raise ValueError(f"Image extraction failed: {e}")

