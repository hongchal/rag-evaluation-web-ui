"""
테스트용 PDF 생성 스크립트
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
import os

# PDF 파일 경로
pdf_path = "test_data/company_report.pdf"

# PDF 문서 생성
doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                        rightMargin=72, leftMargin=72,
                        topMargin=72, bottomMargin=18)

# 스토리 (콘텐츠)
story = []
styles = getSampleStyleSheet()

# 제목 스타일
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor='blue',
    spaceAfter=30,
    alignment=TA_CENTER
)

# 일반 텍스트 스타일
normal_style = styles['BodyText']
normal_style.alignment = TA_JUSTIFY

# 제목
title = Paragraph("2024년 AI 기술 동향 보고서", title_style)
story.append(title)
story.append(Spacer(1, 12))

# 개요
overview = Paragraph(
    "<b>Executive Summary</b><br/><br/>"
    "본 보고서는 2024년 현재 인공지능 기술의 주요 동향과 "
    "산업 적용 사례를 분석합니다. 특히 RAG(Retrieval-Augmented Generation) "
    "시스템의 발전과 대규모 언어 모델(LLM)의 실용화에 초점을 맞추었습니다.",
    styles['BodyText']
)
story.append(overview)
story.append(Spacer(1, 20))

# 섹션 1
section1_title = Paragraph("<b>1. 대규모 언어 모델의 진화</b>", styles['Heading2'])
story.append(section1_title)
story.append(Spacer(1, 12))

section1_content = Paragraph(
    "2024년에는 GPT-4, Claude 3, Gemini 1.5 등 차세대 언어 모델들이 "
    "상용화되었습니다. 이러한 모델들은 다음과 같은 특징을 보입니다:<br/><br/>"
    "• 컨텍스트 윈도우 확장: 최대 1M 토큰까지 처리 가능<br/>"
    "• 멀티모달 지원: 텍스트, 이미지, 오디오 통합 처리<br/>"
    "• 추론 능력 향상: 복잡한 수학 및 논리 문제 해결<br/>"
    "• 코드 생성: 프로그래밍 보조 기능 강화<br/><br/>"
    "특히 주목할 만한 것은 환각(Hallucination) 현상이 크게 감소했다는 점입니다. "
    "이는 RAG 시스템과의 결합으로 더욱 신뢰할 수 있는 답변 생성이 가능해졌습니다.",
    styles['BodyText']
)
story.append(section1_content)
story.append(Spacer(1, 20))

# 섹션 2
section2_title = Paragraph("<b>2. RAG 시스템의 발전</b>", styles['Heading2'])
story.append(section2_title)
story.append(Spacer(1, 12))

section2_content = Paragraph(
    "RAG(Retrieval-Augmented Generation)는 정보 검색과 생성을 결합한 "
    "혁신적인 아키텍처입니다. 2024년의 주요 발전 사항:<br/><br/>"
    "<b>2.1 하이브리드 검색</b><br/>"
    "Dense 벡터 검색과 Sparse 벡터 검색을 결합하여 검색 정확도가 크게 향상되었습니다. "
    "BGE-M3, Cohere Embed 등의 모델이 하이브리드 임베딩을 지원합니다.<br/><br/>"
    "<b>2.2 청킹 전략</b><br/>"
    "문서를 효과적으로 분할하는 다양한 청킹 전략이 개발되었습니다:<br/>"
    "• Recursive Chunking: 재귀적 분할로 의미 단위 유지<br/>"
    "• Semantic Chunking: 의미 기반 분할<br/>"
    "• Late Chunking: 임베딩 후 분할로 컨텍스트 보존<br/><br/>"
    "<b>2.3 리랭킹</b><br/>"
    "Cross-Encoder 기반 리랭커가 검색 결과의 순위를 재조정하여 "
    "최종 답변의 품질을 향상시킵니다.",
    styles['BodyText']
)
story.append(section2_content)
story.append(Spacer(1, 20))

# 섹션 3
section3_title = Paragraph("<b>3. 벡터 데이터베이스</b>", styles['Heading2'])
story.append(section3_title)
story.append(Spacer(1, 12))

section3_content = Paragraph(
    "벡터 데이터베이스는 RAG 시스템의 핵심 인프라입니다. "
    "주요 솔루션들의 특징을 비교하면:<br/><br/>"
    "<b>Qdrant</b><br/>"
    "• Rust 기반 고성능 벡터 DB<br/>"
    "• 하이브리드 검색 지원 (Named Vectors)<br/>"
    "• 필터링 및 페이로드 검색 강화<br/>"
    "• 클러스터링 및 샤딩 지원<br/><br/>"
    "<b>Pinecone</b><br/>"
    "• 완전 관리형 클라우드 서비스<br/>"
    "• 자동 스케일링<br/>"
    "• 메타데이터 필터링<br/><br/>"
    "<b>Weaviate</b><br/>"
    "• GraphQL API 제공<br/>"
    "• 멀티모달 벡터 검색<br/>"
    "• 내장 모듈식 아키텍처",
    styles['BodyText']
)
story.append(section3_content)
story.append(PageBreak())

# 섹션 4
section4_title = Paragraph("<b>4. 실제 적용 사례</b>", styles['Heading2'])
story.append(section4_title)
story.append(Spacer(1, 12))

section4_content = Paragraph(
    "<b>4.1 고객 지원 챗봇</b><br/>"
    "대형 e-커머스 기업들이 RAG 기반 챗봇을 도입하여 고객 문의에 "
    "정확하고 신속하게 대응하고 있습니다. 실시간으로 제품 정보, "
    "배송 상태, 반품 정책 등을 검색하여 제공합니다.<br/><br/>"
    "<b>4.2 법률 문서 분석</b><br/>"
    "로펌에서는 방대한 판례와 법률 문서를 RAG 시스템으로 검색하여 "
    "변호사의 업무 효율을 크게 향상시켰습니다.<br/><br/>"
    "<b>4.3 의료 정보 시스템</b><br/>"
    "의료 기관에서 환자 기록, 논문, 임상 가이드라인을 통합 검색하여 "
    "의사의 진단과 치료 결정을 지원합니다.<br/><br/>"
    "<b>4.4 내부 지식 관리</b><br/>"
    "기업들이 사내 문서, 위키, 이메일 등을 RAG 시스템에 통합하여 "
    "직원들의 정보 접근성을 개선하고 있습니다.",
    styles['BodyText']
)
story.append(section4_content)
story.append(Spacer(1, 20))

# 섹션 5
section5_title = Paragraph("<b>5. 성능 평가 방법론</b>", styles['Heading2'])
story.append(section5_title)
story.append(Spacer(1, 12))

section5_content = Paragraph(
    "RAG 시스템의 성능을 정량적으로 평가하기 위한 메트릭들:<br/><br/>"
    "<b>검색 성능 메트릭</b><br/>"
    "• Precision@K: 상위 K개 결과 중 관련 문서 비율<br/>"
    "• Recall@K: 전체 관련 문서 중 검색된 비율<br/>"
    "• NDCG@K: 순위를 고려한 정규화된 할인 누적 이득<br/>"
    "• MRR: 첫 번째 관련 문서의 평균 역순위<br/>"
    "• Hit Rate: 관련 문서가 검색되었는지 여부<br/><br/>"
    "<b>생성 품질 메트릭</b><br/>"
    "• BLEU: 참조 답변과의 n-gram 유사도<br/>"
    "• ROUGE: 요약 품질 평가<br/>"
    "• BERTScore: 의미적 유사도<br/>"
    "• Human Evaluation: 전문가 평가<br/><br/>"
    "최근에는 LLM-as-a-Judge 방식으로 GPT-4 등을 평가자로 활용하는 "
    "방법도 널리 사용되고 있습니다.",
    styles['BodyText']
)
story.append(section5_content)
story.append(Spacer(1, 20))

# 결론
conclusion_title = Paragraph("<b>6. 결론 및 전망</b>", styles['Heading2'])
story.append(conclusion_title)
story.append(Spacer(1, 12))

conclusion_content = Paragraph(
    "2024년 AI 기술은 실용화 단계에 본격 진입했습니다. "
    "특히 RAG 시스템은 환각 문제를 해결하고 정확한 정보 제공이 가능한 "
    "핵심 기술로 자리잡았습니다.<br/><br/>"
    "향후 전망:<br/>"
    "• 멀티모달 RAG: 이미지, 비디오까지 통합 검색<br/>"
    "• 실시간 업데이트: 동적 지식 베이스<br/>"
    "• 개인화: 사용자별 맞춤 검색 및 생성<br/>"
    "• 다국어 지원: 언어 장벽 없는 정보 접근<br/><br/>"
    "RAG 기술의 발전은 계속될 것이며, 더욱 다양한 산업 분야에서 "
    "혁신을 가져올 것으로 기대됩니다.",
    styles['BodyText']
)
story.append(conclusion_content)

# PDF 생성
try:
    doc.build(story)
    print(f"✓ PDF 파일 생성 완료: {pdf_path}")
    print(f"  파일 크기: {os.path.getsize(pdf_path)} bytes")
except Exception as e:
    print(f"✗ PDF 생성 실패: {e}")
    import traceback
    traceback.print_exc()

