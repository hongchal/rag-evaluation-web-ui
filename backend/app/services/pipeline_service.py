"""Pipeline Service"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import structlog
import time

from app.models.pipeline import Pipeline, PipelineType
from app.models.rag import RAGConfiguration
from app.models.datasource import DataSource, SourceStatus
from app.models.evaluation_dataset import EvaluationDataset
from app.models.base_document import BaseDocument
from app.models.chunk import Chunk
from app.schemas.pipeline import NormalPipelineCreate, TestPipelineCreate, PipelineUpdate
from app.services.qdrant_service import QdrantService
from app.services.rag_factory import RAGFactory
from app.services.document_loader import DocumentLoader
from app.services.file_processor import FileProcessor

logger = structlog.get_logger(__name__)


class PipelineService:
    """Pipeline 관리 서비스"""

    def __init__(self, db: Session, qdrant_service: Optional[QdrantService] = None):
        self.db = db
        self.qdrant_service = qdrant_service

    def create_normal_pipeline(
        self,
        pipeline_data: NormalPipelineCreate,
        auto_index: bool = True
    ) -> Pipeline:
        """
        Normal Pipeline 생성 (DataSource 기반)
        
        Args:
            pipeline_data: Pipeline 생성 데이터
            auto_index: 자동으로 인덱싱 수행 여부 (default: True)
            
        Returns:
            생성된 Pipeline
            
        Raises:
            ValueError: RAG 또는 DataSource가 존재하지 않을 때
        """
        # Validate RAG exists
        rag = self.db.query(RAGConfiguration).filter(
            RAGConfiguration.id == pipeline_data.rag_id
        ).first()
        if not rag:
            raise ValueError(f"RAG configuration {pipeline_data.rag_id} not found")

        # Validate all datasources exist
        datasources = self.db.query(DataSource).filter(
            DataSource.id.in_(pipeline_data.datasource_ids)
        ).all()
        
        if len(datasources) != len(pipeline_data.datasource_ids):
            found_ids = {ds.id for ds in datasources}
            missing_ids = set(pipeline_data.datasource_ids) - found_ids
            raise ValueError(f"Data sources not found: {missing_ids}")
        
        # Check if datasources are active (optional warning)
        inactive_datasources = [ds for ds in datasources if ds.status != SourceStatus.ACTIVE]
        if inactive_datasources:
            logger.warning(
                "pipeline_has_inactive_datasources",
                pipeline_name=pipeline_data.name,
                inactive_ids=[ds.id for ds in inactive_datasources]
            )

        # Create pipeline
        pipeline = Pipeline(
            name=pipeline_data.name,
            description=pipeline_data.description,
            pipeline_type=PipelineType.NORMAL,
            rag_id=pipeline_data.rag_id,
            dataset_id=None,
            datasources=datasources
        )
        
        self.db.add(pipeline)
        self.db.commit()
        self.db.refresh(pipeline)
        
        logger.info(
            "normal_pipeline_created",
            pipeline_id=pipeline.id,
            name=pipeline.name,
            rag_id=pipeline.rag_id,
            datasource_count=len(datasources)
        )
        
        # Auto index if requested and qdrant_service is available
        if auto_index and self.qdrant_service:
            try:
                self._index_pipeline_datasources(pipeline)
            except Exception as e:
                logger.error(
                    "pipeline_indexing_failed",
                    pipeline_id=pipeline.id,
                    error=str(e)
                )
                # Don't fail pipeline creation, just log the error
        
        return pipeline

    def create_test_pipeline(
        self,
        pipeline_data: TestPipelineCreate,
        auto_index: bool = True
    ) -> Pipeline:
        """
        Test Pipeline 생성 (EvaluationDataset 기반)
        
        Args:
            pipeline_data: Pipeline 생성 데이터
            auto_index: 자동으로 인덱싱 수행 여부 (default: True)
            
        Returns:
            생성된 Pipeline
            
        Raises:
            ValueError: RAG 또는 Dataset이 존재하지 않을 때
        """
        # Validate RAG exists
        rag = self.db.query(RAGConfiguration).filter(
            RAGConfiguration.id == pipeline_data.rag_id
        ).first()
        if not rag:
            raise ValueError(f"RAG configuration {pipeline_data.rag_id} not found")

        # Validate dataset exists
        dataset = self.db.query(EvaluationDataset).filter(
            EvaluationDataset.id == pipeline_data.dataset_id
        ).first()
        if not dataset:
            raise ValueError(f"Evaluation dataset {pipeline_data.dataset_id} not found")

        # Create pipeline
        pipeline = Pipeline(
            name=pipeline_data.name,
            description=pipeline_data.description,
            pipeline_type=PipelineType.TEST,
            rag_id=pipeline_data.rag_id,
            dataset_id=dataset.id,
        )
        
        self.db.add(pipeline)
        self.db.commit()
        self.db.refresh(pipeline)
        
        logger.info(
            "test_pipeline_created",
            pipeline_id=pipeline.id,
            name=pipeline.name,
            rag_id=pipeline.rag_id,
            dataset_id=dataset.id,
            dataset_name=dataset.name
        )
        
        # Auto index if requested and qdrant_service is available
        if auto_index and self.qdrant_service:
            try:
                self._index_pipeline_dataset(pipeline)
            except Exception as e:
                logger.error(
                    "pipeline_indexing_failed",
                    pipeline_id=pipeline.id,
                    error=str(e)
                )
                # Don't fail pipeline creation, just log the error
        
        return pipeline

    def get_pipeline(self, pipeline_id: int) -> Optional[Pipeline]:
        """Pipeline 조회"""
        return self.db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()

    def get_pipeline_by_name(self, name: str) -> Optional[Pipeline]:
        """이름으로 Pipeline 조회"""
        return self.db.query(Pipeline).filter(Pipeline.name == name).first()

    def list_pipelines(
        self,
        rag_id: Optional[int] = None,
        datasource_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Pipeline], int]:
        """
        Pipeline 목록 조회
        
        Args:
            rag_id: RAG ID로 필터링 (optional)
            datasource_id: DataSource ID로 필터링 (optional)
            skip: 건너뛸 개수
            limit: 최대 반환 개수
            
        Returns:
            (pipelines, total_count)
        """
        query = self.db.query(Pipeline)
        
        if rag_id is not None:
            query = query.filter(Pipeline.rag_id == rag_id)
        
        if datasource_id is not None:
            # Join with datasources
            query = query.join(Pipeline.datasources).filter(
                DataSource.id == datasource_id
            )
        
        total = query.count()
        pipelines = query.offset(skip).limit(limit).all()
        
        return pipelines, total

    def update_pipeline(
        self,
        pipeline_id: int,
        pipeline_data: PipelineUpdate
    ) -> Optional[Pipeline]:
        """
        Pipeline 업데이트
        
        Args:
            pipeline_id: Pipeline ID
            pipeline_data: 업데이트할 데이터
            
        Returns:
            업데이트된 Pipeline 또는 None
        """
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            return None

        # Update basic fields
        if pipeline_data.name is not None:
            pipeline.name = pipeline_data.name
        
        if pipeline_data.description is not None:
            pipeline.description = pipeline_data.description

        # Update datasources if provided
        if pipeline_data.datasource_ids is not None:
            datasources = self.db.query(DataSource).filter(
                DataSource.id.in_(pipeline_data.datasource_ids)
            ).all()
            
            if len(datasources) != len(pipeline_data.datasource_ids):
                found_ids = {ds.id for ds in datasources}
                missing_ids = set(pipeline_data.datasource_ids) - found_ids
                raise ValueError(f"Data sources not found: {missing_ids}")
            
            pipeline.datasources = datasources

        self.db.commit()
        self.db.refresh(pipeline)
        
        logger.info("pipeline_updated", pipeline_id=pipeline_id)
        
        return pipeline

    def delete_pipeline(self, pipeline_id: int) -> bool:
        """
        Pipeline 삭제
        
        Args:
            pipeline_id: Pipeline ID
            
        Returns:
            삭제 성공 여부
        """
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            return False

        # Before deletion: remove related vectors and documents only for this pipeline
        try:
            rag = pipeline.rag
            collection_name = rag.collection_name

            # Remove vectors from Qdrant filtered by pipeline_id
            # 이렇게 하면 같은 DataSource나 Dataset을 사용하는 다른 파이프라인의 벡터는 보존됩니다
            if self.qdrant_service:
                self.qdrant_service.delete_by_filter(
                    collection_name=collection_name,
                    filter_conditions={"pipeline_id": pipeline_id},
                )
                logger.info(
                    "pipeline_vectors_deleted",
                    pipeline_id=pipeline_id,
                    collection_name=collection_name
                )

            # NOTE: RDB 문서 스토어 정리
            # 현재 구조: 청크는 Qdrant에만 저장됨 (별도 RDB 청크 테이블 없음)
            # 향후 필요 시: 청크/문서 테이블 생성 후 여기서 pipeline_id로 필터링하여 삭제
            # Example:
            #   self.db.query(Chunk).filter(Chunk.pipeline_id == pipeline_id).delete()
            #   self.db.commit()
            # 
            # 주의: DataSource나 Dataset 레코드 자체는 삭제하지 않습니다.
            # 다른 파이프라인이 같은 데이터 소스를 공유할 수 있기 때문입니다.
        except Exception as e:
            logger.error("pipeline_vector_cleanup_failed", pipeline_id=pipeline_id, error=str(e))
            # Proceed with pipeline deletion anyway

        self.db.delete(pipeline)
        self.db.commit()
        
        logger.info("pipeline_deleted", pipeline_id=pipeline_id)
        
        return True

    def get_pipeline_datasource_ids(self, pipeline_id: int) -> List[int]:
        """
        Pipeline에 속한 DataSource ID 목록 반환
        
        이 메서드는 Query Service에서 사용됩니다.
        """
        pipeline = self.get_pipeline(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        
        return [ds.id for ds in pipeline.datasources]

    def _index_pipeline_datasources(self, pipeline: Pipeline) -> Dict[str, Any]:
        """
        Normal Pipeline의 DataSource들을 인덱싱
        
        DataSource 문서들을 RAG 설정에 따라:
        1. 청킹
        2. 임베딩
        3. Qdrant에 저장
        
        Args:
            pipeline: Pipeline 객체
            
        Returns:
            인덱싱 통계
        """
        if not self.qdrant_service:
            raise ValueError("QdrantService is required for indexing")
        
        logger.info(
            "starting_pipeline_indexing",
            pipeline_id=pipeline.id,
            rag_id=pipeline.rag.id,
            datasource_count=len(pipeline.datasources)
        )
        
        start_time = time.time()
        rag = pipeline.rag
        collection_name = rag.collection_name
        
        # Create chunker and embedder
        chunker = RAGFactory.create_chunker(rag.chunking_module, rag.chunking_params)
        embedder = RAGFactory.create_embedder(rag.embedding_module, rag.embedding_params)
        
        # Ensure Qdrant collection exists
        if not self.qdrant_service.collection_exists(collection_name):
            vector_size = embedder.EMBEDDING_DIM
            # Enable hybrid search for BGE-M3 (dense + sparse vectors)
            enable_hybrid = (rag.embedding_module == "bge_m3")
            self.qdrant_service.create_collection(collection_name, vector_size, enable_hybrid=enable_hybrid)
            logger.info(
                "qdrant_collection_created",
                collection_name=collection_name,
                vector_size=vector_size,
                hybrid_enabled=enable_hybrid
            )
        
        total_chunks = 0
        total_docs = 0
        
        # Process each datasource (file or directory)
        for datasource in pipeline.datasources:
            try:
                logger.info(
                    "indexing_datasource",
                    datasource_id=datasource.id,
                    datasource_name=datasource.name
                )
                
                from pathlib import Path
                path = Path(datasource.source_uri)

                # Build list of documents from file(s)
                documents: list[BaseDocument] = []
                if path.is_dir():
                    # Load supported files recursively
                    for fp in path.rglob("*"):
                        if not fp.is_file():
                            continue
                        if fp.suffix.lower() not in {".txt", ".pdf", ".json"}:
                            continue
                        documents.extend(DocumentLoader.load_file(str(fp), datasource_id=datasource.id))
                else:
                    documents.extend(DocumentLoader.load_file(str(path), datasource_id=datasource.id))

                if not documents:
                    logger.warning("no_documents_loaded_for_datasource", datasource_id=datasource.id)
                    continue

                # Chunk and embed, batch upserts
                for doc in documents:
                    chunks = chunker.chunk_document(doc)
                    if not chunks:
                        continue

                    texts = [c.content for c in chunks]
                    embedding_result = embedder.embed_texts(texts)
                    dense_vectors = embedding_result.get("dense", [])
                    sparse_vectors = embedding_result.get("sparse", None)

                    # Validate sparse_vectors format
                    valid_sparse = None
                    if sparse_vectors is not None and isinstance(sparse_vectors, list) and len(sparse_vectors) > 0:
                        # Check if first element is a valid sparse vector (has indices and values)
                        first_sparse = sparse_vectors[0]
                        if isinstance(first_sparse, dict) and "indices" in first_sparse and "values" in first_sparse:
                            if isinstance(first_sparse["indices"], list) and isinstance(first_sparse["values"], list):
                                valid_sparse = sparse_vectors

                    # Payload extras merged per chunk
                    payload_extra = {
                        "datasource_id": datasource.id,
                        "document_id": doc.id,
                        "chunk_index_field": "chunk_index",
                    }

                    # Build payloads with required fields (including pipeline_id)
                    payloads = []
                    for idx, ch in enumerate(chunks):
                        p = {
                            "content": ch.content,
                            "pipeline_id": pipeline.id,  # 파이프라인별 필터링을 위해 추가
                            "datasource_id": datasource.id,
                            "document_id": doc.id,
                            "chunk_index": idx,
                            "metadata": ch.metadata or {},
                        }
                        payloads.append(p)

                    # Upsert via unified API
                    vector_ids = self.qdrant_service.upsert_vectors(
                        collection_name=collection_name,
                        vectors=dense_vectors,
                        payloads=payloads,
                        sparse_vectors=valid_sparse,
                    )

                    # Save chunks to RDB
                    for idx, (ch, vector_id) in enumerate(zip(chunks, vector_ids)):
                        chunk_record = Chunk(
                            pipeline_id=pipeline.id,
                            document_id=doc.id,
                            chunk_index=idx,
                            content=ch.content,
                            metadata=ch.metadata or {},
                            vector_id=vector_id,
                            token_count=None,  # TODO: Calculate token count if needed
                            char_count=len(ch.content)
                        )
                        self.db.add(chunk_record)
                    
                    # Commit chunks for this document
                    self.db.commit()

                    total_chunks += len(chunks)
                    total_docs += 1
                
                logger.info(
                    "datasource_indexed",
                    datasource_id=datasource.id,
                    chunks_indexed=total_chunks
                )
                
            except Exception as e:
                logger.error(
                    "datasource_indexing_failed",
                    datasource_id=datasource.id,
                    error=str(e)
                )
                # Continue with other datasources
        
        elapsed = time.time() - start_time
        
        stats = {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "elapsed_seconds": elapsed
        }
        
        logger.info(
            "pipeline_indexing_completed",
            pipeline_id=pipeline.id,
            **stats
        )
        
        return stats

    def _index_pipeline_dataset(self, pipeline: Pipeline) -> Dict[str, Any]:
        """
        Test Pipeline의 EvaluationDataset을 인덱싱
        
        Dataset의 documents를 RAG 설정에 따라:
        1. 청킹
        2. 임베딩
        3. Qdrant에 저장
        
        Args:
            pipeline: Pipeline 객체
            
        Returns:
            인덱싱 통계
        """
        if not self.qdrant_service:
            raise ValueError("QdrantService is required for indexing")
        
        if not pipeline.dataset:
            raise ValueError(f"Pipeline {pipeline.id} does not have a dataset")
        
        logger.info(
            "starting_test_pipeline_indexing",
            pipeline_id=pipeline.id,
            rag_id=pipeline.rag.id,
            dataset_id=pipeline.dataset.id,
            dataset_name=pipeline.dataset.name
        )
        
        start_time = time.time()
        rag = pipeline.rag
        dataset = pipeline.dataset
        collection_name = rag.collection_name
        
        # Create chunker and embedder
        chunker = RAGFactory.create_chunker(rag.chunking_module, rag.chunking_params)
        embedder = RAGFactory.create_embedder(rag.embedding_module, rag.embedding_params)
        
        # Ensure Qdrant collection exists
        if not self.qdrant_service.collection_exists(collection_name):
            vector_size = embedder.EMBEDDING_DIM
            # Enable hybrid search for BGE-M3 (dense + sparse vectors)
            enable_hybrid = (rag.embedding_module == "bge_m3")
            self.qdrant_service.create_collection(collection_name, vector_size, enable_hybrid=enable_hybrid)
            logger.info(
                "qdrant_collection_created",
                collection_name=collection_name,
                vector_size=vector_size,
                hybrid_enabled=enable_hybrid
            )
        
        total_chunks = 0
        total_docs = len(dataset.documents)
        
        # Process each document in dataset
        for doc in dataset.documents:
            try:
                # Convert EvaluationDocument to BaseDocument for chunker
                base_doc = BaseDocument(
                    id=doc.doc_id,
                    content=doc.content,
                    source_type="evaluation_dataset",
                    source_uri=f"dataset_{dataset.id}_doc_{doc.doc_id}",
                    metadata={
                        "dataset_id": dataset.id,
                        "doc_id": doc.doc_id,
                        "title": doc.title or "",
                        "filename": doc.title or doc.doc_id,
                        "file_type": "evaluation_dataset",
                    }
                )
                
                # Chunk document
                chunks = chunker.chunk_document(base_doc)
                if not chunks:
                    continue
                
                # Embed chunks
                chunk_texts = [chunk.content for chunk in chunks]
                embedding_result = embedder.embed_texts(chunk_texts)
                dense_vectors = embedding_result.get("dense", [])
                sparse_vectors = embedding_result.get("sparse", None)
                
                # Validate sparse_vectors format
                valid_sparse_list = None
                if sparse_vectors is not None and isinstance(sparse_vectors, list) and len(sparse_vectors) > 0:
                    # Check if first element is a valid sparse vector (has indices and values)
                    first_sparse = sparse_vectors[0]
                    if isinstance(first_sparse, dict) and "indices" in first_sparse and "values" in first_sparse:
                        if isinstance(first_sparse["indices"], list) and isinstance(first_sparse["values"], list):
                            valid_sparse_list = sparse_vectors
                
                # Prepare points for Qdrant (including pipeline_id)
                for i, (chunk, embedding) in enumerate(zip(chunks, dense_vectors)):
                    point_id = f"pipeline_{pipeline.id}_dataset_{dataset.id}_doc_{doc.id}_chunk_{i}"
                    payload = {
                        "pipeline_id": pipeline.id,  # 파이프라인별 필터링을 위해 추가
                        "dataset_id": dataset.id,
                        "document_id": doc.id,
                        "chunk_index": i,
                        "content": chunk.content,
                        "metadata": {
                            "doc_id": doc.doc_id,
                            "title": doc.title or "",
                        }
                    }
                    
                    # Extract sparse vector for this specific chunk
                    chunk_sparse = None
                    if valid_sparse_list and i < len(valid_sparse_list):
                        chunk_sparse = [valid_sparse_list[i]]
                    
                    self.qdrant_service.upsert_vectors(
                        collection_name=collection_name,
                        vectors=[embedding],
                        payloads=[payload],
                        sparse_vectors=chunk_sparse,
                    )
                
                total_chunks += len(chunks)
                
            except Exception as e:
                logger.error(
                    "document_indexing_failed",
                    document_id=doc.id,
                    error=str(e)
                )
                # Continue with other documents
        
        elapsed = time.time() - start_time
        
        stats = {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "elapsed_seconds": elapsed
        }
        
        logger.info(
            "test_pipeline_indexing_completed",
            pipeline_id=pipeline.id,
            **stats
        )
        
        return stats

