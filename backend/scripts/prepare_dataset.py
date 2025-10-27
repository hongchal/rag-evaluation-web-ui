#!/usr/bin/env python3
"""
범용 데이터셋 준비 스크립트

BEIR, Wikipedia, MS MARCO 등 다양한 RAG 평가 데이터셋을 다운로드하고
평가 시스템에서 사용 가능한 형태로 변환합니다.

Usage:
    # BEIR 데이터셋
    python backend/scripts/prepare_dataset.py beir --name scifact
    python backend/scripts/prepare_dataset.py beir --name hotpotqa --sample 1000
    
    # 모든 BEIR 데이터셋 한번에
    python backend/scripts/prepare_dataset.py download-all
    
    # Wikipedia 데이터셋
    python backend/scripts/prepare_dataset.py wikipedia --size 1000
    
    # MS MARCO
    python backend/scripts/prepare_dataset.py msmarco --size 10000
    
    # 데이터셋 검증
    python backend/scripts/prepare_dataset.py verify --dataset backend/datasets/frames_eval.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# datasets 라이브러리
try:
    from datasets import load_dataset
except ImportError:
    print("❌ datasets 라이브러리가 설치되지 않았습니다.")
    print("   다음 명령어로 설치하세요: pip install datasets")
    sys.exit(1)


def register_dataset_to_db(dataset_path: str) -> bool:
    """데이터셋을 데이터베이스에 등록"""
    print(f"\n📝 데이터베이스에 자동 등록 중...")
    try:
        # dataset_registry 모듈 직접 실행
        import subprocess
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent / "dataset_registry.py"),
                "register",
                dataset_path
            ],
            env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/rag_evaluation")},
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"   ✅ 데이터베이스 등록 완료!")
            return True
        else:
            print(f"   ⚠️  데이터베이스 등록 실패")
            if result.stderr:
                print(f"   에러: {result.stderr[:200]}")
            print(f"   수동으로 등록하려면:")
            print(f"   DATABASE_URL=\"postgresql://postgres:postgres@localhost:5433/rag_evaluation\" \\")
            print(f"     python3 backend/scripts/dataset_registry.py register {dataset_path}")
            return False
    except Exception as e:
        print(f"   ⚠️  자동 등록 실패: {e}")
        print(f"   수동으로 등록하려면:")
        print(f"   DATABASE_URL=\"postgresql://postgres:postgres@localhost:5433/rag_evaluation\" \\")
        print(f"     python3 backend/scripts/dataset_registry.py register {dataset_path}")
        return False


# BEIR 데이터셋 목록
BEIR_DATASETS = {
    "scifact": {
        "name": "BEIR SciFact",
        "description": "Scientific fact verification dataset",
        "size": "small"
    },
    "nfcorpus": {
        "name": "BEIR NFCorpus",
        "description": "Nutrition and health corpus",
        "size": "small"
    },
    "hotpotqa": {
        "name": "BEIR HotpotQA",
        "description": "Multi-hop question answering",
        "size": "large"
    },
    "fiqa": {
        "name": "BEIR FiQA",
        "description": "Financial question answering",
        "size": "medium"
    },
    "trec-covid": {
        "name": "BEIR TREC-COVID",
        "description": "COVID-19 research articles",
        "size": "large"
    }
}


class BEIRDatasetPreparer:
    """BEIR 데이터셋 준비"""
    
    def __init__(self, dataset_name: str, output_dir: str = "backend/datasets", sample_size: Optional[int] = None, auto_register: bool = True):
        self.dataset_name = dataset_name
        self.output_dir = Path(output_dir)
        self.sample_size = sample_size
        self.auto_register = auto_register
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare(self) -> str:
        """BEIR 데이터셋 다운로드 및 변환"""
        
        if self.dataset_name not in BEIR_DATASETS:
            print(f"❌ 알 수 없는 BEIR 데이터셋: {self.dataset_name}")
            print(f"   사용 가능한 데이터셋: {', '.join(BEIR_DATASETS.keys())}")
            return None
        
        info = BEIR_DATASETS[self.dataset_name]
        print(f"\n🦛 BEIR 데이터셋 다운로드: {info['name']}")
        print(f"   설명: {info['description']}")
        print(f"   크기: {info['size']}")
        
        try:
            # BEIR 라이브러리 사용
            from beir import util
            from beir.datasets.data_loader import GenericDataLoader
            
            # 데이터셋 다운로드
            url = f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{self.dataset_name}.zip"
            data_path = util.download_and_unzip(url, str(self.output_dir / ".beir"))
            
            # 데이터 로드
            corpus, queries, qrels = GenericDataLoader(data_folder=data_path).load(split="test")
            
            print(f"   ✅ 로드 완료:")
            print(f"      - 문서: {len(corpus)}")
            print(f"      - 쿼리: {len(queries)}")
            
            # 샘플링
            if self.sample_size:
                queries = dict(list(queries.items())[:self.sample_size])
                print(f"   📊 샘플링: {len(queries)} 쿼리")
            
            # 평가 형식으로 변환
            documents = []
            eval_queries = []
            
            # 문서 변환
            for doc_id, doc_data in corpus.items():
                documents.append({
                    "id": f"beir_{self.dataset_name}_{doc_id}",
                    "content": doc_data.get("text", ""),
                    "title": doc_data.get("title", "Untitled"),
                    "metadata": {
                        "source": f"beir_{self.dataset_name}",
                        "original_id": doc_id
                    }
                })
            
            # 쿼리 변환
            for query_id, query_text in queries.items():
                # 관련 문서 찾기
                relevant_docs = []
                if query_id in qrels:
                    relevant_docs = [
                        f"beir_{self.dataset_name}_{doc_id}"
                        for doc_id in qrels[query_id].keys()
                    ]
                
                eval_queries.append({
                    "query": query_text,
                    "relevant_doc_ids": relevant_docs,
                    "expected_answer": "",  # BEIR는 answer 없음
                    "difficulty": "medium",
                    "query_type": "retrieval",
                    "metadata": {
                        "source": f"beir_{self.dataset_name}",
                        "original_id": query_id
                    }
                })
            
            # 최종 데이터셋
            evaluation_dataset = {
                "name": info["name"],
                "description": info["description"],
                "documents": documents,
                "queries": eval_queries,
                "metadata": {
                    "source": f"beir/{self.dataset_name}",
                    "total_documents": len(documents),
                    "total_queries": len(eval_queries)
                }
            }
            
            # 저장
            output_file = self.output_dir / f"beir_{self.dataset_name}_eval.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(evaluation_dataset, f, indent=2, ensure_ascii=False)
            
            file_size = output_file.stat().st_size / 1024 / 1024
            print(f"\n✅ 완료: {output_file}")
            print(f"   📊 통계:")
            print(f"      - 문서: {len(documents)}")
            print(f"      - 쿼리: {len(eval_queries)}")
            print(f"      - 파일 크기: {file_size:.2f} MB")
            
            # 자동 DB 등록
            if self.auto_register:
                self._register_to_db(str(output_file))
            
            return str(output_file)
            
        except ImportError:
            print("❌ BEIR 라이브러리가 설치되지 않았습니다.")
            print("   다음 명령어로 설치하세요: pip install beir")
            return None
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            return None
    
    def _register_to_db(self, dataset_path: str):
        """데이터베이스에 등록"""
        register_dataset_to_db(dataset_path)


class WikipediaDatasetPreparer:
    """Wikipedia 데이터셋 준비"""
    
    def __init__(self, size: int = 1000, queries_per_doc: int = 2, output_dir: str = "backend/datasets", auto_register: bool = True):
        self.size = size
        self.queries_per_doc = queries_per_doc
        self.output_dir = Path(output_dir)
        self.auto_register = auto_register
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare(self) -> str:
        """Wikipedia 데이터셋 생성"""
        
        print(f"\n🦛 Wikipedia 데이터셋 생성")
        print(f"   문서 수: {self.size}")
        print(f"   쿼리/문서: {self.queries_per_doc}")
        
        try:
            # Wikipedia 데이터셋 로드
            print(f"\n📦 Wikipedia 데이터셋 로딩...")
            dataset = load_dataset("wikipedia", "20220301.en", split=f"train[:{self.size}]")
            print(f"   ✅ 로드 완료: {len(dataset)} 문서")
            
            documents = []
            queries = []
            
            for idx, example in enumerate(dataset):
                if idx % 100 == 0:
                    print(f"   진행: {idx}/{len(dataset)}")
                
                title = example.get("title", "")
                text = example.get("text", "")
                
                if not text or len(text) < 100:
                    continue
                
                doc_id = f"wiki_{idx}"
                
                # 문서 생성
                documents.append({
                    "id": doc_id,
                    "content": text,
                    "title": title,
                    "metadata": {
                        "source": "wikipedia",
                        "doc_idx": idx
                    }
                })
                
                # 간단한 쿼리 생성 (제목 기반)
                for q_idx in range(self.queries_per_doc):
                    query_text = f"What is {title}?"
                    if q_idx == 1:
                        query_text = f"Tell me about {title}"
                    
                    queries.append({
                        "query": query_text,
                        "relevant_doc_ids": [doc_id],
                        "expected_answer": text[:200] + "...",
                        "difficulty": "easy",
                        "query_type": "factual",
                        "metadata": {
                            "source": "wikipedia",
                            "doc_idx": idx,
                            "query_idx": q_idx
                        }
                    })
            
            # 최종 데이터셋
            evaluation_dataset = {
                "name": f"Wikipedia-{self.size}",
                "description": f"Wikipedia articles with auto-generated queries ({self.size} docs)",
                "documents": documents,
                "queries": queries,
                "metadata": {
                    "source": "wikipedia/20220301.en",
                    "total_documents": len(documents),
                    "total_queries": len(queries),
                    "queries_per_doc": self.queries_per_doc
                }
            }
            
            # 저장
            output_file = self.output_dir / f"wikipedia_{self.size}_eval.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(evaluation_dataset, f, indent=2, ensure_ascii=False)
            
            file_size = output_file.stat().st_size / 1024 / 1024
            print(f"\n✅ 완료: {output_file}")
            print(f"   📊 통계:")
            print(f"      - 문서: {len(documents)}")
            print(f"      - 쿼리: {len(queries)}")
            print(f"      - 파일 크기: {file_size:.2f} MB")
            
            # 자동 DB 등록
            if self.auto_register:
                register_dataset_to_db(str(output_file))
            
            return str(output_file)
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            return None


class MSMARCODatasetPreparer:
    """MS MARCO 데이터셋 준비"""
    
    def __init__(self, size: int = 10000, output_dir: str = "backend/datasets", auto_register: bool = True):
        self.size = size
        self.output_dir = Path(output_dir)
        self.auto_register = auto_register
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare(self) -> str:
        """MS MARCO 데이터셋 다운로드"""
        
        print(f"\n🦛 MS MARCO 데이터셋 다운로드")
        print(f"   크기: {self.size} passages")
        
        try:
            # MS MARCO 데이터셋 로드
            print(f"\n📦 MS MARCO 로딩...")
            dataset = load_dataset("ms_marco", "v2.1", split=f"train[:{self.size}]")
            print(f"   ✅ 로드 완료: {len(dataset)} 항목")
            
            documents = []
            queries = []
            doc_id_map = {}
            
            for idx, example in enumerate(dataset):
                if idx % 1000 == 0:
                    print(f"   진행: {idx}/{len(dataset)}")
                
                query = example.get("query", "")
                passages = example.get("passages", {})
                answers = example.get("answers", [])
                
                if not query:
                    continue
                
                relevant_doc_ids = []
                
                # Passage를 문서로 변환
                for p_idx, passage in enumerate(passages.get("passage_text", [])):
                    doc_id = f"msmarco_{idx}_p{p_idx}"
                    
                    documents.append({
                        "id": doc_id,
                        "content": passage,
                        "title": f"Passage {idx}-{p_idx}",
                        "metadata": {
                            "source": "msmarco",
                            "query_idx": idx,
                            "passage_idx": p_idx
                        }
                    })
                    
                    # 관련 문서로 표시
                    if passages.get("is_selected", [])[p_idx]:
                        relevant_doc_ids.append(doc_id)
                
                # 쿼리 생성
                queries.append({
                    "query": query,
                    "relevant_doc_ids": relevant_doc_ids,
                    "expected_answer": answers[0] if answers else "",
                    "difficulty": "medium",
                    "query_type": "qa",
                    "metadata": {
                        "source": "msmarco",
                        "query_idx": idx
                    }
                })
            
            # 최종 데이터셋
            evaluation_dataset = {
                "name": f"MS-MARCO-{self.size}",
                "description": f"MS MARCO passages for retrieval evaluation ({self.size} queries)",
                "documents": documents,
                "queries": queries,
                "metadata": {
                    "source": "ms_marco/v2.1",
                    "total_documents": len(documents),
                    "total_queries": len(queries)
                }
            }
            
            # 저장
            output_file = self.output_dir / f"msmarco_{self.size}_eval.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(evaluation_dataset, f, indent=2, ensure_ascii=False)
            
            file_size = output_file.stat().st_size / 1024 / 1024
            print(f"\n✅ 완료: {output_file}")
            print(f"   📊 통계:")
            print(f"      - 문서: {len(documents)}")
            print(f"      - 쿼리: {len(queries)}")
            print(f"      - 파일 크기: {file_size:.2f} MB")
            
            # 자동 DB 등록
            if self.auto_register:
                register_dataset_to_db(str(output_file))
            
            return str(output_file)
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            return None


def download_all_beir(output_dir: str = "backend/datasets", auto_register: bool = True) -> List[str]:
    """모든 BEIR 데이터셋 다운로드"""
    
    print("\n🦛 모든 BEIR 데이터셋 다운로드 시작")
    print(f"   데이터셋 수: {len(BEIR_DATASETS)}")
    
    downloaded = []
    
    for dataset_name in BEIR_DATASETS.keys():
        print(f"\n{'='*60}")
        preparer = BEIRDatasetPreparer(dataset_name, output_dir, auto_register=auto_register)
        output_file = preparer.prepare()
        
        if output_file:
            downloaded.append(output_file)
    
    print(f"\n{'='*60}")
    print(f"✅ 전체 다운로드 완료: {len(downloaded)}/{len(BEIR_DATASETS)}")
    
    return downloaded


def verify_dataset(dataset_path: str):
    """데이터셋 검증 및 통계 출력"""
    
    print(f"\n🔍 데이터셋 검증: {dataset_path}")
    
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"\n📊 기본 정보:")
        print(f"   이름: {data.get('name', 'Unknown')}")
        print(f"   설명: {data.get('description', 'No description')}")
        
        documents = data.get("documents", [])
        queries = data.get("queries", [])
        
        print(f"\n📊 통계:")
        print(f"   문서 수: {len(documents)}")
        print(f"   쿼리 수: {len(queries)}")
        
        if documents:
            doc_lengths = [len(d["content"]) for d in documents]
            print(f"\n📄 문서 길이:")
            print(f"   평균: {sum(doc_lengths) / len(doc_lengths):.0f} 자")
            print(f"   최소: {min(doc_lengths)} 자")
            print(f"   최대: {max(doc_lengths)} 자")
        
        if queries:
            query_lengths = [len(q["query"]) for q in queries]
            print(f"\n❓ 쿼리 길이:")
            print(f"   평균: {sum(query_lengths) / len(query_lengths):.0f} 자")
            print(f"   최소: {min(query_lengths)} 자")
            print(f"   최대: {max(query_lengths)} 자")
            
            # 쿼리 타입 분포
            query_types = {}
            for q in queries:
                qt = q.get("query_type", "unknown")
                query_types[qt] = query_types.get(qt, 0) + 1
            
            print(f"\n🏷️  쿼리 타입 분포:")
            for qt, count in query_types.items():
                print(f"   {qt}: {count}")
        
        print(f"\n✅ 검증 완료!")
        
    except Exception as e:
        print(f"❌ 검증 실패: {e}")


def list_datasets():
    """사용 가능한 데이터셋 목록"""
    
    print("\n📚 사용 가능한 데이터셋:\n")
    
    print("BEIR 벤치마크:")
    for name, info in BEIR_DATASETS.items():
        print(f"  - {name:15s} : {info['description']} ({info['size']})")
    
    print("\n기타:")
    print(f"  - wikipedia     : Wikipedia articles with auto-generated queries")
    print(f"  - msmarco       : MS MARCO passages for retrieval")


def main():
    parser = argparse.ArgumentParser(
        description="범용 데이터셋 준비 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="명령어")
    
    # BEIR 명령
    beir_parser = subparsers.add_parser("beir", help="BEIR 데이터셋 다운로드")
    beir_parser.add_argument("--name", required=True, choices=BEIR_DATASETS.keys(), help="BEIR 데이터셋 이름")
    beir_parser.add_argument("--sample", type=int, help="샘플 크기")
    beir_parser.add_argument("--output-dir", default="backend/datasets", help="출력 디렉토리")
    beir_parser.add_argument("--no-register", action="store_true", help="자동 DB 등록 건너뛰기")
    
    # 모든 BEIR 다운로드
    download_all_parser = subparsers.add_parser("download-all", help="모든 BEIR 데이터셋 다운로드")
    download_all_parser.add_argument("--output-dir", default="backend/datasets", help="출력 디렉토리")
    download_all_parser.add_argument("--no-register", action="store_true", help="자동 DB 등록 건너뛰기")
    
    # Wikipedia 명령
    wiki_parser = subparsers.add_parser("wikipedia", help="Wikipedia 데이터셋 생성")
    wiki_parser.add_argument("--size", type=int, default=1000, help="문서 수")
    wiki_parser.add_argument("--queries-per-doc", type=int, default=2, help="문서당 쿼리 수")
    wiki_parser.add_argument("--output-dir", default="backend/datasets", help="출력 디렉토리")
    wiki_parser.add_argument("--no-register", action="store_true", help="자동 DB 등록 건너뛰기")
    
    # MS MARCO 명령
    msmarco_parser = subparsers.add_parser("msmarco", help="MS MARCO 데이터셋 다운로드")
    msmarco_parser.add_argument("--size", type=int, default=10000, help="Passage 수")
    msmarco_parser.add_argument("--output-dir", default="backend/datasets", help="출력 디렉토리")
    msmarco_parser.add_argument("--no-register", action="store_true", help="자동 DB 등록 건너뛰기")
    
    # 검증 명령
    verify_parser = subparsers.add_parser("verify", help="데이터셋 검증")
    verify_parser.add_argument("--dataset", required=True, help="검증할 데이터셋 경로")
    
    # 목록 명령
    list_parser = subparsers.add_parser("list", help="사용 가능한 데이터셋 목록")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 명령 실행
    if args.command == "beir":
        auto_register = not args.no_register
        preparer = BEIRDatasetPreparer(args.name, args.output_dir, args.sample, auto_register)
        preparer.prepare()
    
    elif args.command == "download-all":
        auto_register = not args.no_register
        download_all_beir(args.output_dir, auto_register)
    
    elif args.command == "wikipedia":
        auto_register = not args.no_register
        preparer = WikipediaDatasetPreparer(args.size, args.queries_per_doc, args.output_dir, auto_register)
        preparer.prepare()
    
    elif args.command == "msmarco":
        auto_register = not args.no_register
        preparer = MSMARCODatasetPreparer(args.size, args.output_dir, auto_register)
        preparer.prepare()
    
    elif args.command == "verify":
        verify_dataset(args.dataset)
    
    elif args.command == "list":
        list_datasets()


if __name__ == "__main__":
    main()

