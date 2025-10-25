"""
API Routes 등록 확인 테스트
FastAPI 앱의 모든 라우트가 올바르게 등록되었는지 확인
"""
import sys
sys.path.insert(0, '.')

print("=" * 80)
print("API Routes 등록 확인")
print("=" * 80)

try:
    from app.main import app
    
    print("\n✓ FastAPI 앱 로드 성공\n")
    
    # 모든 라우트 추출
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            for method in route.methods:
                if method != "HEAD":  # HEAD는 제외
                    routes.append({
                        'method': method,
                        'path': route.path,
                        'name': route.name if hasattr(route, 'name') else 'N/A'
                    })
    
    # 카테고리별로 정리
    categories = {
        'Pipeline': [],
        'Query': [],
        'Evaluation': [],
        'RAG': [],
        'DataSource': [],
        'Dataset': [],
        'Other': []
    }
    
    for route in sorted(routes, key=lambda x: (x['path'], x['method'])):
        path = route['path']
        if '/pipelines' in path:
            categories['Pipeline'].append(route)
        elif '/query' in path:
            categories['Query'].append(route)
        elif '/evaluations' in path:
            categories['Evaluation'].append(route)
        elif '/rags' in path:
            categories['RAG'].append(route)
        elif '/datasources' in path:
            categories['DataSource'].append(route)
        elif '/datasets' in path:
            categories['Dataset'].append(route)
        else:
            categories['Other'].append(route)
    
    # 카테고리별 출력
    for category, cat_routes in categories.items():
        if cat_routes:
            print(f"[{category}] - {len(cat_routes)}개 엔드포인트")
            print("-" * 80)
            for route in cat_routes:
                print(f"  {route['method']:7s} {route['path']:50s} ({route['name']})")
            print()
    
    # 주요 엔드포인트 확인
    print("=" * 80)
    print("주요 엔드포인트 확인")
    print("=" * 80)
    
    required_endpoints = [
        ('POST', '/api/v1/pipelines'),
        ('GET', '/api/v1/pipelines'),
        ('GET', '/api/v1/pipelines/{pipeline_id}'),
        ('PATCH', '/api/v1/pipelines/{pipeline_id}'),
        ('DELETE', '/api/v1/pipelines/{pipeline_id}'),
        ('POST', '/api/v1/query/search'),
        ('POST', '/api/v1/query/answer'),
        ('POST', '/api/v1/evaluations/run'),
        ('POST', '/api/v1/evaluations/compare'),
        ('GET', '/api/v1/evaluations'),
        ('GET', '/api/v1/evaluations/{evaluation_id}'),
    ]
    
    all_paths = [(r['method'], r['path']) for r in routes]
    
    for method, path in required_endpoints:
        if (method, path) in all_paths:
            print(f"  ✓ {method:7s} {path}")
        else:
            print(f"  ✗ {method:7s} {path} - 없음!")
    
    print("\n" + "=" * 80)
    print("✅ API Routes 검증 완료!")
    print(f"총 {len(routes)}개 엔드포인트 등록됨")
    print("=" * 80)

except Exception as e:
    print(f"\n✗ API 로드 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

