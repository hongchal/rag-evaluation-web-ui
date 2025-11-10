# PDF 전처리 프로세서 가이드

RAG 평가 시스템에서 3가지 PDF 전처리 프로세서를 선택할 수 있습니다.

## 📦 지원하는 프로세서

### 1. **PyPDF2** (빠른 처리)
- ⚡ **장점**: 가장 빠름, 가벼움
- ⚠️ **단점**: 기본적인 텍스트만 추출, 레이아웃 손실
- 🎯 **추천**: 단순 텍스트 문서, 빠른 테스트

### 2. **pdfplumber** (균형잡힌 선택) ⭐ 기본값
- ✅ **장점**: 좋은 품질, 테이블 인식
- 📊 **특징**: 페이지별 구분, 테이블 구조 보존
- 🎯 **추천**: 일반적인 문서, 테이블 포함 문서

### 3. **Docling** (최고 품질)
- 🚀 **장점**: 
  - 레이아웃 이해 (제목, 단락, 리스트 등)
  - 읽기 순서 보존
  - 테이블 구조 완벽 보존
  - 코드 블록 인식
  - 수식 추출
  - 이미지 분류
- 📝 **출력**: Markdown 형식 (구조화된 데이터)
- 🎯 **추천**: 복잡한 레이아웃, 학술 논문, 기술 문서

## 🚀 사용 방법

### 1. 파일 업로드 시 프로세서 선택

#### Python/Requests
```python
import requests

# Docling으로 처리
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8001/api/datasources/upload',
        files={'file': f},
        data={'processor_type': 'docling'}  # pypdf2, pdfplumber, docling
    )

print(response.json())
```

#### cURL
```bash
# PyPDF2 (빠름)
curl -X POST http://localhost:8001/api/datasources/upload \
  -F "file=@document.pdf" \
  -F "processor_type=pypdf2"

# pdfplumber (기본값)
curl -X POST http://localhost:8001/api/datasources/upload \
  -F "file=@document.pdf" \
  -F "processor_type=pdfplumber"

# Docling (고급)
curl -X POST http://localhost:8001/api/datasources/upload \
  -F "file=@document.pdf" \
  -F "processor_type=docling"
```

### 2. 프로세서 비교 API

같은 PDF를 3가지 방법으로 모두 처리하고 결과를 비교할 수 있습니다:

```bash
curl -X POST http://localhost:8001/api/datasources/compare-processors \
  -F "file=@document.pdf"
```

**응답 예시:**
```json
{
  "filename": "document.pdf",
  "processors": {
    "pypdf2": {
      "success": true,
      "content_length": 5000,
      "num_pages": 10
    },
    "pdfplumber": {
      "success": true,
      "content_length": 5500,
      "num_pages": 10
    },
    "docling": {
      "success": true,
      "content_length": 6000,
      "num_pages": 10,
      "metadata": {
        "num_tables": 3,
        "num_images": 5,
        "num_code_blocks": 2
      }
    }
  },
  "summary": {
    "fastest": "pypdf2",
    "most_content": "docling",
    "most_structured": "docling"
  }
}
```

## 📊 성능 비교

| 프로세서 | 속도 | 품질 | 테이블 | 레이아웃 | 구조화 |
|---------|------|------|--------|----------|--------|
| PyPDF2 | ⚡⚡⚡ | ⭐ | ❌ | ❌ | ❌ |
| pdfplumber | ⚡⚡ | ⭐⭐⭐ | ✅ | ⚠️ | ⚠️ |
| Docling | ⚡ | ⭐⭐⭐⭐⭐ | ✅ | ✅ | ✅ |

## 🎯 선택 가이드

### PyPDF2를 선택하세요:
- ✅ 단순한 텍스트 문서
- ✅ 빠른 처리가 중요할 때
- ✅ 레이아웃이 중요하지 않을 때

### pdfplumber를 선택하세요: (기본값)
- ✅ 일반적인 문서
- ✅ 테이블이 포함된 문서
- ✅ 속도와 품질의 균형이 필요할 때

### Docling을 선택하세요:
- ✅ 복잡한 레이아웃의 문서
- ✅ 학술 논문, 기술 문서
- ✅ 테이블, 코드, 수식이 많은 문서
- ✅ RAG 품질이 가장 중요할 때
- ✅ 구조화된 정보가 필요할 때

## 🔧 설치

Docling을 사용하려면 패키지가 설치되어 있어야 합니다:

```bash
pip install -r requirements.txt
```

`requirements.txt`에 이미 포함되어 있습니다:
```
docling==2.58.0
```

## 📝 RAG 평가에 미치는 영향

전처리 품질은 RAG 성능에 직접적인 영향을 미칩니다:

### PyPDF2
- 🔍 **검색 정확도**: 보통
- 📝 **컨텍스트 품질**: 낮음 (레이아웃 손실)
- 🎯 **추천 시나리오**: 빠른 프로토타이핑

### pdfplumber
- 🔍 **검색 정확도**: 좋음
- 📝 **컨텍스트 품질**: 좋음 (테이블 보존)
- 🎯 **추천 시나리오**: 대부분의 경우

### Docling
- 🔍 **검색 정확도**: 최고
- 📝 **컨텍스트 품질**: 최고 (완전한 구조 보존)
- 🎯 **추천 시나리오**: 프로덕션, 고품질 RAG

## 🧪 실험 예시

동일한 PDF로 3가지 프로세서를 비교하여 최적의 선택을 찾으세요:

```bash
# 1. 비교 API로 3가지 모두 테스트
curl -X POST http://localhost:8001/api/datasources/compare-processors \
  -F "file=@technical_paper.pdf" \
  -o comparison.json

# 2. 결과 확인
cat comparison.json | jq '.summary'

# 3. 최적의 프로세서로 업로드
curl -X POST http://localhost:8001/api/datasources/upload \
  -F "file=@technical_paper.pdf" \
  -F "processor_type=docling"
```

## 🔗 참고 자료

- **Docling GitHub**: https://github.com/docling-project/docling
- **Docling 문서**: https://docling-project.github.io/docling
- **Docling 논문**: https://arxiv.org/abs/2408.09869

---

Happy RAG Evaluation! 🚀

