"""
Routes 파일 정적 분석
실제 코드를 분석하여 API 엔드포인트 확인
"""
import re
from pathlib import Path

print("=" * 80)
print("API Routes 정적 분석")
print("=" * 80)

routes_dir = Path("app/api/routes")

# 분석할 파일들
route_files = {
    'pipelines.py': 'Pipeline API',
    'query.py': 'Query API',
    'evaluate.py': 'Evaluation API',
    'rags.py': 'RAG API',
    'datasources.py': 'DataSource API',
    'datasets.py': 'Dataset API',
}

all_endpoints = []

for filename, description in route_files.items():
    filepath = routes_dir / filename
    
    if not filepath.exists():
        print(f"\n⚠ {filename} 파일 없음")
        continue
    
    print(f"\n[{description}] - {filename}")
    print("-" * 80)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # @router 데코레이터 추출
    router_pattern = r'@router\.(get|post|put|patch|delete)\(([^)]+)\)'
    matches = re.findall(router_pattern, content, re.IGNORECASE | re.MULTILINE)
    
    for method, path_args in matches:
        # path 추출
        path_match = re.search(r'"([^"]+)"', path_args)
        if path_match:
            path = path_match.group(1)
            
            # prefix 추가 (router에서 확인)
            prefix_match = re.search(r'router\s*=\s*APIRouter\([^)]*prefix\s*=\s*"([^"]+)"', content)
            if prefix_match:
                prefix = prefix_match.group(1)
                full_path = prefix + path if path != "" else prefix
            else:
                full_path = path
            
            endpoint = {
                'method': method.upper(),
                'path': full_path,
                'file': filename
            }
            all_endpoints.append(endpoint)
            print(f"  {method.upper():7s} {full_path}")

# 주요 엔드포인트 확인
print("\n" + "=" * 80)
print("주요 엔드포인트 검증")
print("=" * 80)

expected_endpoints = {
    'Pipeline API': [
        ('POST', '/api/v1/pipelines'),
        ('GET', '/api/v1/pipelines'),
        ('GET', '/api/v1/pipelines/{pipeline_id}'),
        ('PATCH', '/api/v1/pipelines/{pipeline_id}'),
        ('DELETE', '/api/v1/pipelines/{pipeline_id}'),
    ],
    'Query API': [
        ('POST', '/api/v1/query/search'),
        ('POST', '/api/v1/query/answer'),
    ],
    'Evaluation API': [
        ('POST', '/api/v1/evaluations/run'),
        ('POST', '/api/v1/evaluations/compare'),
        ('GET', '/api/v1/evaluations'),
        ('GET', '/api/v1/evaluations/{evaluation_id}'),
        ('GET', '/api/v1/evaluations/{evaluation_id}/status'),
        ('POST', '/api/v1/evaluations/{evaluation_id}/cancel'),
        ('DELETE', '/api/v1/evaluations/{evaluation_id}'),
    ],
}

all_paths_set = set((e['method'], e['path']) for e in all_endpoints)

for api_name, endpoints in expected_endpoints.items():
    print(f"\n{api_name}:")
    for method, path in endpoints:
        if (method, path) in all_paths_set:
            print(f"  ✓ {method:7s} {path}")
        else:
            # 경로 변형 확인 (예: {id} vs {pipeline_id})
            found = False
            for actual_method, actual_path in all_paths_set:
                if method == actual_method and actual_path.endswith(path.split('/')[-1]):
                    print(f"  ✓ {method:7s} {path} (as {actual_path})")
                    found = True
                    break
            
            if not found:
                print(f"  ✗ {method:7s} {path} - 없음!")

# Request/Response 스키마 확인
print("\n" + "=" * 80)
print("Request/Response 스키마 사용 확인")
print("=" * 80)

schema_checks = {
    'pipelines.py': [
        ('NormalPipelineCreate', False),
        ('TestPipelineCreate', False),
        ('PipelineResponse', False),
        ('PipelineListResponse', False),
    ],
    'query.py': [
        ('SearchRequest', False),
        ('SearchResponse', False),
        ('pipeline_id', False),
    ],
    'evaluate.py': [
        ('EvaluationCreate', False),
        ('CompareRequest', False),
        ('EvaluationResponse', False),
        ('ComparisonResponse', False),
        ('pipeline_ids', False),
    ],
}

for filename, checks in schema_checks.items():
    filepath = routes_dir / filename
    
    if not filepath.exists():
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n{filename}:")
    for schema_name, _ in checks:
        if schema_name in content:
            print(f"  ✓ {schema_name} 사용됨")
        else:
            print(f"  ✗ {schema_name} 사용 안 됨")

# Service 메서드 호출 확인
print("\n" + "=" * 80)
print("Service 메서드 호출 확인")
print("=" * 80)

service_checks = {
    'pipelines.py': [
        'create_normal_pipeline',
        'create_test_pipeline',
        'get_pipeline',
        'list_pipelines',
        'update_pipeline',
        'delete_pipeline',
    ],
    'query.py': [
        'search',
        'answer',
    ],
    'evaluate.py': [
        'evaluate_pipelines',
        'compare_pipelines',
        'get_evaluation',
        'list_evaluations',
    ],
}

for filename, methods in service_checks.items():
    filepath = routes_dir / filename
    
    if not filepath.exists():
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n{filename}:")
    for method in methods:
        if f'.{method}(' in content or f'.{method} (' in content:
            print(f"  ✓ {method}() 호출됨")
        else:
            print(f"  ⚠ {method}() 호출 확인 안 됨")

print("\n" + "=" * 80)
print("✅ API Routes 정적 분석 완료!")
print(f"총 {len(all_endpoints)}개 엔드포인트 발견")
print("=" * 80)

