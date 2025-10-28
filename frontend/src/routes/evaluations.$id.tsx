import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type Evaluation } from '../lib/api'

export const Route = createFileRoute('/evaluations/$id')({
  component: EvaluationResult,
})

function EvaluationResult() {
  const { id } = Route.useParams()
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<string | null>(null)
  const [analyzingStatus, setAnalyzingStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

  useEffect(() => {
    loadEvaluation()
    
    // Poll for status if evaluation is running
    const interval = setInterval(() => {
      if (evaluation?.status === 'running' || evaluation?.status === 'pending') {
        loadEvaluation()
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [id, evaluation?.status])

  const loadEvaluation = async () => {
    try {
      setLoading(true)
      const data = await api.getEvaluation(Number(id))
      setEvaluation(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load evaluation')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async () => {
    try {
      await api.cancelEvaluation(Number(id))
      await loadEvaluation()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to cancel evaluation')
    }
  }

  const handleAnalyze = async () => {
    try {
      setAnalyzingStatus('loading')
      const result = await api.analyzeEvaluation(Number(id))
      setAnalysis(result.analysis)
      setAnalyzingStatus('success')
    } catch (err) {
      console.error('Failed to generate analysis:', err)
      setAnalyzingStatus('error')
      alert(err instanceof Error ? err.message : 'Failed to generate analysis')
    }
  }

  if (loading && !evaluation) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    )
  }

  if (!evaluation) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">Evaluation not found</div>
      </div>
    )
  }

  // Use metrics from API response (supports multiple pipelines)
  const metrics = evaluation.metrics || []
  const hasResults = metrics.length > 0

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">{evaluation.name}</h1>
        {evaluation.description && (
          <p className="text-gray-600">{evaluation.description}</p>
        )}
      </div>

      {/* Status */}
      <div className="bg-white shadow rounded-lg p-6 mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold mb-2">Status</h2>
            <div className="flex items-center space-x-4">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                evaluation.status === 'completed' ? 'bg-green-100 text-green-800' :
                evaluation.status === 'running' ? 'bg-blue-100 text-blue-800' :
                evaluation.status === 'failed' ? 'bg-red-100 text-red-800' :
                evaluation.status === 'cancelled' ? 'bg-gray-100 text-gray-800' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                {evaluation.status.toUpperCase()}
              </span>
              {(evaluation.status === 'running' || evaluation.status === 'pending') && (
                <span className="text-gray-600">{evaluation.progress.toFixed(1)}%</span>
              )}
            </div>
            {evaluation.current_step && (
              <p className="text-sm text-gray-500 mt-2">{evaluation.current_step}</p>
            )}
            {evaluation.error_message && (
              <p className="text-sm text-red-600 mt-2">{evaluation.error_message}</p>
            )}
          </div>

          {(evaluation.status === 'running' || evaluation.status === 'pending') && (
            <button
              onClick={handleCancel}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
            >
              Cancel
            </button>
          )}
        </div>

        {(evaluation.status === 'running' || evaluation.status === 'pending') && (
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${evaluation.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Metrics Explanation */}
      {hasResults && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">📊 평가 지표 설명</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h3 className="font-semibold text-gray-800 mb-2">NDCG@10 (Normalized Discounted Cumulative Gain)</h3>
              <p className="text-gray-600">검색 결과의 순위를 고려한 정확도. 상위 순위에 정답이 있을수록 높은 점수. (0~1, 높을수록 좋음)</p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-800 mb-2">MRR (Mean Reciprocal Rank)</h3>
              <p className="text-gray-600">첫 번째 정답 문서가 나타나는 순위의 역수. 정답이 빨리 나올수록 높은 점수. (0~1, 높을수록 좋음)</p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-800 mb-2">Recall@10</h3>
              <p className="text-gray-600">전체 정답 중 상위 10개 결과에 포함된 비율. 정답을 얼마나 많이 찾았는지 측정. (0~1, 높을수록 좋음)</p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-800 mb-2">Precision@10</h3>
              <p className="text-gray-600">상위 10개 결과 중 정답의 비율. 검색 결과의 정확성 측정. (0~1, 높을수록 좋음)</p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-800 mb-2">Hit Rate</h3>
              <p className="text-gray-600">상위 결과에 정답이 하나라도 포함되어 있으면 1, 없으면 0. 기본적인 검색 성공률. (0~1, 높을수록 좋음)</p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-800 mb-2">MAP (Mean Average Precision)</h3>
              <p className="text-gray-600">모든 정답 위치에서의 Precision 평균. 전체적인 검색 품질 측정. (0~1, 높을수록 좋음)</p>
            </div>
          </div>
        </div>
      )}

      {/* AI Analysis Section */}
      {hasResults && evaluation.status === 'completed' && (
        <div className="bg-white shadow rounded-lg overflow-hidden mb-8">
          <div className="flex items-center justify-between p-6 border-b border-gray-200" style={{ background: 'linear-gradient(to right, rgb(250 245 255), rgb(238 242 255))' }}>
            <h2 className="text-2xl font-semibold text-gray-900">🤖 AI 종합 분석 (Claude)</h2>
            <div className="flex items-center gap-2">
              {analyzingStatus === 'success' && (
                <button
                  onClick={() => {
                    setAnalysis(null)
                    setAnalyzingStatus('idle')
                  }}
                  className="px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                >
                  다시 생성
                </button>
              )}
              {analyzingStatus === 'idle' && (
                <button
                  onClick={handleAnalyze}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors shadow-sm"
                >
                  분석 생성
                </button>
              )}
            </div>
          </div>

          <div className="p-6">
            {analyzingStatus === 'loading' && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-10 w-10 border-3 border-purple-600 border-t-transparent"></div>
                <span className="ml-4 text-gray-600 text-lg">Claude가 결과를 분석하고 있습니다...</span>
              </div>
            )}

            {analyzingStatus === 'success' && analysis && (
              <div 
                className="max-h-[600px] overflow-y-auto pr-4 custom-scrollbar"
                style={{
                  scrollbarWidth: 'thin',
                  scrollbarColor: '#9333ea #f3f4f6'
                }}
              >
                <style>{`
                  .custom-scrollbar::-webkit-scrollbar {
                    width: 8px;
                  }
                  .custom-scrollbar::-webkit-scrollbar-track {
                    background: #f3f4f6;
                    border-radius: 4px;
                  }
                  .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #9333ea;
                    border-radius: 4px;
                  }
                  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #7e22ce;
                  }
                  .analysis-content h3 {
                    font-size: 1.25rem;
                    font-weight: 600;
                    margin-top: 1.5rem;
                    margin-bottom: 0.75rem;
                    color: #111827;
                    padding-bottom: 0.5rem;
                    border-bottom: 2px solid #e5e7eb;
                  }
                  .analysis-content h4 {
                    font-size: 1.1rem;
                    font-weight: 600;
                    margin-top: 1rem;
                    margin-bottom: 0.5rem;
                    color: #374151;
                  }
                  .analysis-content ul {
                    list-style-type: disc;
                    margin-left: 1.5rem;
                    margin-bottom: 1rem;
                  }
                  .analysis-content li {
                    margin-bottom: 0.5rem;
                    line-height: 1.6;
                    color: #4b5563;
                  }
                  .analysis-content p {
                    margin-bottom: 0.75rem;
                    line-height: 1.7;
                    color: #374151;
                  }
                  .analysis-content strong {
                    font-weight: 600;
                    color: #111827;
                  }
                `}</style>
                <div 
                  className="analysis-content text-gray-700 leading-relaxed"
                  dangerouslySetInnerHTML={{ 
                    __html: analysis
                      .split('\n\n')
                      .map(paragraph => {
                        // 제목 처리
                        if (paragraph.startsWith('## ')) {
                          return `<h3>${paragraph.substring(3)}</h3>`
                        }
                        if (paragraph.startsWith('### ')) {
                          return `<h4>${paragraph.substring(4)}</h4>`
                        }
                        // 리스트 처리
                        if (paragraph.includes('\n- ')) {
                          const items = paragraph.split('\n- ').filter(Boolean)
                          const firstItem = items[0]
                          if (firstItem.startsWith('- ')) {
                            return `<ul>${items.map(item => `<li>${item.replace(/^- /, '').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</li>`).join('')}</ul>`
                          } else {
                            return `<p>${firstItem}</p><ul>${items.slice(1).map(item => `<li>${item.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</li>`).join('')}</ul>`
                          }
                        }
                        // 일반 단락
                        return `<p>${paragraph.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</p>`
                      })
                      .join('')
                  }} 
                />
              </div>
            )}

            {analyzingStatus === 'error' && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
                <p className="font-medium">분석 생성 중 오류가 발생했습니다.</p>
                <p className="text-sm mt-1">ANTHROPIC_API_KEY 환경변수가 설정되어 있는지 확인해주세요.</p>
              </div>
            )}

            {analyzingStatus === 'idle' && (
              <div className="text-center py-12 text-gray-500">
                <p className="text-lg">Claude AI가 평가 결과를 종합적으로 분석합니다.</p>
                <p className="text-sm mt-2">위의 "분석 생성" 버튼을 클릭하세요.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Comparison Table (if multiple pipelines) */}
      {hasResults && metrics.length > 1 && (
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6">Pipeline Comparison</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Pipeline</th>
                  <th className="text-center py-3 px-2 font-semibold text-gray-700">NDCG@10</th>
                  <th className="text-center py-3 px-2 font-semibold text-gray-700">MRR</th>
                  <th className="text-center py-3 px-2 font-semibold text-gray-700">Recall@10</th>
                  <th className="text-center py-3 px-2 font-semibold text-gray-700">Precision@10</th>
                  <th className="text-center py-3 px-2 font-semibold text-gray-700">Hit Rate</th>
                  <th className="text-center py-3 px-2 font-semibold text-gray-700">Retrieval Time</th>
                  <th className="text-center py-3 px-2 font-semibold text-gray-700">Chunks</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((metric: any) => (
                  <tr key={metric.pipeline_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium text-gray-900">
                      {metric.pipeline_name || `Pipeline #${metric.pipeline_id}`}
                    </td>
                    <td className="text-center py-3 px-2">
                      <span className={`font-semibold ${
                        metric.ndcg_at_k >= 0.7 ? 'text-green-600' :
                        metric.ndcg_at_k >= 0.4 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {(metric.ndcg_at_k * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="text-center py-3 px-2">
                      <span className={`font-semibold ${
                        metric.mrr >= 0.7 ? 'text-green-600' :
                        metric.mrr >= 0.4 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {(metric.mrr * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="text-center py-3 px-2">
                      <span className={`font-semibold ${
                        metric.recall_at_k >= 0.7 ? 'text-green-600' :
                        metric.recall_at_k >= 0.4 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {(metric.recall_at_k * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="text-center py-3 px-2">
                      <span className={`font-semibold ${
                        metric.precision_at_k >= 0.7 ? 'text-green-600' :
                        metric.precision_at_k >= 0.4 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {(metric.precision_at_k * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="text-center py-3 px-2">
                      <span className={`font-semibold ${
                        metric.hit_rate >= 0.7 ? 'text-green-600' :
                        metric.hit_rate >= 0.4 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {(metric.hit_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="text-center py-3 px-2 text-gray-700">
                      {metric.retrieval_time?.toFixed(3) || 'N/A'}s
                    </td>
                    <td className="text-center py-3 px-2 text-gray-700">
                      {metric.num_chunks || 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Individual Pipeline Results */}
      {hasResults && metrics.map((metric: any) => (
        <div key={metric.pipeline_id} className="mb-8">
          {/* Pipeline Name */}
          <div className="mb-4">
            <h2 className="text-2xl font-semibold text-gray-900">
              {metric.pipeline_name || `Pipeline #${metric.pipeline_id}`}
            </h2>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
            <MetricCard title="NDCG@10" value={metric.ndcg_at_k} />
            <MetricCard title="MRR" value={metric.mrr} />
            <MetricCard title="Precision@10" value={metric.precision_at_k} />
            <MetricCard title="Recall@10" value={metric.recall_at_k} />
            <MetricCard title="Hit Rate" value={metric.hit_rate} />
            <MetricCard title="MAP" value={metric.map_score} />
          </div>

          {/* Performance */}
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">Performance</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <p className="text-sm text-gray-500">Chunking Time</p>
                <p className="text-xl font-semibold">
                  {metric.chunking_time && metric.chunking_time > 0 
                    ? `${metric.chunking_time.toFixed(3)}s` 
                    : <span className="text-gray-400">N/A</span>}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Embedding Time</p>
                <p className="text-xl font-semibold">
                  {metric.embedding_time && metric.embedding_time > 0 
                    ? `${metric.embedding_time.toFixed(3)}s` 
                    : <span className="text-gray-400">N/A</span>}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Retrieval Time</p>
                <p className="text-xl font-semibold">
                  {metric.retrieval_time && metric.retrieval_time > 0
                    ? `${metric.retrieval_time.toFixed(3)}s` 
                    : <span className="text-gray-400">N/A</span>}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Chunks</p>
                <p className="text-xl font-semibold">{metric.num_chunks || <span className="text-gray-400">N/A</span>}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Avg Chunk Size</p>
                <p className="text-xl font-semibold">
                  {metric.avg_chunk_size && metric.avg_chunk_size > 0 
                    ? metric.avg_chunk_size.toFixed(0) 
                    : <span className="text-gray-400">N/A</span>}
                </p>
              </div>
            </div>
          </div>
        </div>
      ))}

      {/* No results message */}
      {!hasResults && evaluation.status === 'completed' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 text-yellow-800">
          <p className="font-medium">No results available</p>
          <p className="text-sm mt-1">The evaluation completed but no metrics were generated.</p>
        </div>
      )}
    </div>
  )
}

function MetricCard({ title, value }: { title: string; value: number }) {
  const percentage = (value * 100).toFixed(1)
  const color = value >= 0.7 ? 'text-green-600' : value >= 0.4 ? 'text-yellow-600' : 'text-red-600'

  return (
    <div className="bg-white shadow rounded-lg p-4">
      <p className="text-sm text-gray-500 mb-1">{title}</p>
      <p className={`text-3xl font-bold ${color}`}>{percentage}%</p>
      <p className="text-xs text-gray-400 mt-1">{value.toFixed(4)}</p>
    </div>
  )
}

