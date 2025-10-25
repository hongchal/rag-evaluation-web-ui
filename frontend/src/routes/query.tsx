import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type Pipeline, type SearchResponse } from '../lib/api'

export const Route = createFileRoute('/query')({
  component: QueryTest,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      pipelineId: search.pipelineId as number | undefined,
    }
  },
})

function QueryTest() {
  const { pipelineId: initialPipelineId } = Route.useSearch()
  
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipelineId, setSelectedPipelineId] = useState<number | null>(initialPipelineId || null)
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPipelines()
  }, [])

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
      <h1 className="text-3xl font-bold mb-8">Query Test</h1>

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
                  <div className="mt-4 space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Precision@K:</span>
                      <span className="font-medium">{result.comparison.precision_at_k.toFixed(3)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Recall@K:</span>
                      <span className="font-medium">{result.comparison.recall_at_k.toFixed(3)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Hit Rate:</span>
                      <span className="font-medium">{result.comparison.hit_rate.toFixed(3)}</span>
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
                    <div key={chunk.chunk_id} className="bg-white shadow rounded-lg p-6">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <span className="flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-600 rounded-full font-semibold">
                            {index + 1}
                          </span>
                          <div>
                            <p className="text-sm text-gray-500">
                              Score: <span className="font-medium text-gray-900">{chunk.score.toFixed(4)}</span>
                            </p>
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

