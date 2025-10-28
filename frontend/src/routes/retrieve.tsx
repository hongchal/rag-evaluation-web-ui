import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type Pipeline, type SearchResponse, type EvaluationQuery } from '../lib/api'

export const Route = createFileRoute('/retrieve')({
  component: RetrieveTab,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      pipelineId: search.pipelineId as number | undefined,
    }
  },
})

function RetrieveTab() {
  const { pipelineId: initialPipelineId } = Route.useSearch()
  
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipelineId, setSelectedPipelineId] = useState<number | null>(initialPipelineId || null)
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  // For test pipelines: evaluation queries
  const [evaluationQueries, setEvaluationQueries] = useState<EvaluationQuery[]>([])
  const [loadingQueries, setLoadingQueries] = useState(false)

  useEffect(() => {
    loadPipelines()
  }, [])

  // Load evaluation queries when a test pipeline is selected
  useEffect(() => {
    const selectedPipeline = pipelines.find(p => p.id === selectedPipelineId)
    if (selectedPipeline && selectedPipeline.pipeline_type === 'test' && selectedPipeline.dataset) {
      loadEvaluationQueries(selectedPipeline.dataset.id)
    } else {
      setEvaluationQueries([])
    }
  }, [selectedPipelineId, pipelines])

  const loadPipelines = async () => {
    try {
      const items = await api.listPipelines()
      setPipelines(items)
      if (items.length > 0 && !selectedPipelineId) {
        setSelectedPipelineId(items[0].id)
      }
    } catch (err) {
      console.error('Failed to load pipelines:', err)
    }
  }

  const loadEvaluationQueries = async (datasetId: number) => {
    try {
      setLoadingQueries(true)
      const queries = await api.getDatasetQueries(datasetId)
      setEvaluationQueries(queries)
    } catch (err) {
      console.error('Failed to load evaluation queries:', err)
      setEvaluationQueries([])
    } finally {
      setLoadingQueries(false)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedPipelineId || !query.trim()) {
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await api.search({
        pipeline_id: selectedPipelineId,
        query: query.trim(),
        top_k: topK,
      })
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Retrieve</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Search Form */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg p-6 sticky top-8">
            <h2 className="text-xl font-semibold mb-4">Search Settings</h2>

            <form onSubmit={handleSearch} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pipeline
                </label>
                <select
                  value={selectedPipelineId || ''}
                  onChange={(e) => setSelectedPipelineId(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select Pipeline...</option>
                  {pipelines.map((pl) => (
                    <option key={pl.id} value={pl.id}>
                      {pl.name} ({pl.pipeline_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Query
                </label>
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={4}
                  placeholder="Enter your query..."
                  required
                />
              </div>

              {/* Evaluation Questions (for test pipelines) */}
              {pipelines.find(p => p.id === selectedPipelineId)?.pipeline_type === 'test' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📋 평가 질문 선택 (선택사항)
                  </label>
                  {loadingQueries ? (
                    <div className="text-sm text-gray-500 py-2">Loading questions...</div>
                  ) : evaluationQueries.length > 0 ? (
                    <div className="max-h-48 overflow-y-auto border border-gray-300 rounded-md">
                      {evaluationQueries.slice(0, 50).map((eq) => (
                        <button
                          key={eq.id}
                          type="button"
                          onClick={() => setQuery(eq.query)}
                          className="w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-200 last:border-b-0 text-sm"
                        >
                          <div className="font-medium text-gray-900 line-clamp-2">
                            {eq.query}
                          </div>
                          {eq.difficulty && (
                            <span className="text-xs text-gray-500 mt-1 inline-block">
                              난이도: {eq.difficulty}
                            </span>
                          )}
                        </button>
                      ))}
                      {evaluationQueries.length > 50 && (
                        <div className="px-3 py-2 text-xs text-gray-500 text-center">
                          +{evaluationQueries.length - 50} more questions
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-gray-500 py-2">No questions available</div>
                  )}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Top K Results
                </label>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  min={1}
                  max={20}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !selectedPipelineId || !query.trim()}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </form>

            {result && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Performance</h3>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Retrieval Time:</span>
                    <span className="font-medium">{result.retrieval_time.toFixed(3)}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Total Results:</span>
                    <span className="font-medium">{result.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Pipeline Type:</span>
                    <span className="font-medium">{result.pipeline_type}</span>
                  </div>
                </div>
                {result.comparison && (
                  <div className="mt-4 p-3 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg">
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">📊 평가 메트릭</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-700">Precision@{topK}:</span>
                        <span className="font-bold text-green-700">
                          {(result.comparison.precision_at_k * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-700">Recall@{topK}:</span>
                        <span className="font-bold text-blue-700">
                          {(result.comparison.recall_at_k * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-700">Hit Rate:</span>
                        <span className="font-bold text-purple-700">
                          {(result.comparison.hit_rate * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-green-200 text-xs text-gray-600">
                      정답 문서: {result.comparison.golden_doc_ids.length}개
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-2">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
              {error}
            </div>
          )}

          {!result && !error && !loading && (
            <div className="bg-white shadow rounded-lg p-8 text-center">
              <p className="text-gray-500">Enter a query to search</p>
            </div>
          )}

          {loading && (
            <div className="bg-white shadow rounded-lg p-8 text-center">
              <p className="text-gray-500">Searching...</p>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              <div className="bg-white shadow rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-2">Query</h2>
                <p className="text-gray-700">{result.query}</p>
              </div>

              <div>
                <h2 className="text-xl font-semibold mb-4">Results ({result.total})</h2>
                <div className="space-y-4">
                  {result.results.map((chunk, index) => (
                    <div 
                      key={chunk.chunk_id} 
                      className={`shadow rounded-lg p-6 ${
                        chunk.is_golden 
                          ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300' 
                          : 'bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <span className={`flex items-center justify-center w-8 h-8 rounded-full font-semibold ${
                            chunk.is_golden 
                              ? 'bg-green-100 text-green-700' 
                              : 'bg-blue-100 text-blue-600'
                          }`}>
                            {index + 1}
                          </span>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="text-sm text-gray-500">
                                Score: <span className="font-medium text-gray-900">{chunk.score.toFixed(4)}</span>
                              </p>
                              {chunk.is_golden && (
                                <span className="px-2 py-0.5 bg-green-600 text-white text-xs font-bold rounded-full">
                                  ✓ 정답
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-gray-400">
                              DataSource: {chunk.datasource_id}
                            </p>
                          </div>
                        </div>
                      </div>

                      <p className="text-gray-700 whitespace-pre-wrap">{chunk.content}</p>

                      {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
                        <details className="mt-3">
                          <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
                            Metadata
                          </summary>
                          <pre className="mt-2 text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                            {JSON.stringify(chunk.metadata, null, 2)}
                          </pre>
                        </details>
                      )}
                      {typeof chunk.is_golden === 'boolean' && (
                        <div className="mt-2 text-xs">
                          <span className={`px-2 py-1 rounded ${chunk.is_golden ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                            {chunk.is_golden ? 'GOLDEN MATCH' : 'NON-GOLDEN'}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

