# Dataset Preparation Guide

테스트용 데이터셋을 구축하기 위한 가이드입니다.

## 📦 필수 패키지 설치

```bash
# 데이터셋 다운로드를 위한 패키지
pip install datasets requests

# BEIR 벤치마크 (선택)
pip install beir
```

## 🎯 지원하는 데이터셋

### 1. FRAMES (Google)
- **설명**: Multi-hop reasoning을 위한 RAG 벤치마크
- **크기**: 824 question-answer pairs
- **특징**: Wikipedia 기반, 복잡한 추론 필요
- **추천**: RAG 평가에 가장 적합

### 2. BEIR Benchmark
- **SciFact**: 과학 논문 검증 (5K docs)
- **NFCorpus**: 영양학 (3.6K docs)
- **HotpotQA**: Multi-hop QA (5M docs)
- **FiQA**: 금융 QA (57K docs)
- **TREC-COVID**: COVID-19 연구 (171K docs)

### 3. Wikipedia
- **설명**: Wikipedia 문서 + 자동 생성 쿼리
- **크기**: 사용자 정의 (1K~100K)
- **특징**: 빠른 테스트용

### 4. MS MARCO
- **설명**: Microsoft의 QA 데이터셋
- **크기**: 사용자 정의 (10K~1M)
- **특징**: 실제 검색 쿼리 기반

---

## 🚀 사용 방법

### FRAMES 데이터셋 다운로드

#### 빠른 테스트 (Wikipedia 내용 없이)
```bash
cd /Users/johongcheol/rag-evaluation-web-ui

# 100개 샘플, placeholder 내용 (자동 DB 등록)
python backend/scripts/download_frames.py --sample --no-fetch-wikipedia
```

#### 완전한 데이터셋 (Wikipedia 내용 포함) ⭐ 추천
```bash
# 전체 데이터셋 (824 queries) + Wikipedia 내용 (자동 DB 등록)
python backend/scripts/download_frames.py --fetch-wikipedia

# 200개 쿼리 + Wikipedia 내용 (자동 DB 등록)
python backend/scripts/download_frames.py --max-queries 200 --fetch-wikipedia

# 커스텀 출력 경로
python backend/scripts/download_frames.py \
    --fetch-wikipedia \
    --max-queries 100 \
    --output backend/datasets/frames_100.json

# DB 등록 건너뛰기
python backend/scripts/download_frames.py --fetch-wikipedia --no-register
```

**⚠️ 주의**: `--fetch-wikipedia` 옵션은 실제 Wikipedia API를 호출하므로:
- 시간이 오래 걸립니다 (100 queries ≈ 2-3분)
- Rate limiting이 적용됩니다 (0.1초/요청)
- 하지만 **실제 RAG 평가를 위해서는 필수**입니다!

**✨ 자동 DB 등록**: 다운로드한 데이터셋은 자동으로 데이터베이스에 등록됩니다!

---

### BEIR 데이터셋 다운로드

#### 개별 다운로드
```bash
cd /Users/johongcheol/rag-evaluation-web-ui

# SciFact (작은 데이터셋, 테스트용) - 자동 DB 등록
python backend/scripts/prepare_dataset.py beir --name scifact

# HotpotQA (샘플링 필요, 너무 큼) - 자동 DB 등록
python backend/scripts/prepare_dataset.py beir --name hotpotqa --sample 1000

# FiQA (금융 QA) - 자동 DB 등록
python backend/scripts/prepare_dataset.py beir --name fiqa

# DB 등록 건너뛰기
python backend/scripts/prepare_dataset.py beir --name scifact --no-register
```

#### 모든 BEIR 데이터셋 한번에 다운로드 ⭐ 새로운 기능!
```bash
# 모든 BEIR 데이터셋 다운로드 및 자동 DB 등록
python backend/scripts/prepare_dataset.py download-all

# DB 등록 건너뛰기
python backend/scripts/prepare_dataset.py download-all --no-register
```

**다운로드되는 데이터셋:**
- scifact (5K docs)
- nfcorpus (3.6K docs)
- hotpotqa (5M docs)
- fiqa (57K docs)
- trec-covid (171K docs)

#### 사용 가능한 데이터셋 목록
```bash
python backend/scripts/prepare_dataset.py list
```

---

### Wikipedia 데이터셋 생성

