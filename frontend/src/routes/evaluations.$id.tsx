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

  const result = evaluation.results?.[0]

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

      {/* Metrics */}
      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <MetricCard title="NDCG@10" value={result.ndcg_at_k} />
            <MetricCard title="MRR" value={result.mrr} />
            <MetricCard title="Precision@10" value={result.precision_at_k} />
            <MetricCard title="Recall@10" value={result.recall_at_k} />
            <MetricCard title="Hit Rate" value={result.hit_rate} />
            <MetricCard title="MAP" value={result.map_score} />
          </div>

          {/* Performance */}
          <div className="bg-white shadow rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Performance</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-500">Retrieval Time</p>
                <p className="text-2xl font-semibold">{result.retrieval_time.toFixed(3)}s</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Time</p>
                <p className="text-2xl font-semibold">{result.total_time.toFixed(3)}s</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Chunks</p>
                <p className="text-2xl font-semibold">{result.num_chunks}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Avg Chunk Size</p>
                <p className="text-2xl font-semibold">{result.avg_chunk_size.toFixed(0)}</p>
              </div>
            </div>
          </div>

          {/* Sample Query Results */}
          {result.query_results && result.query_results.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Sample Query Results</h2>
              <div className="space-y-6">
                {result.query_results.map((qr: any, index: number) => (
                  <div key={index} className="border-b border-gray-200 pb-6 last:border-b-0">
                    <div className="mb-3">
                      <p className="font-medium text-gray-900">{qr.query}</p>
                      <p className="text-sm text-gray-500">Query ID: {qr.query_id}</p>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-6 gap-2 mb-3">
                      <div className="text-center">
                        <p className="text-xs text-gray-500">NDCG</p>
                        <p className="text-sm font-medium">{qr.metrics.ndcg_at_k.toFixed(3)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-500">MRR</p>
                        <p className="text-sm font-medium">{qr.metrics.mrr.toFixed(3)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-500">Precision</p>
                        <p className="text-sm font-medium">{qr.metrics.precision_at_k.toFixed(3)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-500">Recall</p>
                        <p className="text-sm font-medium">{qr.metrics.recall_at_k.toFixed(3)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-500">Hit Rate</p>
                        <p className="text-sm font-medium">{qr.metrics.hit_rate.toFixed(3)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-500">MAP</p>
                        <p className="text-sm font-medium">{qr.metrics.map_score.toFixed(3)}</p>
                      </div>
                    </div>

                    <details>
                      <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
                        Retrieved Documents ({qr.retrieved.length})
                      </summary>
                      <div className="mt-2 space-y-2">
                        {qr.retrieved.map((doc: any, docIndex: number) => (
                          <div key={docIndex} className="bg-gray-50 p-3 rounded text-sm">
                            <p className="text-gray-700">{doc.content}</p>
                            <p className="text-xs text-gray-500 mt-1">Score: {doc.score.toFixed(4)}</p>
                          </div>
                        ))}
                      </div>
                    </details>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
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

