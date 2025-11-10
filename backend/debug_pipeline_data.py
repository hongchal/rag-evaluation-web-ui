"""
Pipeline 데이터 디버깅 스크립트

특정 pipeline의 인덱싱 상태와 Qdrant 데이터를 확인합니다.
"""

import sys
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient

# Add backend to path
sys.path.insert(0, '/Users/chohongcheol/rag-evaluation-web-ui/backend')

from app.core.config import settings
from app.models.pipeline import Pipeline


def check_pipeline_data(pipeline_id: int):
    """Pipeline 데이터 확인"""
    
    print(f"=" * 80)
    print(f"Pipeline {pipeline_id} 데이터 확인")
    print(f"=" * 80)
    
    # 1. Database에서 Pipeline 정보 확인
    print(f"\n[1] Database에서 Pipeline 정보 조회")
    print("-" * 80)
    
    engine = create_engine(settings.database_url)
    db = Session(engine)
    
    try:
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        
        if not pipeline:
            print(f"❌ Pipeline {pipeline_id}를 찾을 수 없습니다!")
            return
        
        print(f"✅ Pipeline 정보:")
        print(f"   ID: {pipeline.id}")
        print(f"   이름: {pipeline.name}")
        print(f"   타입: {pipeline.pipeline_type.value}")
        print(f"   RAG ID: {pipeline.rag_id}")
        print(f"   Dataset ID: {pipeline.dataset_id}")
        print(f"   상태: {pipeline.status.value if pipeline.status else 'N/A'}")
        
        if pipeline.indexing_stats:
            stats = pipeline.indexing_stats
            print(f"\n   인덱싱 통계:")
            print(f"   - Total chunks: {stats.get('total_chunks', 0)}")
            print(f"   - Total documents: {stats.get('total_documents', 0)}")
            print(f"   - Chunking time: {stats.get('chunking_time', 0):.2f}s")
            print(f"   - Embedding time: {stats.get('embedding_time', 0):.2f}s")
        else:
            print(f"\n   ⚠️  인덱싱 통계가 없습니다!")
        
        # RAG 정보
        rag = pipeline.rag
        if rag:
            print(f"\n✅ RAG 정보:")
            print(f"   ID: {rag.id}")
            print(f"   이름: {rag.name}")
            print(f"   Collection: {rag.collection_name}")
            print(f"   Chunking: {rag.chunking_module}")
            print(f"   Embedding: {rag.embedding_module}")
            print(f"   Reranking: {rag.reranking_module}")
        else:
            print(f"❌ RAG 정보를 찾을 수 없습니다!")
            return
        
        # 2. Qdrant에서 데이터 확인
        print(f"\n[2] Qdrant Collection 확인")
        print("-" * 80)
        
        qdrant = QdrantClient(url=settings.qdrant_url)
        collection_name = rag.collection_name
        
        try:
            # Collection 정보
            collection_info = qdrant.get_collection(collection_name)
            print(f"✅ Collection '{collection_name}' 존재")
            print(f"   Points count: {collection_info.points_count}")
            print(f"   Vector size: {collection_info.config.params.vectors}")
            
            if collection_info.points_count == 0:
                print(f"\n❌ Collection이 비어있습니다!")
                print(f"   Pipeline 인덱싱이 완료되지 않았거나 실패했을 수 있습니다.")
                return
            
            # 3. Pipeline ID로 필터링된 데이터 확인
            print(f"\n[3] Pipeline {pipeline_id}의 데이터 확인")
            print("-" * 80)
            
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Scroll로 해당 pipeline_id를 가진 모든 points 조회
            filter_obj = Filter(
                must=[
                    FieldCondition(
                        key="pipeline_id",
                        match=MatchValue(value=pipeline_id)
                    )
                ]
            )
            
            scroll_result = qdrant.scroll(
                collection_name=collection_name,
                scroll_filter=filter_obj,
                limit=10,  # 처음 10개만
                with_payload=True,
                with_vectors=False,
            )
            
            points = scroll_result[0]
            
            if not points:
                print(f"❌ Pipeline {pipeline_id}의 데이터가 없습니다!")
                print(f"\n가능한 원인:")
                print(f"  1. 인덱싱이 실패했을 수 있습니다")
                print(f"  2. pipeline_id가 payload에 저장되지 않았을 수 있습니다")
                print(f"  3. 다른 pipeline_id로 저장되었을 수 있습니다")
                
                # Collection의 샘플 데이터 확인
                print(f"\n[4] Collection의 샘플 데이터 확인 (첫 3개)")
                print("-" * 80)
                sample_result = qdrant.scroll(
                    collection_name=collection_name,
                    limit=3,
                    with_payload=True,
                    with_vectors=False,
                )
                
                for i, point in enumerate(sample_result[0], 1):
                    payload = point.payload or {}
                    print(f"\n샘플 {i}:")
                    print(f"  ID: {point.id}")
                    print(f"  Pipeline ID: {payload.get('pipeline_id', 'N/A')}")
                    print(f"  Dataset ID: {payload.get('dataset_id', 'N/A')}")
                    print(f"  Document ID: {payload.get('document_id', 'N/A')}")
                    print(f"  Content: {payload.get('content', '')[:100]}...")
                
            else:
                print(f"✅ Pipeline {pipeline_id}의 데이터를 찾았습니다!")
                print(f"   찾은 points: {len(points)}개")
                
                # 처음 3개 데이터 상세 정보
                print(f"\n   상세 정보 (첫 3개):")
                for i, point in enumerate(points[:3], 1):
                    payload = point.payload or {}
                    print(f"\n   Point {i}:")
                    print(f"   - ID: {point.id}")
                    print(f"   - Pipeline ID: {payload.get('pipeline_id')}")
                    print(f"   - Dataset ID: {payload.get('dataset_id')}")
                    print(f"   - Document ID: {payload.get('document_id')}")
                    print(f"   - Chunk Index: {payload.get('chunk_index')}")
                    print(f"   - Content: {payload.get('content', '')[:100]}...")
                
                # 4. 실제 검색 테스트
                print(f"\n[4] 실제 검색 테스트")
                print("-" * 80)
                
                # 간단한 테스트 쿼리
                from app.services.rag_factory import RAGFactory
                
                embedder = RAGFactory.create_embedder(
                    rag.embedding_module,
                    rag.embedding_params
                )
                
                test_query = "test query"
                print(f"테스트 쿼리: '{test_query}'")
                
                # Embed
                if hasattr(embedder, "embed_query"):
                    q = embedder.embed_query(test_query)
                    query_vector = q.get("dense") if isinstance(q, dict) else q
                else:
                    q = embedder.embed_texts([test_query])
                    query_vector = q.get("dense")[0] if isinstance(q, dict) else q[0]
                
                # Search with filter
                uses_named_vectors = isinstance(collection_info.config.params.vectors, dict)
                
                if uses_named_vectors:
                    search_results = qdrant.search(
                        collection_name=collection_name,
                        query_vector=("dense", query_vector),
                        limit=5,
                        query_filter=filter_obj,
                    )
                else:
                    search_results = qdrant.search(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        limit=5,
                        query_filter=filter_obj,
                    )
                
                print(f"\n검색 결과: {len(search_results)}개")
                
                if not search_results:
                    print(f"❌ 검색 결과가 없습니다!")
                    print(f"   필터는 정상 작동했지만 embedding이나 vector가 문제일 수 있습니다.")
                else:
                    print(f"✅ 검색 성공!")
                    for i, hit in enumerate(search_results[:3], 1):
                        print(f"\n   결과 {i}:")
                        print(f"   - Score: {hit.score:.4f}")
                        print(f"   - Content: {hit.payload.get('content', '')[:100]}...")
        
        except Exception as e:
            print(f"❌ Qdrant 작업 중 오류: {e}")
            import traceback
            traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python debug_pipeline_data.py <pipeline_id>")
        print("예: python debug_pipeline_data.py 98")
        sys.exit(1)
    
    pipeline_id = int(sys.argv[1])
    check_pipeline_data(pipeline_id)

