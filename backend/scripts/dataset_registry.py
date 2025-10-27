#!/usr/bin/env python3
"""
데이터셋 레지스트리 관리 스크립트

다운로드한 데이터셋을 데이터베이스에 등록하고 관리합니다.

Usage:
    # 특정 데이터셋 등록
    python backend/scripts/dataset_registry.py register backend/datasets/frames_eval.json
    
    # 모든 데이터셋 자동 등록
    python backend/scripts/dataset_registry.py auto-register
    
    # 등록된 데이터셋 목록 확인
    python backend/scripts/dataset_registry.py list
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.models.evaluation_dataset import EvaluationDataset
    from app.models.evaluation_document import EvaluationDocument
    from app.models.evaluation_query import EvaluationQuery
    from app.core.database import Base
except ImportError as e:
    print(f"❌ 필수 모듈을 import할 수 없습니다: {e}")
    print("   backend 디렉토리가 Python path에 있는지 확인하세요.")
    sys.exit(1)


class DatasetRegistry:
    """데이터셋 레지스트리 관리자"""
    
    def __init__(self):
        """데이터베이스 연결 초기화"""
        try:
            # DATABASE_URL 환경변수를 우선적으로 사용 (서브프로세스 실행 시)
            database_url = os.environ.get("DATABASE_URL", settings.database_url)
            
            # 데이터베이스 엔진 생성
            self.engine = create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True
            )
            
            # 테이블 생성
            Base.metadata.create_all(bind=self.engine)
            
            # 세션 팩토리
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.session = SessionLocal()
            
            print("✅ 데이터베이스 연결 완료")
            
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            sys.exit(1)
    
    def __del__(self):
        """세션 정리"""
        if hasattr(self, 'session'):
            self.session.close()
    
    def register_dataset(self, dataset_file: str) -> bool:
        """데이터셋을 데이터베이스에 등록"""
        
        dataset_path = Path(dataset_file)
        
        if not dataset_path.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {dataset_file}")
            return False
        
        print(f"\n📝 데이터셋 등록: {dataset_path.name}")
        
        try:
            # JSON 파일 로드
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 기본 정보 추출
            name = data.get("name", dataset_path.stem)
            description = data.get("description", "")
            documents = data.get("documents", [])
            queries = data.get("queries", [])
            metadata = data.get("metadata", {})
            
            print(f"   이름: {name}")
            print(f"   문서: {len(documents)}개")
            print(f"   쿼리: {len(queries)}개")
            
            # 이미 등록된 데이터셋인지 확인
            existing = self.session.query(EvaluationDataset).filter_by(name=name).first()
            
            if existing:
                print(f"   ⚠️  이미 등록된 데이터셋입니다 (ID: {existing.id})")
                print(f"   기존 데이터를 업데이트합니다...")
                
                # 기존 문서와 쿼리 삭제
                self.session.query(EvaluationDocument).filter_by(dataset_id=existing.id).delete()
                self.session.query(EvaluationQuery).filter_by(dataset_id=existing.id).delete()
                
                # 데이터셋 업데이트
                existing.description = description
                existing.dataset_uri = str(dataset_path.absolute())
                existing.num_queries = len(queries)
                existing.num_documents = len(documents)
                dataset_obj = existing
            else:
                # 새 데이터셋 생성
                dataset_obj = EvaluationDataset(
                    name=name,
                    description=description,
                    dataset_uri=str(dataset_path.absolute()),
                    num_queries=len(queries),
                    num_documents=len(documents)
                )
                self.session.add(dataset_obj)
                self.session.flush()  # ID 생성
            
            # 문서 추가
            print(f"   📄 문서 등록 중...")
            for doc_data in documents:
                doc = EvaluationDocument(
                    dataset_id=dataset_obj.id,
                    doc_id=doc_data["id"],
                    content=doc_data["content"],
                    title=doc_data.get("title", ""),
                    metadata=doc_data.get("metadata", {})
                )
                self.session.add(doc)
            
            # 쿼리 추가
            print(f"   ❓ 쿼리 등록 중...")
            for query_data in queries:
                query = EvaluationQuery(
                    dataset_id=dataset_obj.id,
                    query=query_data["query"],
                    relevant_doc_ids=query_data.get("relevant_doc_ids", []),
                    expected_answer=query_data.get("expected_answer", ""),
                    difficulty=query_data.get("difficulty", "medium"),
                    query_type=query_data.get("query_type", "unknown"),
                    metadata=query_data.get("metadata", {})
                )
                self.session.add(query)
            
            # 커밋
            self.session.commit()
            
            print(f"   ✅ 등록 완료! (Dataset ID: {dataset_obj.id})")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 실패: {e}")
            return False
        except Exception as e:
            print(f"❌ 등록 실패: {e}")
            self.session.rollback()
            return False
    
    def auto_register(self, dataset_dir: str = "backend/datasets") -> List[str]:
        """디렉토리의 모든 JSON 파일을 자동 등록"""
        
        dataset_path = Path(dataset_dir)
        
        if not dataset_path.exists():
            print(f"❌ 디렉토리를 찾을 수 없습니다: {dataset_dir}")
            return []
        
        print(f"\n🔍 데이터셋 디렉토리 스캔: {dataset_dir}")
        
        # JSON 파일 찾기
        json_files = list(dataset_path.glob("*_eval.json"))
        
        if not json_files:
            print(f"   ⚠️  등록할 데이터셋이 없습니다 (*_eval.json)")
            return []
        
        print(f"   발견한 데이터셋: {len(json_files)}개")
        
        registered = []
        
        for json_file in json_files:
            if self.register_dataset(str(json_file)):
                registered.append(str(json_file))
        
        print(f"\n✅ 자동 등록 완료: {len(registered)}/{len(json_files)}")
        
        return registered
    
    def list_datasets(self):
        """등록된 데이터셋 목록 출력"""
        
        print("\n📚 등록된 데이터셋 목록:\n")
        
        try:
            datasets = self.session.query(EvaluationDataset).all()
            
            if not datasets:
                print("   등록된 데이터셋이 없습니다.")
                return
            
            for ds in datasets:
                # 문서와 쿼리 개수 계산
                doc_count = self.session.query(EvaluationDocument).filter_by(dataset_id=ds.id).count()
                query_count = self.session.query(EvaluationQuery).filter_by(dataset_id=ds.id).count()
                
                print(f"📦 {ds.name} (ID: {ds.id})")
                print(f"   설명: {ds.description}")
                print(f"   문서: {doc_count}개")
                print(f"   쿼리: {query_count}개")
                print(f"   생성일: {ds.created_at}")
                print()
            
            print(f"총 {len(datasets)}개 데이터셋 등록됨")
            
        except Exception as e:
            print(f"❌ 목록 조회 실패: {e}")
    
    def delete_dataset(self, dataset_id: int) -> bool:
        """데이터셋 삭제"""
        
        print(f"\n🗑️  데이터셋 삭제: ID {dataset_id}")
        
        try:
            # 데이터셋 찾기
            dataset = self.session.query(EvaluationDataset).filter_by(id=dataset_id).first()
            
            if not dataset:
                print(f"❌ 데이터셋을 찾을 수 없습니다: ID {dataset_id}")
                return False
            
            print(f"   이름: {dataset.name}")
            
            # 관련 문서와 쿼리도 함께 삭제 (CASCADE)
            self.session.delete(dataset)
            self.session.commit()
            
            print(f"   ✅ 삭제 완료!")
            return True
            
        except Exception as e:
            print(f"❌ 삭제 실패: {e}")
            self.session.rollback()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="데이터셋 레지스트리 관리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 특정 데이터셋 등록
  python backend/scripts/dataset_registry.py register backend/datasets/frames_eval.json
  
  # 모든 데이터셋 자동 등록
  python backend/scripts/dataset_registry.py auto-register
  
  # 다른 디렉토리의 데이터셋 자동 등록
  python backend/scripts/dataset_registry.py auto-register --dir /path/to/datasets
  
  # 등록된 데이터셋 목록 확인
  python backend/scripts/dataset_registry.py list
  
  # 데이터셋 삭제
  python backend/scripts/dataset_registry.py delete --id 1
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="명령어")
    
    # 등록 명령
    register_parser = subparsers.add_parser("register", help="데이터셋 등록")
    register_parser.add_argument("dataset_file", help="등록할 데이터셋 JSON 파일")
    
    # 자동 등록 명령
    auto_parser = subparsers.add_parser("auto-register", help="디렉토리의 모든 데이터셋 자동 등록")
    auto_parser.add_argument("--dir", default="backend/datasets", help="데이터셋 디렉토리")
    
    # 목록 명령
    list_parser = subparsers.add_parser("list", help="등록된 데이터셋 목록")
    
    # 삭제 명령
    delete_parser = subparsers.add_parser("delete", help="데이터셋 삭제")
    delete_parser.add_argument("--id", type=int, required=True, help="삭제할 데이터셋 ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 레지스트리 초기화
    registry = DatasetRegistry()
    
    # 명령 실행
    if args.command == "register":
        registry.register_dataset(args.dataset_file)
    
    elif args.command == "auto-register":
        registry.auto_register(args.dir)
    
    elif args.command == "list":
        registry.list_datasets()
    
    elif args.command == "delete":
        registry.delete_dataset(args.id)


if __name__ == "__main__":
    main()

