#!/usr/bin/env python3
"""
FRAMES 데이터셋 다운로드 스크립트

Google의 FRAMES (Factuality, Retrieval, And reasoning MEasurement Set) 벤치마크를
다운로드하고 RAG 평가 시스템에서 사용 가능한 형태로 변환합니다.

Usage:
    # 빠른 테스트 (Wikipedia 내용 없이)
    python backend/scripts/download_frames.py --sample --no-fetch-wikipedia
    
    # 완전한 데이터셋 (Wikipedia 내용 포함) - 추천
    python backend/scripts/download_frames.py --fetch-wikipedia
    
    # 200개 쿼리만 + Wikipedia 내용
    python backend/scripts/download_frames.py --max-queries 200 --fetch-wikipedia
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# datasets 라이브러리 임포트 시도
try:
    from datasets import load_dataset
except ImportError:
    print("❌ datasets 라이브러리가 설치되지 않았습니다.")
    print("   다음 명령어로 설치하세요: pip install datasets")
    sys.exit(1)

# Wikipedia API용 라이브러리
try:
    import requests
except ImportError:
    print("❌ requests 라이브러리가 설치되지 않았습니다.")
    print("   다음 명령어로 설치하세요: pip install requests")
    sys.exit(1)


class FramesDownloader:
    """FRAMES 데이터셋 다운로더"""
    
    def __init__(
        self,
        output_path: str = "backend/datasets/frames_eval.json",
        fetch_wikipedia: bool = False,
        max_queries: Optional[int] = None,
        sample: bool = False
    ):
        self.output_path = Path(output_path)
        self.fetch_wikipedia = fetch_wikipedia
        self.max_queries = max_queries if not sample else 100
        self.sample = sample
        
        # 출력 디렉토리 생성
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def fetch_wikipedia_content(self, title: str) -> Optional[str]:
        """Wikipedia API를 통해 실제 내용 가져오기"""
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + title.replace(" ", "_")
        
        # Wikipedia requires a User-Agent header
        headers = {
            'User-Agent': 'RAG-Evaluation-System/1.0 (Educational/Research Purpose; Contact: admin@example.com)'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # extract 필드가 있으면 사용 (요약)
            content = data.get("extract", "")
            
            if not content:
                return None
            
            return content
            
        except Exception as e:
            return None
    
    def convert_to_evaluation_format(self, dataset) -> Dict[str, Any]:
        """FRAMES 데이터셋을 평가 형식으로 변환"""
        
        print("\n📝 데이터셋 변환 중...", flush=True)
        
        documents = []
        queries = []
        doc_id_map = {}  # Wikipedia 제목 → 문서 ID 매핑
        
        # 쿼리 제한 적용
        total_examples = len(dataset)
        if self.max_queries:
            dataset = dataset.select(range(min(self.max_queries, total_examples)))
        
        print(f"   처리할 쿼리 수: {len(dataset)}", flush=True)
        
        for idx, example in enumerate(dataset):
            if idx % 50 == 0:
                print(f"   진행: {idx}/{len(dataset)} 쿼리", flush=True)
            
            # 쿼리 정보
            question = example.get("Prompt", "")
            answer = example.get("Answer", "")
            wikipedia_links = example.get("wiki_links", [])
            reasoning_type = example.get("reasoning_types", ["unknown"])[0]
            
            # Parse wiki_links if it's a string (JSON format)
            if isinstance(wikipedia_links, str):
                import ast
                try:
                    wikipedia_links = ast.literal_eval(wikipedia_links)
                except:
                    wikipedia_links = []
            
            if not question:
                continue
            
            # 관련 문서 ID 리스트
            relevant_doc_ids = []
            
            # Wikipedia 링크에서 문서 생성
            for wiki_link in wikipedia_links:
                # 제목 추출
                title = wiki_link.split("/")[-1].replace("_", " ")
                
                # 이미 처리된 문서인지 확인
                if title in doc_id_map:
                    relevant_doc_ids.append(doc_id_map[title])
                    continue
                
                # 새 문서 ID 생성
                doc_id = f"frames_q{idx}_doc{len(documents)}"
                doc_id_map[title] = doc_id
                relevant_doc_ids.append(doc_id)
                
                # Wikipedia 내용 가져오기
                if self.fetch_wikipedia:
                    if len(documents) % 100 == 0 and len(documents) > 0:
                        print(f"   📥 Wikipedia 문서 다운로드 중: {len(documents)}/{len(doc_id_map)} 문서", flush=True)
                    content = self.fetch_wikipedia_content(title)
                    if content is None:
                        content = f"[Wikipedia content for '{title}']"
                    # Rate limiting (be respectful to Wikipedia API)
                    time.sleep(0.2)
                else:
                    content = f"[Placeholder content for Wikipedia article: {title}]"
                
                # 문서 생성
                document = {
                    "id": doc_id,
                    "content": content,
                    "title": title,
                    "metadata": {
                        "source": "frames",
                        "wikipedia_url": wiki_link,
                        "question_idx": idx,
                        "content_length": len(content)
                    }
                }
                documents.append(document)
            
            # 쿼리 생성
            query = {
                "query": question,
                "relevant_doc_ids": relevant_doc_ids,
                "expected_answer": answer,
                "difficulty": "hard",  # FRAMES는 대부분 어려움
                "query_type": "multi-hop" if len(relevant_doc_ids) > 1 else "single-hop",
                "metadata": {
                    "source": "frames",
                    "question_idx": idx,
                    "reasoning_type": reasoning_type,
                    "num_wikipedia_links": len(wikipedia_links)
                }
            }
            queries.append(query)
        
        # 최종 데이터셋 구조
        evaluation_dataset = {
            "name": "FRAMES-RAG",
            "description": "Google FRAMES benchmark for RAG evaluation with multi-hop reasoning",
            "documents": documents,
            "queries": queries,
            "metadata": {
                "source": "google/frames-benchmark",
                "version": "2024",
                "total_examples": total_examples,
                "converted_queries": len(queries),
                "converted_documents": len(documents),
                "fetched_wikipedia": self.fetch_wikipedia
            }
        }
        
        return evaluation_dataset
    
    def download(self):
        """데이터셋 다운로드 및 변환"""
        
        print("🦛 FRAMES 데이터셋 다운로드 시작", flush=True)
        print(f"   출력 경로: {self.output_path}", flush=True)
        print(f"   Wikipedia 가져오기: {'✅' if self.fetch_wikipedia else '❌'}", flush=True)
        print(f"   최대 쿼리 수: {self.max_queries or '전체 (824)'}", flush=True)
        
        # 1. HuggingFace에서 FRAMES 데이터셋 로드
        print("\n📦 HuggingFace에서 데이터셋 로딩...", flush=True)
        try:
            dataset = load_dataset("google/frames-benchmark", split="test")
            print(f"   ✅ 로드 완료: {len(dataset)} 예제", flush=True)
        except Exception as e:
            print(f"   ❌ 로드 실패: {e}", flush=True)
            return False
        
        # 2. 평가 형식으로 변환
        evaluation_dataset = self.convert_to_evaluation_format(dataset)
        
        # 3. JSON 파일로 저장
        print(f"\n💾 파일 저장 중: {self.output_path}", flush=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_dataset, f, indent=2, ensure_ascii=False)
        
        # 4. 통계 출력
        file_size = self.output_path.stat().st_size / 1024 / 1024  # MB
        print(f"\n✅ 다운로드 완료!", flush=True)
        print(f"   쿼리: {len(evaluation_dataset['queries'])}, 문서: {len(evaluation_dataset['documents'])}, 크기: {file_size:.2f}MB", flush=True)
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="FRAMES 데이터셋 다운로드",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 빠른 테스트 (100 queries, placeholder content)
  python backend/scripts/download_frames.py --sample --no-fetch-wikipedia
  
  # 완전한 데이터셋 (824 queries, real Wikipedia content) - 추천
  python backend/scripts/download_frames.py --fetch-wikipedia
  
  # 200 queries + real Wikipedia content
  python backend/scripts/download_frames.py --max-queries 200 --fetch-wikipedia
  
  # 커스텀 출력 경로
  python backend/scripts/download_frames.py --fetch-wikipedia --output custom/path.json
        """
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="backend/datasets/frames_eval.json",
        help="출력 JSON 파일 경로 (default: backend/datasets/frames_eval.json)"
    )
    
    parser.add_argument(
        "--fetch-wikipedia",
        action="store_true",
        help="실제 Wikipedia 내용 가져오기 (시간 소요, 하지만 권장)"
    )
    
    parser.add_argument(
        "--no-fetch-wikipedia",
        dest="fetch_wikipedia",
        action="store_false",
        help="Placeholder 내용만 사용 (빠른 테스트용)"
    )
    
    parser.add_argument(
        "--max-queries",
        type=int,
        help="최대 쿼리 수 제한 (예: 200)"
    )
    
    parser.add_argument(
        "--sample",
        action="store_true",
        help="샘플 모드 (100 queries만)"
    )
    
    parser.add_argument(
        "--register",
        action="store_true",
        default=True,
        help="다운로드 후 자동으로 DB에 등록 (기본: True)"
    )
    
    parser.add_argument(
        "--no-register",
        dest="register",
        action="store_false",
        help="자동 DB 등록 건너뛰기"
    )
    
    parser.set_defaults(fetch_wikipedia=False)
    
    args = parser.parse_args()
    
    # 다운로더 실행
    downloader = FramesDownloader(
        output_path=args.output,
        fetch_wikipedia=args.fetch_wikipedia,
        max_queries=args.max_queries,
        sample=args.sample
    )
    
    success = downloader.download()
    
    if success:
        # 자동 DB 등록
        if args.register:
            print(f"\n📝 데이터베이스에 자동 등록 중...")
            try:
                import subprocess
                import os
                result = subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).parent / "dataset_registry.py"),
                        "register",
                        args.output
                    ],
                    env={**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/rag_evaluation")},
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print(f"   ✅ 데이터베이스 등록 완료!")
                else:
                    print(f"   ⚠️  데이터베이스 등록 실패")
            except Exception as e:
                print(f"   ⚠️  자동 등록 실패: {e}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

