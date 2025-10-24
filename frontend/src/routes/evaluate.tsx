import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type RAGConfiguration, type EvaluationDataset, type Evaluation } from '../lib/api'

export const Route = createFileRoute('/evaluate')({
  component: EvaluatePage,
})

function EvaluatePage() {
  const navigate = useNavigate()
  const [rags, setRags] = useState<RAGConfiguration[]>([])
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([])
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [loading, setLoading] = useState(true)

  // Form state
  const [selectedRagId, setSelectedRagId] = useState<number | null>(null)
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null)
  const [evalName, setEvalName] = useState('')
  const [evalDescription, setEvalDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [ragsData, datasetsData, evalsData] = await Promise.all([
        api.listRAGs(),
        api.listDatasets(),
        api.listEvaluations(),
      ])
      setRags(ragsData)
      setDatasets(datasetsData)
      setEvaluations(evalsData)

      if (ragsData.length > 0) setSelectedRagId(ragsData[0].id)
      if (datasetsData.length > 0) setSelectedDatasetId(datasetsData[0].id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedRagId || !selectedDatasetId) {
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      const evaluation = await api.runEvaluation(
        selectedRagId,
        selectedDatasetId,
        evalName || undefined,
        evalDescription || undefined
      )
      navigate({ to: '/evaluations/$id', params: { id: evaluation.id.toString() } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start evaluation')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Run Evaluation</h1>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Evaluation Form */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-6">Start New Evaluation</h2>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
                {error}
              </div>
            )}

            {rags.length === 0 || datasets.length === 0 ? (
              <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
                {rags.length === 0 && <p>⚠️ No RAG configurations available. Create one first.</p>}
                {datasets.length === 0 && <p>⚠️ No datasets available. Upload a dataset first.</p>}
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    RAG Configuration *
                  </label>
                  <select
                    value={selectedRagId || ''}
                    onChange={(e) => setSelectedRagId(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    {rags.map((rag) => (
                      <option key={rag.id} value={rag.id}>
                        {rag.name} ({rag.chunking_module} + {rag.embedding_module} + {rag.reranking_module})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Evaluation Dataset *
                  </label>
                  <select
                    value={selectedDatasetId || ''}
                    onChange={(e) => setSelectedDatasetId(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    {datasets.map((dataset) => (
                      <option key={dataset.id} value={dataset.id}>
                        {dataset.name} ({dataset.num_queries} queries, {dataset.num_documents} docs)
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Evaluation Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={evalName}
                    onChange={(e) => setEvalName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Leave empty for auto-generated name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description (Optional)
                  </label>
                  <textarea
                    value={evalDescription}
                    onChange={(e) => setEvalDescription(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={3}
                    placeholder="Describe this evaluation..."
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting || !selectedRagId || !selectedDatasetId}
                  className="w-full px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 font-medium"
                >
                  {submitting ? 'Starting Evaluation...' : 'Start Evaluation'}
                </button>
              </form>
            )}
          </div>
        </div>

        {/* Recent Evaluations */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg p-6 sticky top-8">
            <h2 className="text-xl font-semibold mb-4">Recent Evaluations</h2>

            {evaluations.length === 0 ? (
              <p className="text-gray-500 text-sm">No evaluations yet</p>
            ) : (
              <div className="space-y-3">
                {evaluations.slice(0, 5).map((evaluation) => (
                  <button
                    key={evaluation.id}
                    onClick={() => navigate({ to: '/evaluations/$id', params: { id: evaluation.id.toString() } })}
                    className="w-full text-left border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors"
                  >
                    <p className="font-medium text-sm mb-1 truncate">{evaluation.name}</p>
                    <div className="flex items-center justify-between text-xs">
                      <span className={`px-2 py-0.5 rounded ${
                        evaluation.status === 'completed' ? 'bg-green-100 text-green-800' :
                        evaluation.status === 'running' ? 'bg-blue-100 text-blue-800' :
                        evaluation.status === 'failed' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {evaluation.status}
                      </span>
                      {(evaluation.status === 'running' || evaluation.status === 'pending') && (
                        <span className="text-gray-500">{evaluation.progress.toFixed(0)}%</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
