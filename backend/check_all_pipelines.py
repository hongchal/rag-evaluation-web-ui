"""
모든 Pipeline의 상태를 확인하는 스크립트
"""

import sys
sys.path.insert(0, '/Users/chohongcheol/rag-evaluation-web-ui/backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient

from app.core.config import settings
from app.models.pipeline import Pipeline


def check_all_pipelines():
    """모든 Pipeline 상태 확인"""
    
    print("=" * 100)
    print("모든 Pipeline 상태 확인")
    print("=" * 100)
    
    engine = create_engine(settings.database_url)
    db = Session(engine)
    qdrant = QdrantClient(url=settings.qdrant_url)
    
    try:
        pipelines = db.query(Pipeline).order_by(Pipeline.id).all()
        
        print(f"\n총 {len(pipelines)}개의 Pipeline 발견\n")
        
        # 테이블 헤더
        print(f"{'ID':<5} {'이름':<50} {'타입':<8} {'상태':<10} {'Chunks':<8} {'RAG ID':<8} {'Reranking':<20}")
        print("-" * 120)
        
        failed_pipelines = []
        success_pipelines = []
        pending_pipelines = []
        
        for pipeline in pipelines:
            rag = pipeline.rag
            reranking = rag.reranking_module if rag else "N/A"
            
            # 인덱싱 통계
            stats = pipeline.indexing_stats or {}
            chunks = stats.get('total_chunks', 0)
            
            # Collection 확인
            try:
                if rag and rag.collection_name:
                    collection = qdrant.get_collection(rag.collection_name)
                    actual_points = collection.points_count
                else:
                    actual_points = 0
            except:
                actual_points = 0
            
            status = pipeline.status.value if pipeline.status else 'N/A'
            
            print(f"{pipeline.id:<5} {pipeline.name[:48]:<50} {pipeline.pipeline_type.value:<8} "
                  f"{status:<10} {chunks:<8} {pipeline.rag_id:<8} {reranking:<20}")
            
            if status == "failed":
                failed_pipelines.append((pipeline.id, pipeline.name, reranking))
            elif status == "ready":
                success_pipelines.append((pipeline.id, pipeline.name, reranking, chunks, actual_points))
            elif status == "pending":
                pending_pipelines.append((pipeline.id, pipeline.name, reranking))
        
        # 요약
        print("\n" + "=" * 100)
        print("요약")
        print("=" * 100)
        
        if failed_pipelines:
            print(f"\n❌ 실패한 Pipeline ({len(failed_pipelines)}개):")
            for pid, name, reranking in failed_pipelines:
                print(f"   - Pipeline {pid}: {name}")
                print(f"     Reranking: {reranking}")
        
        if pending_pipelines:
            print(f"\n⏳ 대기 중인 Pipeline ({len(pending_pipelines)}개):")
            for pid, name, reranking in pending_pipelines:
                print(f"   - Pipeline {pid}: {name}")
                print(f"     Reranking: {reranking}")
        
        if success_pipelines:
            print(f"\n✅ 성공한 Pipeline ({len(success_pipelines)}개):")
            for pid, name, reranking, chunks, actual_points in success_pipelines:
                match = "✓" if chunks == actual_points else "✗"
                print(f"   - Pipeline {pid}: {name}")
                print(f"     Reranking: {reranking}, Chunks: {chunks}, Qdrant points: {actual_points} {match}")
        
        # Reranking 모듈별 통계
        print(f"\n📊 Reranking 모듈별 통계:")
        reranking_stats = {}
        for pipeline in pipelines:
            rag = pipeline.rag
            if rag:
                reranking = rag.reranking_module
                status = pipeline.status.value
                
                if reranking not in reranking_stats:
                    reranking_stats[reranking] = {"total": 0, "ready": 0, "failed": 0, "pending": 0}
                
                reranking_stats[reranking]["total"] += 1
                reranking_stats[reranking][status] += 1
        
        for reranking, stats in sorted(reranking_stats.items()):
            print(f"   {reranking}: ")
            print(f"      Total: {stats['total']}, "
                  f"Ready: {stats['ready']}, "
                  f"Failed: {stats['failed']}, "
                  f"Pending: {stats['pending']}")
    
    finally:
        db.close()


if __name__ == "__main__":
    check_all_pipelines()




