"""
fpdf2를 사용한 테스트 PDF 생성
"""
from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, '2024 AI Technology Trends Report', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(4)
    
    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 5, body)
        self.ln()

# PDF 생성
pdf = PDF()
pdf.add_page()

# 내용 추가
pdf.chapter_title('Executive Summary')
pdf.chapter_body(
    'This report analyzes major trends in artificial intelligence technology as of 2024. '
    'It focuses on the development of RAG (Retrieval-Augmented Generation) systems and '
    'the practical application of Large Language Models (LLMs).'
)

pdf.chapter_title('1. Evolution of Large Language Models')
pdf.chapter_body(
    'In 2024, next-generation language models such as GPT-4, Claude 3, and Gemini 1.5 have been commercialized. '
    'These models exhibit the following characteristics:\n\n'
    '- Extended Context Window: Processing up to 1M tokens\n'
    '- Multimodal Support: Integrated processing of text, images, and audio\n'
    '- Enhanced Reasoning: Solving complex mathematical and logical problems\n'
    '- Code Generation: Strengthened programming assistance\n\n'
    'Notably, hallucination phenomena have significantly decreased. '
    'This enables more reliable answer generation through integration with RAG systems.'
)

pdf.chapter_title('2. Advancement of RAG Systems')
pdf.chapter_body(
    'RAG (Retrieval-Augmented Generation) is an innovative architecture combining information retrieval and generation. '
    'Key developments in 2024:\n\n'
    '2.1 Hybrid Search\n'
    'Search accuracy has greatly improved by combining Dense and Sparse vector searches. '
    'Models like BGE-M3 and Cohere Embed support hybrid embeddings.\n\n'
    '2.2 Chunking Strategies\n'
    'Various strategies for effective document segmentation:\n'
    '- Recursive Chunking: Maintains semantic units through recursive splitting\n'
    '- Semantic Chunking: Meaning-based segmentation\n'
    '- Late Chunking: Preserves context by splitting after embedding\n\n'
    '2.3 Reranking\n'
    'Cross-Encoder based rerankers reorder search results to improve final answer quality.'
)

pdf.chapter_title('3. Vector Databases')
pdf.chapter_body(
    'Vector databases are the core infrastructure of RAG systems.\n\n'
    'Qdrant:\n'
    '- High-performance vector DB based on Rust\n'
    '- Hybrid search support (Named Vectors)\n'
    '- Enhanced filtering and payload search\n'
    '- Clustering and sharding support\n\n'
    'Pinecone:\n'
    '- Fully managed cloud service\n'
    '- Auto-scaling\n'
    '- Metadata filtering\n\n'
    'Weaviate:\n'
    '- GraphQL API provision\n'
    '- Multimodal vector search\n'
    '- Built-in modular architecture'
)

pdf.add_page()

pdf.chapter_title('4. Real-World Applications')
pdf.chapter_body(
    '4.1 Customer Support Chatbots\n'
    'Major e-commerce companies have adopted RAG-based chatbots to respond accurately and promptly to customer inquiries.\n\n'
    '4.2 Legal Document Analysis\n'
    'Law firms search vast case laws and legal documents with RAG systems, significantly improving lawyer efficiency.\n\n'
    '4.3 Medical Information Systems\n'
    'Healthcare institutions support doctors\' diagnoses by integrating patient records, papers, and clinical guidelines.\n\n'
    '4.4 Internal Knowledge Management\n'
    'Companies integrate internal documents, wikis, and emails into RAG systems to improve information accessibility.'
)

pdf.chapter_title('5. Performance Evaluation Methodology')
pdf.chapter_body(
    'Metrics for quantitatively evaluating RAG system performance:\n\n'
    'Retrieval Performance Metrics:\n'
    '- Precision@K: Proportion of relevant documents in top K results\n'
    '- Recall@K: Proportion of retrieved among all relevant documents\n'
    '- NDCG@K: Normalized Discounted Cumulative Gain considering ranking\n'
    '- MRR: Mean Reciprocal Rank of first relevant document\n'
    '- Hit Rate: Whether relevant documents were retrieved\n\n'
    'Generation Quality Metrics:\n'
    '- BLEU: N-gram similarity with reference answers\n'
    '- ROUGE: Summary quality evaluation\n'
    '- BERTScore: Semantic similarity\n'
    '- Human Evaluation: Expert assessment\n\n'
    'Recently, LLM-as-a-Judge methods using GPT-4 as evaluators are also widely used.'
)

pdf.chapter_title('6. Conclusion and Outlook')
pdf.chapter_body(
    'AI technology in 2024 has entered the practical application phase. '
    'RAG systems have become core technologies capable of solving hallucination problems and providing accurate information.\n\n'
    'Future Outlook:\n'
    '- Multimodal RAG: Integrated search including images and videos\n'
    '- Real-time Updates: Dynamic knowledge bases\n'
    '- Personalization: Customized search and generation per user\n'
    '- Multilingual Support: Information access without language barriers\n\n'
    'The development of RAG technology will continue, expected to bring innovation to various industries.'
)

# 파일 저장
output_path = 'test_data/ai_report.pdf'
pdf.output(output_path)

# 확인
if os.path.exists(output_path):
    file_size = os.path.getsize(output_path)
    print(f"✓ PDF 파일 생성 완료: {output_path}")
    print(f"  파일 크기: {file_size:,} bytes ({file_size/1024:.1f} KB)")
else:
    print(f"✗ PDF 파일 생성 실패")

