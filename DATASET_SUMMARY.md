# 데이터셋 다운로드 및 자동 등록 기능 ✨

## ✅ 구현 완료

### 1. 데이터셋 다운로드 스크립트

#### `backend/scripts/download_frames.py`
- **FRAMES 데이터셋** 다운로드 (Google)
- Wikipedia 내용 자동 fetch 옵션
- 샘플링 지원 (--sample, --max-queries)
- **자동 DB 등록** 기능 추가

#### `backend/scripts/prepare_dataset.py`
- **BEIR 벤치마크** 다운로드 (5개 데이터셋)
  - scifact, nfcorpus, hotpotqa, fiqa, trec-covid
- **Wikipedia** 데이터셋 생성
- **MS MARCO** 데이터셋 다운로드
- **모든 BEIR 데이터셋 한번에 다운로드** (`download-all` 명령)
- **자동 DB 등록** 기능 추가

#### `backend/scripts/dataset_registry.py` (새로 추가)
- 데이터셋을 데이터베이스에 등록
- 등록된 데이터셋 목록 조회
- 개별 등록 / 일괄 자동 등록 지원

---

## 🚀 주요 기능

### 자동 DB 등록
- 모든 다운로드 스크립트는 **기본적으로 데이터셋을 DB에 자동 등록**
- `--no-register` 플래그로 자동 등록 건너뛰기 가능
- 이미 등록된 데이터셋은 자동으로 업데이트
- 실패 시 수동 등록 방법 안내

### BEIR 전체 다운로드
```bash
# 모든 BEIR 데이터셋 한번에 다운로드 및 자동 DB 등록
python backend/scripts/prepare_dataset.py download-all
```

### 데이터셋 관리
```bash
# 등록된 데이터셋 목록
python backend/scripts/dataset_registry.py list

# 개별 등록
python backend/scripts/dataset_registry.py register backend/datasets/frames_eval.json

# 일괄 자동 등록
python backend/scripts/dataset_registry.py auto-register
```

---

## 📋 사용 예시

### FRAMES 다운로드 (자동 DB 등록)
```bash
# 빠른 테스트 (100 queries, placeholder)
python backend/scripts/download_frames.py --sample --no-fetch-wikipedia

# 완전한 데이터셋 (824 queries, real Wikipedia content)
python backend/scripts/download_frames.py --fetch-wikipedia

# DB 등록 건너뛰기
python backend/scripts/download_frames.py --fetch-wikipedia --no-register
```

### BEIR 다운로드 (자동 DB 등록)
```bash
# 개별 다운로드
python backend/scripts/prepare_dataset.py beir --name scifact

# 모든 BEIR 데이터셋 한번에
python backend/scripts/prepare_dataset.py download-all

# DB 등록 건너뛰기
python backend/scripts/prepare_dataset.py beir --name scifact --no-register
```

### Wikipedia 생성 (자동 DB 등록)
```bash
# 1000개 문서 + 2개 쿼리/문서
python backend/scripts/prepare_dataset.py wikipedia --size 1000

# DB 등록 건너뛰기
python backend/scripts/prepare_dataset.py wikipedia --size 1000 --no-register
```

### MS MARCO 다운로드 (자동 DB 등록)
```bash
# 10K passages
python backend/scripts/prepare_dataset.py msmarco --size 10000

# DB 등록 건너뛰기
python backend/scripts/prepare_dataset.py msmarco --size 10000 --no-register
```

---

## 📊 지원하는 데이터셋

### FRAMES (Google)
- **크기**: 824 question-answer pairs
- **특징**: Multi-hop reasoning, Wikipedia 기반
- **추천**: RAG 평가에 가장 적합

### BEIR Benchmark
1. **scifact** - 과학 논문 검증 (5K docs)
2. **nfcorpus** - 영양학 (3.6K docs)
3. **hotpotqa** - Multi-hop QA (5M docs)
4. **fiqa** - 금융 QA (57K docs)
5. **trec-covid** - COVID-19 연구 (171K docs)

### Wikipedia
- 사용자 정의 크기 (1K~100K)
- 자동 생성 쿼리

### MS MARCO
- 사용자 정의 크기 (10K~1M)
- 실제 검색 쿼리 기반

---

## 🔧 데이터베이스 스키마

```python
class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)  # 데이터셋 이름
    description = Column(Text)               # 설명
    dataset_uri = Column(Text)               # JSON 파일 경로
    num_queries = Column(Integer)            # 쿼리 개수
    num_documents = Column(Integer)          # 문서 개수
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

---

## 📁 파일 구조

```
backend/
├── datasets/                           # 다운로드된 데이터셋
│   ├── frames_eval.json               # FRAMES
│   ├── beir_scifact_eval.json         # BEIR SciFact
│   ├── beir_nfcorpus_eval.json        # BEIR NFCorpus
│   ├── beir_hotpotqa_eval.json        # BEIR HotpotQA
│   ├── beir_fiqa_eval.json            # BEIR FiQA
│   ├── beir_trec-covid_eval.json      # BEIR TREC-COVID
│   ├── wikipedia_1000_eval.json       # Wikipedia
│   ├── msmarco_10000_eval.json        # MS MARCO
│   └── .beir/                         # BEIR 캐시
├── scripts/
│   ├── download_frames.py             # FRAMES 다운로더
│   ├── prepare_dataset.py             # 범용 데이터셋 준비
│   └── dataset_registry.py            # DB 등록 관리 (새로 추가)
```

---

## 💡 워크플로우

### 1단계: 데이터셋 다운로드
```bash
# FRAMES
python backend/scripts/download_frames.py --fetch-wikipedia

# 모든 BEIR
python backend/scripts/prepare_dataset.py download-all

# Wikipedia
python backend/scripts/prepare_dataset.py wikipedia --size 1000
```

### 2단계: 등록 확인
```bash
# 자동으로 DB에 등록됨!
python backend/scripts/dataset_registry.py list
```

### 3단계: API로 사용
```bash
# 등록된 데이터셋 조회
curl http://localhost:8001/api/datasets

# RAG 설정 생성
curl -X POST http://localhost:8001/api/rags -d '{...}'

# 평가 실행
curl -X POST http://localhost:8001/api/evaluations -d '{
  "rag_id": 1,
  "dataset_id": 1
}'
```

---

## 🎯 핵심 개선사항

1. ✅ **자동 DB 등록**: 다운로드 후 수동 등록 불필요
2. ✅ **BEIR 전체 다운로드**: `download-all` 명령으로 한번에
3. ✅ **데이터셋 관리 도구**: `dataset_registry.py`로 편리한 관리
4. ✅ **중복 방지**: 이미 등록된 데이터셋은 자동 업데이트
5. ✅ **유연한 옵션**: `--no-register`로 자동 등록 건너뛰기 가능

---

## 📚 문서

- **DATASET_GUIDE.md**: 전체 가이드 (사용법, 예시, 문제 해결)
- **DATASET_SUMMARY.md**: 이 파일 (요약)
- **README.md**: 프로젝트 전체 README (업데이트됨)

Happy Evaluating! 🚀