```bash
# 1000개 문서 + 2개 쿼리/문서 (자동 DB 등록)
python backend/scripts/prepare_dataset.py wikipedia --size 1000

# 10000개 문서 + 3개 쿼리/문서 (자동 DB 등록)
python backend/scripts/prepare_dataset.py wikipedia --size 10000 --queries-per-doc 3

# 커스텀 출력 경로
python backend/scripts/prepare_dataset.py wikipedia \
    --size 5000 \
    --queries-per-doc 2 \
    --output backend/datasets/wiki_5k.json

# DB 등록 건너뛰기
python backend/scripts/prepare_dataset.py wikipedia --size 1000 --no-register
```

---

### MS MARCO 데이터셋 다운로드

```bash
# 10K passages (기본) - 자동 DB 등록
python backend/scripts/prepare_dataset.py msmarco --size 10000

# 50K passages - 자동 DB 등록
python backend/scripts/prepare_dataset.py msmarco --size 50000

# DB 등록 건너뛰기
python backend/scripts/prepare_dataset.py msmarco --size 10000 --no-register
```

---

### 데이터셋 검증

```bash
# 다운로드한 데이터셋 검증
python backend/scripts/prepare_dataset.py verify --dataset backend/datasets/frames_eval.json

# 통계 출력:
# - 문서/쿼리 개수
# - 문서 길이 분포
# - 쿼리 난이도 분포
# - 쿼리 타입 분포
# - 관련 문서 수
```

---

### 데이터셋 관리 (DB)

#### 등록된 데이터셋 목록 확인
```bash
# 데이터베이스에 등록된 모든 데이터셋 확인
python backend/scripts/dataset_registry.py list
```

#### 수동으로 데이터셋 등록
```bash
# 특정 데이터셋 파일을 수동으로 등록
python backend/scripts/dataset_registry.py register backend/datasets/frames_eval.json
```

#### 모든 데이터셋 자동 등록
```bash
# datasets 디렉토리의 모든 JSON 파일을 자동 등록
python backend/scripts/dataset_registry.py auto-register

# 다른 디렉토리 지정
python backend/scripts/dataset_registry.py auto-register --dir /path/to/datasets
```

---

## 📊 데이터셋 형식

생성된 JSON 파일은 다음 형식을 따릅니다:

```json
{
  "name": "FRAMES-RAG",
  "description": "Google FRAMES benchmark for RAG evaluation",
  "documents": [
    {
      "id": "frames_q0_doc0",
      "content": "Wikipedia article content...",
      "title": "Article Title",
      "metadata": {
        "source": "frames",
        "wikipedia_url": "https://en.wikipedia.org/wiki/...",
        "question_idx": 0,
        "content_length": 1234
      }
    }
  ],
  "queries": [
    {
      "query": "What is the capital of France?",
      "relevant_doc_ids": ["frames_q0_doc0", "frames_q0_doc1"],
      "expected_answer": "Paris",
      "difficulty": "hard",
      "query_type": "multi-hop",
      "metadata": {
        "source": "frames",
        "question_idx": 0,
        "reasoning_type": "multi-hop",
        "num_wikipedia_links": 2
      }
    }
  ],
  "metadata": {
    "source": "google/frames-benchmark",
    "version": "2024",
    "total_examples": 824,
    "converted_queries": 820,
    "converted_documents": 3456,
    "fetched_wikipedia": true
  }
}
```

---

## 💡 추천 워크플로우

### 1. 빠른 테스트 (개발 중)
```bash
# 작은 샘플로 빠르게 테스트 (자동 DB 등록)
python backend/scripts/download_frames.py --sample --no-fetch-wikipedia
# → backend/datasets/frames_eval.json (100 queries, placeholder content)
# → 자동으로 DB에 등록됨!
```

### 2. 실제 평가 (프로덕션)
```bash
# Wikipedia 내용을 포함한 완전한 데이터셋 (자동 DB 등록)
python backend/scripts/download_frames.py --fetch-wikipedia
# → backend/datasets/frames_eval.json (824 queries, real Wikipedia content)
# → 자동으로 DB에 등록됨!
```

### 3. 다양한 데이터셋으로 벤치마킹 (모두 자동 DB 등록)
```bash
# FRAMES (multi-hop reasoning)
python backend/scripts/download_frames.py --fetch-wikipedia --max-queries 200

# 모든 BEIR 데이터셋 한번에 다운로드
python backend/scripts/prepare_dataset.py download-all

# 또는 개별 다운로드
python backend/scripts/prepare_dataset.py beir --name scifact
python backend/scripts/prepare_dataset.py beir --name fiqa

# Wikipedia (general knowledge)
python backend/scripts/prepare_dataset.py wikipedia --size 1000

# 등록된 데이터셋 확인
python backend/scripts/dataset_registry.py list
```

