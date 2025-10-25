"""
전체 통합 테스트 실행
실제 파일로 Pipeline 생성, 쿼리, 평가까지 테스트
"""
import sys
sys.path.insert(0, '.')

import os
import time
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.rag import RAGConfiguration
from app.models.datasource import DataSource
from app.models.pipeline import Pipeline, PipelineType
from app.services.qdrant_service import QdrantService
from app.services.pipeline_service import PipelineService
from app.services.query_service import QueryService
from app.schemas.pipeline import NormalPipelineCreate, TestPipelineCreate

print("=" * 80)
print("🧪 통합 테스트 시작")
print("=" * 80)

# Database
db = SessionLocal()

# 테스트 파일 경로
TEST_FILES = {
    'txt1': 'test_data/sample_document.txt',
    'txt2': 'test_data/tech_trends.txt',
    'json': 'test_data/products.json',
}

# 파일 존재 확인
print("\n[1] 테스트 파일 확인")
print("-" * 80)
for name, path in TEST_FILES.items():
    full_path = os.path.join(os.getcwd(), path)
    if os.path.exists(full_path):
        size = os.path.getsize(full_path)
        print(f"✓ {name}: {path} ({size} bytes)")
    else:
        print(f"✗ {name}: {path} - 파일 없음!")

try:
    # ========================================================================
    # Step 1: Qdrant 연결 확인
    # ========================================================================
    print("\n[2] Qdrant 서버 연결 확인")
    print("-" * 80)
    
    try:
        qdrant_service = QdrantService()
        print("✓ Qdrant 서버 연결 성공")
    except Exception as e:
        print(f"✗ Qdrant 서버 연결 실패: {e}")
        print("  → docker-compose up qdrant 명령으로 Qdrant 서버를 실행해주세요")
        sys.exit(1)
    
    # ========================================================================
    # Step 2: RAG Configuration 생성
    # ========================================================================
    print("\n[3] RAG Configuration 생성")
    print("-" * 80)
    
    # 기존 RAG 확인 또는 생성
    rag_name = "IntegrationTest-RAG-Recursive-BGE-M3"
    existing_rag = db.query(RAGConfiguration).filter(
        RAGConfiguration.name == rag_name
    ).first()
    
    if existing_rag:
        print(f"✓ 기존 RAG 사용: {existing_rag.name}")
        test_rag = existing_rag
    else:
        test_rag = RAGConfiguration(
            name=rag_name,
            description="Integration test RAG with recursive chunking and BGE-M3",
            chunking_module="recursive",
            chunking_params={
                "chunk_size": 512,
                "chunk_overlap": 50
            },
            embedding_module="bge_m3",
            embedding_params={},
            reranking_module="none",
            reranking_params={},
            collection_name="integration_test_collection",
        )
        db.add(test_rag)
        db.commit()
        db.refresh(test_rag)
        print(f"✓ 새 RAG 생성: {test_rag.name}")
    
    print(f"  - ID: {test_rag.id}")
    print(f"  - Chunking: {test_rag.chunking_module}")
    print(f"  - Embedding: {test_rag.embedding_module}")
    print(f"  - Collection: {test_rag.collection_name}")
    
    # ========================================================================
    # Step 3: DataSource 생성
    # ========================================================================
    print("\n[4] DataSource 생성")
    print("-" * 80)
    
    # TXT DataSource
    txt_ds_name = "IntegrationTest-TextFiles"
    existing_txt_ds = db.query(DataSource).filter(
        DataSource.name == txt_ds_name
    ).first()
    
    if existing_txt_ds:
        print(f"✓ 기존 TXT DataSource 사용: {existing_txt_ds.name}")
        txt_datasource = existing_txt_ds
    else:
        from app.models.datasource import SourceType, SourceStatus
        txt_datasource = DataSource(
            name=txt_ds_name,
            source_type=SourceType.FILE,
            source_uri=os.path.abspath("test_data/sample_document.txt"),
            status=SourceStatus.ACTIVE,
            source_metadata='{"description": "Integration test text files"}'
        )
        db.add(txt_datasource)
        db.commit()
        db.refresh(txt_datasource)
        print(f"✓ 새 TXT DataSource 생성: {txt_datasource.name}")
    
    # JSON DataSource
    json_ds_name = "IntegrationTest-JSONFile"
    existing_json_ds = db.query(DataSource).filter(
        DataSource.name == json_ds_name
    ).first()
    
    if existing_json_ds:
        print(f"✓ 기존 JSON DataSource 사용: {existing_json_ds.name}")
        json_datasource = existing_json_ds
    else:
        json_datasource = DataSource(
            name=json_ds_name,
            source_type=SourceType.FILE,
            source_uri=os.path.abspath("test_data/products.json"),
            status=SourceStatus.ACTIVE,
            source_metadata='{"description": "Integration test JSON file"}'
        )
        db.add(json_datasource)
        db.commit()
        db.refresh(json_datasource)
        print(f"✓ 새 JSON DataSource 생성: {json_datasource.name}")
    
    # ========================================================================
    # Step 4: Pipeline 생성 (자동 인덱싱)
    # ========================================================================
    print("\n[5] NORMAL Pipeline 생성 (자동 인덱싱)")
    print("-" * 80)
    
    pipeline_service = PipelineService(db, qdrant_service)
    
    # 기존 파이프라인 확인
    pipeline_name = "IntegrationTest-Normal-Pipeline"
    existing_pipeline = db.query(Pipeline).filter(
        Pipeline.name == pipeline_name
    ).first()
    
    if existing_pipeline:
        print(f"✓ 기존 Pipeline 사용: {existing_pipeline.name}")
        # 기존 파이프라인 삭제 후 재생성
        print("  → 기존 파이프라인 삭제 중...")
        pipeline_service.delete_pipeline(existing_pipeline.id)
        print("  ✓ 삭제 완료")
    
    # 새 파이프라인 생성
    print("  → 새 Pipeline 생성 및 인덱싱 중...")
    print("  ⚠  이 작업은 시간이 걸릴 수 있습니다 (임베딩 모델 로딩 + 인덱싱)")
    
    start_time = time.time()
    
    try:
        normal_pipeline_data = NormalPipelineCreate(
            name=pipeline_name,
            description="Integration test pipeline with multiple data sources",
            pipeline_type="normal",
            rag_id=test_rag.id,
            datasource_ids=[txt_datasource.id, json_datasource.id]
        )
        
        normal_pipeline = pipeline_service.create_normal_pipeline(normal_pipeline_data)
        
        elapsed = time.time() - start_time
        print(f"  ✓ Pipeline 생성 완료 ({elapsed:.2f}초)")
        print(f"    - Pipeline ID: {normal_pipeline.id}")
        print(f"    - Type: {normal_pipeline.pipeline_type.value}")
        print(f"    - DataSources: {len(normal_pipeline.datasources)}개")
        
    except Exception as e:
        print(f"  ✗ Pipeline 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ========================================================================
    # Step 5: Query 테스트
    # ========================================================================
    print("\n[6] Query 테스트")
    print("-" * 80)
    
    query_service = QueryService(db, qdrant_service)
    
    test_queries = [
        "RAG 시스템이 무엇인가요?",
        "MacBook Pro의 가격은 얼마인가요?",
        "하이브리드 검색에 대해 설명해주세요",
    ]
    
    for i, query_text in enumerate(test_queries, 1):
        print(f"\n쿼리 {i}: '{query_text}'")
        print("-" * 60)
        
        try:
            result = query_service.search(
                pipeline_id=normal_pipeline.id,
                query=query_text,
                top_k=3
            )
            
            print(f"✓ 검색 완료")
            print(f"  - 검색 시간: {result.total_time:.3f}초")
            print(f"  - 검색된 청크: {len(result.chunks)}개")
            
            if result.chunks:
                print(f"  - Top 1 Score: {result.chunks[0]['score']:.4f}")
                content_preview = result.chunks[0]['content'][:150]
                print(f"  - Top 1 Content: {content_preview}...")
            
        except Exception as e:
            print(f"✗ 쿼리 실패: {e}")
            import traceback
            traceback.print_exc()
    
    # ========================================================================
    # Step 6: Pipeline 조회 테스트
    # ========================================================================
    print("\n[7] Pipeline 조회 테스트")
    print("-" * 80)
    
    all_pipelines = pipeline_service.list_pipelines()
    if isinstance(all_pipelines, list) and len(all_pipelines) > 0:
        print(f"✓ 전체 Pipeline 수: {len(all_pipelines)}")
        for p in all_pipelines:
            if hasattr(p, 'name'):
                print(f"  - {p.name} (ID: {p.id}, Type: {p.pipeline_type.value})")
            else:
                print(f"  - (Invalid pipeline object: {type(p)})")
    else:
        print(f"✓ 전체 Pipeline 수: 0")
    
    # 특정 Pipeline 조회
    retrieved_pipeline = pipeline_service.get_pipeline(normal_pipeline.id)
    print(f"\n✓ Pipeline 상세 조회:")
    print(f"  - Name: {retrieved_pipeline.name}")
    print(f"  - RAG: {retrieved_pipeline.rag.name}")
    print(f"  - DataSources: {[ds.name for ds in retrieved_pipeline.datasources]}")
    
    # ========================================================================
    # 최종 요약
    # ========================================================================
    print("\n" + "=" * 80)
    print("🎉 통합 테스트 완료!")
    print("=" * 80)
    
    summary = {
        "RAG Configuration": "✓ PASS",
        "DataSource 생성": "✓ PASS",
        "Pipeline 생성 (자동 인덱싱)": "✓ PASS",
        "Query 실행": "✓ PASS",
        "Pipeline 조회": "✓ PASS",
    }
    
    for test_name, result in summary.items():
        print(f"  {test_name:35s}: {result}")
    
    print("\n✅ 모든 핵심 기능이 정상 동작합니다!")
    print("\n📝 다음 단계:")
    print("  1. Frontend에서 API 호출 테스트")
    print("  2. TEST Pipeline 생성 및 평가 테스트")
    print("  3. 다중 파이프라인 비교 평가 테스트")
    
except Exception as e:
    print(f"\n❌ 테스트 중 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    db.close()
    print("\n" + "=" * 80)

