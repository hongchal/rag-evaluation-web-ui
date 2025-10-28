"""Claude-based evaluation analysis service."""

from typing import List, Dict, Any
import structlog
from anthropic import Anthropic

from app.core.config import settings

logger = structlog.get_logger(__name__)


class ClaudeAnalysisService:
    """Service for generating AI-powered evaluation analysis using Claude."""
    
    def __init__(self):
        """Initialize Claude client."""
        api_key = settings.anthropic_api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"  # Latest Claude model
    
    def analyze_evaluation_results(
        self,
        evaluation_name: str,
        metrics: List[Dict[str, Any]],
        dataset_name: str = None
    ) -> str:
        """
        Generate comprehensive analysis of evaluation results.
        
        Args:
            evaluation_name: Name of the evaluation
            metrics: List of pipeline metrics
            dataset_name: Optional dataset name
            
        Returns:
            Analysis text in markdown format
        """
        try:
            # Build context for Claude
            context = self._build_context(evaluation_name, metrics, dataset_name)
            
            # Create prompt
            prompt = f"""당신은 RAG (Retrieval-Augmented Generation) 시스템 평가 전문가입니다.

다음 평가 결과를 분석하고 종합적인 의견을 제공해주세요:

{context}

다음 형식으로 분석해주세요:

## 📈 전체 성능 요약
- 전반적인 검색 성능 수준 평가
- 가장 높은 성능을 보인 파이프라인과 그 이유

## 🎯 파이프라인별 특징
- 각 파이프라인의 강점과 약점
- 지표별 성능 차이 분석

## 💡 개선 제안
- 성능 향상을 위한 구체적인 제안
- 각 파이프라인에 맞는 최적화 방향

## ⚖️ 종합 평가
- 전체적인 평가와 추천 파이프라인
- 사용 시나리오별 권장사항

한국어로 작성하되, 기술적이면서도 이해하기 쉽게 설명해주세요.
"""
            
            logger.info("requesting_claude_analysis", num_pipelines=len(metrics))
            
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more consistent analysis
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text from response
            analysis = message.content[0].text
            
            logger.info("claude_analysis_completed", response_length=len(analysis))
            
            return analysis
            
        except Exception as e:
            logger.error("claude_analysis_failed", error=str(e))
            raise
    
    def _build_context(
        self,
        evaluation_name: str,
        metrics: List[Dict[str, Any]],
        dataset_name: str = None
    ) -> str:
        """Build context string for Claude."""
        lines = [
            f"**평가 이름**: {evaluation_name}",
        ]
        
        if dataset_name:
            lines.append(f"**데이터셋**: {dataset_name}")
        
        lines.append(f"**평가 파이프라인 수**: {len(metrics)}")
        lines.append("")
        lines.append("### 파이프라인별 성능 지표:")
        lines.append("")
        
        for i, metric in enumerate(metrics, 1):
            pipeline_name = metric.get("pipeline_name", f"Pipeline #{metric.get('pipeline_id')}")
            lines.append(f"**{i}. {pipeline_name}**")
            lines.append(f"- NDCG@10: {metric.get('ndcg_at_k', 0) * 100:.1f}%")
            lines.append(f"- MRR (Mean Reciprocal Rank): {metric.get('mrr', 0) * 100:.1f}%")
            lines.append(f"- Recall@10: {metric.get('recall_at_k', 0) * 100:.1f}%")
            lines.append(f"- Precision@10: {metric.get('precision_at_k', 0) * 100:.1f}%")
            lines.append(f"- Hit Rate: {metric.get('hit_rate', 0) * 100:.1f}%")
            lines.append(f"- MAP (Mean Average Precision): {metric.get('map_score', 0) * 100:.1f}%")
            
            # Add timing info if available
            if metric.get('retrieval_time'):
                lines.append(f"- 검색 시간: {metric.get('retrieval_time'):.3f}초")
            if metric.get('chunking_time') and metric.get('chunking_time') > 0:
                lines.append(f"- 청킹 시간: {metric.get('chunking_time'):.3f}초")
            if metric.get('embedding_time') and metric.get('embedding_time') > 0:
                lines.append(f"- 임베딩 시간: {metric.get('embedding_time'):.3f}초")
            
            if metric.get('num_chunks'):
                lines.append(f"- 총 청크 수: {metric.get('num_chunks')}")
            
            lines.append("")
        
        return "\n".join(lines)