### 4. 기존 데이터셋 일괄 등록
```bash
# datasets 디렉토리의 모든 JSON 파일을 DB에 등록
python backend/scripts/dataset_registry.py auto-register
```

---

## 🔧 API를 통한 데이터셋 사용

데이터셋이 자동으로 DB에 등록되므로, 바로 API를 통해 사용할 수 있습니다:

```bash
# 1. 등록된 데이터셋 목록 확인
curl http://localhost:8001/api/datasets

# 2. RAG 설정 생성
curl -X POST http://localhost:8001/api/rags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My RAG",
    "chunking": {"module": "recursive", "params": {"chunk_size": 512}},
    "embedding": {"module": "bge_m3", "params": {}},
    "reranking": {"module": "cross_encoder", "params": {}}
  }'

# 3. 평가 실행 (dataset_id는 위에서 확인한 ID 사용)
curl -X POST http://localhost:8001/api/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "rag_id": 1,
    "dataset_id": 1,
    "metrics": ["precision", "recall", "mrr", "ndcg"]
  }'

# 4. 평가 결과 확인
curl http://localhost:8001/api/evaluations/1
```

---

## 📁 파일 구조

```
backend/
├── datasets/                    # 다운로드된 데이터셋
│   ├── frames_eval.json        # FRAMES 데이터셋
│   ├── beir_scifact_eval.json  # BEIR SciFact
│   ├── wikipedia_1000_eval.json # Wikipedia
│   └── .beir/                  # BEIR 캐시
├── scripts/
│   ├── download_frames.py      # FRAMES 다운로더
│   └── prepare_dataset.py      # 범용 데이터셋 준비 도구
```

---

## ⚡ 성능 팁

### FRAMES 다운로드 최적화
- **빠른 테스트**: `--no-fetch-wikipedia` (초 단위)
- **실제 평가**: `--fetch-wikipedia` (분 단위, 하지만 필수!)
- **샘플링**: `--sample` 또는 `--max-queries 100` (개발 중)

### BEIR 다운로드 최적화
- **작은 데이터셋**: scifact, nfcorpus (빠름)
- **큰 데이터셋**: hotpotqa, trec-covid (샘플링 필수)
- **샘플링**: `--sample 1000` (처음 1000개만)

### Wikipedia 다운로드 최적화
- **테스트**: `--size 1000` (1-2분)
- **중간**: `--size 10000` (10-15분)
- **대규모**: `--size 100000` (1-2시간)

---

## 🐛 문제 해결

### "datasets library not installed"
```bash
pip install datasets
```

### "BEIR not installed"
```bash
pip install beir
```

### "Failed to fetch Wikipedia"
- Rate limiting: 잠시 기다렸다가 재시도
- 네트워크 문제: 인터넷 연결 확인
- API 오류: `--no-fetch-wikipedia` 사용 (placeholder)

### "Dataset verification failed"
```bash
# 데이터셋 검증 실행
python backend/scripts/prepare_dataset.py verify --dataset backend/datasets/frames_eval.json

# 문제가 있으면 재다운로드
```

---

## 📚 참고 자료

- **FRAMES**: https://arxiv.org/abs/2409.12941
- **BEIR**: https://github.com/beir-cellar/beir
- **MS MARCO**: https://microsoft.github.io/msmarco/
- **Wikipedia Dataset**: https://huggingface.co/datasets/wikipedia

---

## 🎯 다음 단계

1. ✅ 데이터셋 다운로드 (자동 DB 등록)
2. ✅ 데이터셋 검증
3. ✅ 데이터베이스에 자동 등록됨!
4. → RAG 설정 생성 (API)
5. → 평가 실행 (API)
6. → 결과 분석

## 📝 요약

### 주요 명령어

```bash
# FRAMES 다운로드 (자동 DB 등록)
python backend/scripts/download_frames.py --fetch-wikipedia

# 모든 BEIR 데이터셋 다운로드 (자동 DB 등록)
python backend/scripts/prepare_dataset.py download-all

# 등록된 데이터셋 확인
python backend/scripts/dataset_registry.py list

# 기존 데이터셋 일괄 등록
python backend/scripts/dataset_registry.py auto-register
```

### 자동 DB 등록 기능 ✨

- 모든 다운로드 스크립트는 **기본적으로 데이터셋을 DB에 자동 등록**합니다
- `--no-register` 플래그로 자동 등록을 건너뛸 수 있습니다
- 이미 등록된 데이터셋은 자동으로 업데이트됩니다
- `dataset_registry.py`로 수동 관리도 가능합니다

Happy Evaluating! 🚀

