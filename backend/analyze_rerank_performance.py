#!/usr/bin/env python3
"""
ReRank 성능 분석 스크립트

백엔드 로그를 분석하여 ReRank가 검색 성능에 미치는 영향을 분석합니다.

사용법:
1. 백엔드 재시작 후 평가 실행
2. 로그 수집: docker-compose logs backend > backend_logs.txt
3. 이 스크립트 실행: python analyze_rerank_performance.py backend_logs.txt
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

def parse_log_line(line: str) -> Dict[str, Any]:
    """JSON 로그 라인 파싱"""
    try:
        # structlog JSON 형식 파싱
        if '{"event":' in line or '{"timestamp":' in line:
            # JSON 부분만 추출
            json_start = line.find('{')
            if json_start >= 0:
                json_str = line[json_start:]
                return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    return {}

def analyze_rerank_impact(log_file: Path) -> None:
    """ReRank 영향 분석"""
    
    print("=" * 80)
    print("ReRank 성능 분석")
    print("=" * 80)
    
    rerank_logs = []
    
    # 로그 파일 읽기
    print(f"\n[1] 로그 파일 분석 중: {log_file}")
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            log_data = parse_log_line(line)
            if log_data.get("event") == "reranking_detailed_comparison":
                rerank_logs.append(log_data)
    
    if not rerank_logs:
        print("❌ ReRank 로그를 찾을 수 없습니다.")
        print("\n다음을 확인하세요:")
        print("1. 백엔드가 재시작되었는지")
        print("2. ReRank를 사용하는 파이프라인으로 평가했는지")
        print("3. 로그 파일이 올바른지")
        return
    
    print(f"✓ {len(rerank_logs)}개의 ReRank 로그 발견")
    
    # 분석
    print("\n[2] ReRank 영향 분석")
    print("-" * 80)
    
    total_queries = len(rerank_logs)
    queries_with_changes = 0
    position_changes = []  # (before_rank, after_rank, doc_id)
    docs_promoted = []  # 순위가 올라간 문서
    docs_demoted = []   # 순위가 내려간 문서
    
    for log in rerank_logs:
        before_doc_ids = log.get("before_doc_ids", [])
        after_doc_ids = log.get("after_doc_ids", [])
        
        if before_doc_ids != after_doc_ids:
            queries_with_changes += 1
        
        # 각 doc의 순위 변화 추적
        for doc_id in set(before_doc_ids + after_doc_ids):
            before_rank = before_doc_ids.index(doc_id) + 1 if doc_id in before_doc_ids else None
            after_rank = after_doc_ids.index(doc_id) + 1 if doc_id in after_doc_ids else None
            
            if before_rank and after_rank:
                if after_rank < before_rank:
                    # 순위 상승 (더 위로)
                    docs_promoted.append({
                        "doc_id": doc_id,
                        "before": before_rank,
                        "after": after_rank,
                        "improvement": before_rank - after_rank
                    })
                elif after_rank > before_rank:
                    # 순위 하락 (더 아래로)
                    docs_demoted.append({
                        "doc_id": doc_id,
                        "before": before_rank,
                        "after": after_rank,
                        "degradation": after_rank - before_rank
                    })
    
    # 요약
    print(f"총 쿼리 수: {total_queries}")
    print(f"순서가 변경된 쿼리: {queries_with_changes} ({queries_with_changes/total_queries*100:.1f}%)")
    print(f"\n순위 상승 문서: {len(docs_promoted)}개")
    print(f"순위 하락 문서: {len(docs_demoted)}개")
    
    # 가장 큰 변화
    if docs_promoted:
        best_promotion = max(docs_promoted, key=lambda x: x["improvement"])
        print(f"\n최대 순위 상승: {best_promotion['doc_id']}")
        print(f"  {best_promotion['before']}위 → {best_promotion['after']}위 (+{best_promotion['improvement']})")
    
    if docs_demoted:
        worst_demotion = max(docs_demoted, key=lambda x: x["degradation"])
        print(f"\n최대 순위 하락: {worst_demotion['doc_id']}")
        print(f"  {worst_demotion['before']}위 → {worst_demotion['after']}위 (-{worst_demotion['degradation']})")
    
    # 상세 분석: 쿼리별 변화
    print("\n\n[3] 쿼리별 상세 분석 (처음 5개)")
    print("-" * 80)
    
    for i, log in enumerate(rerank_logs[:5], 1):
        query = log.get("query", "N/A")
        rerank_module = log.get("reranking_module", "N/A")
        num_candidates = log.get("num_candidates", 0)
        
        before_doc_ids = log.get("before_doc_ids", [])
        after_doc_ids = log.get("after_doc_ids", [])
        
        print(f"\n쿼리 {i}: {query}")
        print(f"ReRank 모듈: {rerank_module}")
        print(f"후보 문서 수: {num_candidates}")
        
        print(f"\n벡터 검색 Top 5 doc_ids:")
        for rank, doc_id in enumerate(before_doc_ids[:5], 1):
            print(f"  {rank}. {doc_id}")
        
        print(f"\nReRank 후 Top 5 doc_ids:")
        for rank, doc_id in enumerate(after_doc_ids[:5], 1):
            # 순위 변화 표시
            before_rank = before_doc_ids.index(doc_id) + 1 if doc_id in before_doc_ids else None
            if before_rank:
                change = before_rank - rank
                if change > 0:
                    change_str = f"↑{change}"
                elif change < 0:
                    change_str = f"↓{abs(change)}"
                else:
                    change_str = "="
                print(f"  {rank}. {doc_id} (was #{before_rank}, {change_str})")
            else:
                print(f"  {rank}. {doc_id} (NEW)")
    
    # ReRank 모델별 통계
    print("\n\n[4] ReRank 모델별 통계")
    print("-" * 80)
    
    by_model = defaultdict(list)
    for log in rerank_logs:
        model = log.get("reranking_module", "unknown")
        by_model[model].append(log)
    
    for model, logs in by_model.items():
        changed = sum(1 for log in logs if log.get("docs_changed", False))
        print(f"\n{model}:")
        print(f"  쿼리 수: {len(logs)}")
        print(f"  순서 변경: {changed} ({changed/len(logs)*100:.1f}%)")
        
        avg_time = sum(log.get("rerank_time", 0) for log in logs) / len(logs)
        print(f"  평균 ReRank 시간: {avg_time*1000:.2f}ms")
    
    # 권장사항
    print("\n\n[5] 권장사항")
    print("-" * 80)
    
    if queries_with_changes / total_queries < 0.3:
        print("⚠️  ReRank가 순서를 거의 바꾸지 않습니다 (< 30%)")
        print("   → 벡터 검색이 이미 정확하거나, ReRank 모델이 효과적이지 않습니다")
        print("   → ReRank 제거를 고려하세요")
    
    if len(docs_demoted) > len(docs_promoted):
        print("\n⚠️  순위 하락 문서가 더 많습니다")
        print("   → ReRank가 오히려 성능을 저하시킬 수 있습니다")
        print("   → 다른 ReRank 모델을 시도하거나 top_k 배수를 조정하세요")
    
    print("\n\n[6] 다음 단계")
    print("-" * 80)
    print("1. 상세 로그 확인:")
    print("   docker-compose logs backend | grep reranking_detailed")
    print("\n2. 특정 쿼리 분석:")
    print("   위의 '쿼리별 상세 분석'을 참고하여")
    print("   순위가 변한 문서가 실제로 관련있는지 확인")
    print("\n3. 다른 ReRank 모델 시도:")
    print("   - BGE → BM25")
    print("   - Qwen → BGE")
    print("   - cross_encoder 파라미터 조정")

def main():
    if len(sys.argv) < 2:
        print("사용법: python analyze_rerank_performance.py <log_file>")
        print("\n로그 수집 방법:")
        print("  docker-compose logs backend > backend_logs.txt")
        print("  python analyze_rerank_performance.py backend_logs.txt")
        sys.exit(1)
    
    log_file = Path(sys.argv[1])
    if not log_file.exists():
        print(f"❌ 로그 파일을 찾을 수 없습니다: {log_file}")
        sys.exit(1)
    
    analyze_rerank_impact(log_file)

if __name__ == "__main__":
    main()

