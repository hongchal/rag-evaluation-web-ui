"""DataSource API endpoints."""

import json
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import structlog

from app.core.dependencies import get_db
from app.core.config import settings
from app.models.datasource import DataSource, SourceType, SourceStatus, ProcessorType
from app.models.document import Document
from app.services.file_processor import FileProcessor, ProcessorType as FileProcessorType
from app.services.document_loader import DocumentLoader
from app.schemas.datasource import DataSourceResponse, DataSourceListResponse, ProcessorTypeOption

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/datasources", tags=["datasources"])


@router.post("/upload", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_datasource(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    processor_type: Optional[ProcessorTypeOption] = Form("pdfplumber"),
    db: Session = Depends(get_db),
):
    """
    Upload a file as a data source.
    
    Args:
        file: File to upload (PDF, TXT, JSON)
        name: Optional custom name for the datasource (defaults to filename)
        description: Optional description
        processor_type: PDF processing method (pypdf2, pdfplumber, docling)
        db: Database session
        
    Returns:
        DataSourceResponse with processing metadata
    """
    # Validate file type
    allowed_extensions = {".txt", ".pdf", ".json"}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Compute hash
        content_hash = FileProcessor.compute_hash(content)
        
        # Map processor type
        processor_enum = ProcessorType(processor_type)
        
        # Check for duplicates (same file + same processor)
        existing = (
            db.query(DataSource)
            .filter(
                DataSource.content_hash == content_hash,
                DataSource.processor_type == processor_enum
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File with this processor already exists: {existing.name} (processor: {processor_type}). Try a different processor to compare results."
            )
        
        # Save file with processor type in filename for uniqueness
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Add processor type to filename to distinguish different processing of same file
        file_stem = Path(file.filename).stem
        file_ext = Path(file.filename).suffix
        unique_filename = f"{file_stem}_{processor_type}{file_ext}"
        
        file_path = await FileProcessor.save_file(content, unique_filename, upload_dir)
        
        # Use custom name if provided, otherwise use filename
        datasource_name = name.strip() if name and name.strip() else file.filename
        
        # Create data source record
        datasource = DataSource(
            name=datasource_name,
            source_type=SourceType.FILE,
            source_uri=str(file_path),
            file_size=file_size,
            content_hash=content_hash,
            processor_type=processor_enum,
            status=SourceStatus.ACTIVE,
            source_metadata=json.dumps({
                "file_extension": file_extension,
                "original_filename": file.filename,
                "custom_name": name,
                "description": description,
                "processor_type": processor_type,
            })
        )
        
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        
        # Load and create document records
        try:
            base_documents = DocumentLoader.load_file(
                str(file_path), 
                datasource_id=datasource.id,
                processor_type=processor_type  # Pass processor_type for PDFs
            )
            
            for base_doc in base_documents:
                document = Document(
                    datasource_id=datasource.id,
                    filename=base_doc.metadata.get("filename", file.filename),
                    original_filename=file.filename,
                    file_type=base_doc.metadata.get("file_type", file_extension[1:]),  # Remove dot
                    file_size=base_doc.metadata.get("file_size", file_size),
                    file_path=str(file_path),
                    content_hash=content_hash,
                    content=base_doc.content[:1000000] if base_doc.content else None,  # Limit to 1MB
                    num_pages=base_doc.metadata.get("num_pages"),
                    upload_status="completed"
                )
                db.add(document)
            
            db.commit()
            logger.info(
                "documents_created",
                datasource_id=datasource.id,
                num_documents=len(base_documents)
            )
        except Exception as e:
            logger.error(
                "document_creation_failed",
                datasource_id=datasource.id,
                error=str(e)
            )
            # Continue anyway - datasource is created even if document parsing fails
        
        logger.info(
            "datasource_uploaded",
            datasource_id=datasource.id,
            name=datasource.name,
            size=file_size,
            processor=processor_type
        )
        
        return DataSourceResponse.from_orm(datasource)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("datasource_upload_failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("", response_model=DataSourceListResponse)
def list_datasources(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all data sources."""
    datasources = db.query(DataSource).offset(skip).limit(limit).all()
    items = [DataSourceResponse.from_orm(ds) for ds in datasources]
    return DataSourceListResponse(total=len(items), items=items)


@router.get("/{datasource_id}", response_model=DataSourceResponse)
def get_datasource(
    datasource_id: int,
    db: Session = Depends(get_db),
):
    """Get a data source by ID."""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {datasource_id} not found"
        )
    return DataSourceResponse.from_orm(datasource)


@router.get("/{datasource_id}/documents")
def get_datasource_documents(
    datasource_id: int,
    db: Session = Depends(get_db),
):
    """Get documents associated with a datasource."""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {datasource_id} not found"
        )
    
    documents = db.query(Document).filter(Document.datasource_id == datasource_id).all()
    
    return {
        "datasource_id": datasource_id,
        "datasource_name": datasource.name,
        "total": len(documents),
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "num_pages": doc.num_pages,
                "content_preview": doc.content[:200] + "..." if doc.content and len(doc.content) > 200 else doc.content,
                "upload_status": doc.upload_status,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in documents
        ]
    }


@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_datasource(
    datasource_id: int,
    db: Session = Depends(get_db),
):
    """Delete a data source."""
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {datasource_id} not found"
        )
    
    # Delete file if it exists
    try:
        file_path = Path(datasource.source_uri)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning(
            "datasource_file_deletion_failed",
            datasource_id=datasource_id,
            error=str(e)
        )
    
    # Documents will be cascade deleted due to relationship
    db.delete(datasource)
    db.commit()
    
    logger.info("datasource_deleted", datasource_id=datasource_id)


@router.post("/compare-processors")
async def compare_processors(
    file: UploadFile = File(...),
):
    """
    Compare different PDF processors on the same file.
    
    This endpoint processes the same PDF file with all three processors
    (pypdf2, pdfplumber, docling) and returns the results for comparison.
    
    Args:
        file: PDF file to process
        
    Returns:
        Comparison results with content and metadata from each processor
    """
    # Validate file type
    file_extension = Path(file.filename).suffix.lower()
    if file_extension != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported for comparison"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Save temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        
        results = {}
        
        # Process with each processor
        for processor_name in ["pypdf2", "pdfplumber", "docling"]:
            try:
                processor_type = FileProcessorType(processor_name)
                file_processor = FileProcessor(processor_type=processor_type)
                
                extracted_content, num_pages, metadata = file_processor.extract_text_from_pdf(temp_path)
                
                results[processor_name] = {
                    "success": True,
                    "content": extracted_content,
                    "content_length": len(extracted_content),
                    "num_pages": num_pages,
                    "metadata": metadata,
                }
                
                logger.info(
                    "processor_comparison_success",
                    processor=processor_name,
                    content_length=len(extracted_content)
                )
                
            except Exception as e:
                results[processor_name] = {
                    "success": False,
                    "error": str(e),
                    "content": None,
                    "content_length": 0,
                    "num_pages": None,
                    "metadata": {}
                }
                
                logger.error(
                    "processor_comparison_failed",
                    processor=processor_name,
                    error=str(e)
                )
        
        # Clean up temp file
        try:
            temp_path.unlink()
        except:
            pass
        
        # Calculate comparison metrics
        comparison = {
            "filename": file.filename,
            "file_size": len(content),
            "processors": results,
            "summary": {
                "fastest": None,
                "most_content": None,
                "most_structured": None,
            }
        }
        
        # Determine which processor extracted the most content
        max_length = 0
        most_content_processor = None
        for processor_name, result in results.items():
            if result["success"] and result["content_length"] > max_length:
                max_length = result["content_length"]
                most_content_processor = processor_name
        
        comparison["summary"]["most_content"] = most_content_processor
        
        # Docling usually provides the most structure
        if results.get("docling", {}).get("success"):
            comparison["summary"]["most_structured"] = "docling"
        
        # PyPDF2 is usually the fastest
        if results.get("pypdf2", {}).get("success"):
            comparison["summary"]["fastest"] = "pypdf2"
        
        return comparison
        
    except Exception as e:
        logger.error("processor_comparison_failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare processors: {str(e)}"
        )

