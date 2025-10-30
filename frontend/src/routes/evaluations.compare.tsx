import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type Evaluation } from '../lib/api'

export const Route = createFileRoute('/evaluations/compare')({
  component: CompareEvaluationsPage,
})

function CompareEvaluationsPage() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Sorting state for Summary Table
  const [sortColumn, setSortColumn] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    loadEvaluations()
  }, [])

  const loadEvaluations = async () => {
    try {
      setLoading(true)
      const data = await api.listEvaluations()
      const completed = data.filter(e => e.status === 'completed')
      setEvaluations(completed)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load evaluations')
    } finally {
      setLoading(false)
    }
  }

  const toggleSelection = (id: number) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id))
    } else {
      if (selectedIds.length < 5) {
        setSelectedIds([...selectedIds, id])
      }
    }
  }

  const selectedEvaluations = evaluations.filter(e => selectedIds.includes(e.id))

  const metrics = [
    { key: 'ndcg_at_k', label: 'NDCG@10', color: 'blue' },
    { key: 'mrr', label: 'MRR', color: 'green' },
    { key: 'precision_at_k', label: 'Precision@10', color: 'purple' },
    { key: 'recall_at_k', label: 'Recall@10', color: 'orange' },
    { key: 'hit_rate', label: 'Hit Rate', color: 'pink' },
    { key: 'map', label: 'MAP', color: 'indigo' },
  ]

  const getMetricValue = (evaluation: Evaluation, metricKey: string): number => {
    if (!evaluation.results || evaluation.results.length === 0) return 0
    const result = evaluation.results[0]
    return (result as any)[metricKey] || 0
  }

  const getBestValue = (metricKey: string): number => {
    return Math.max(...selectedEvaluations.map(e => getMetricValue(e, metricKey)))
  }

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      // Set new column with descending order by default (higher is better)
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  const getSortedEvaluations = (evaluations: Evaluation[]) => {
    if (!sortColumn) return evaluations

    return [...evaluations].sort((a, b) => {
      if (sortColumn === 'name') {
        const aName = a.name
        const bName = b.name
        return sortDirection === 'asc' 
          ? aName.localeCompare(bName)
          : bName.localeCompare(aName)
      }

      // For metric columns
      const aValue = getMetricValue(a, sortColumn)
      const bValue = getMetricValue(b, sortColumn)
      return sortDirection === 'asc' ? aValue - bValue : bValue - aValue
    })
  }

  const SortIcon = ({ column }: { column: string }) => {
    if (sortColumn !== column) {
      return <span className="text-gray-400 ml-1">↕</span>
    }
    return <span className="ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>
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
      <h1 className="text-3xl font-bold mb-8">Compare Evaluations</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Selection Panel */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg p-6 sticky top-8">
            <h2 className="text-xl font-semibold mb-4">
              Select Evaluations ({selectedIds.length}/5)
            </h2>

            {evaluations.length === 0 ? (
              <p className="text-gray-500 text-sm">No completed evaluations available</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {evaluations.map((evaluation) => (
                  <button
                    key={evaluation.id}
                    onClick={() => toggleSelection(evaluation.id)}
                    disabled={!selectedIds.includes(evaluation.id) && selectedIds.length >= 5}
                    className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
                      selectedIds.includes(evaluation.id)
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    <p className="font-medium text-sm truncate">{evaluation.name}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      RAG #{evaluation.rag_id} • Dataset #{evaluation.dataset_id}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Comparison Panel */}
        <div className="lg:col-span-2">
          {selectedEvaluations.length === 0 ? (
            <div className="bg-white shadow rounded-lg p-12 text-center">
              <div className="text-gray-400 mb-4">
                <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No evaluations selected</h3>
              <p className="text-gray-500">
                Select 2-5 evaluations from the left panel to compare their metrics.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Metrics Comparison */}
              {metrics.map((metric) => (
                <div key={metric.key} className="bg-white shadow rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">{metric.label}</h3>
                  <div className="space-y-3">
                    {selectedEvaluations.map((evaluation) => {
                      const value = getMetricValue(evaluation, metric.key)
                      const bestValue = getBestValue(metric.key)
                      const isBest = value === bestValue && value > 0
                      const percentage = bestValue > 0 ? (value / bestValue) * 100 : 0

                      return (
                        <div key={evaluation.id}>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-sm font-medium text-gray-700 truncate max-w-xs">
                              {evaluation.name}
                              {isBest && <span className="ml-2 text-xs text-green-600">🏆 Best</span>}
                            </span>
                            <span className="text-sm font-bold text-gray-900">
                              {value.toFixed(4)}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full transition-all ${
                                isBest ? 'bg-green-600' : `bg-${metric.color}-600`
                              }`}
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}

              {/* Summary Table */}
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Summary Table</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th 
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none"
                          onClick={() => handleSort('name')}
                        >
                          Evaluation <SortIcon column="name" />
                        </th>
                        {metrics.map((metric) => (
                          <th 
                            key={metric.key} 
                            className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100 select-none"
                            onClick={() => handleSort(metric.key)}
                          >
                            {metric.label} <SortIcon column={metric.key} />
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {getSortedEvaluations(selectedEvaluations).map((evaluation) => (
                        <tr key={evaluation.id}>
                          <td className="px-4 py-3 text-sm font-medium text-gray-900 truncate max-w-xs">
                            {evaluation.name}
                          </td>
                          {metrics.map((metric) => {
                            const value = getMetricValue(evaluation, metric.key)
                            const bestValue = getBestValue(metric.key)
                            const isBest = value === bestValue && value > 0

                            return (
                              <td
                                key={metric.key}
                                className={`px-4 py-3 text-sm text-right ${
                                  isBest ? 'font-bold text-green-600' : 'text-gray-900'
                                }`}
                              >
                                {value.toFixed(4)}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Performance Comparison */}
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Performance Metrics</h3>
                <div className="grid md:grid-cols-3 gap-4">
                  {selectedEvaluations.map((evaluation) => (
                    <div key={evaluation.id} className="border border-gray-200 rounded-lg p-4">
                      <p className="text-sm font-medium text-gray-700 mb-3 truncate">
                        {evaluation.name}
                      </p>
                      <div className="space-y-2 text-xs">
                        {evaluation.results && evaluation.results[0] && (
                          <>
                            <div className="flex justify-between">
                              <span className="text-gray-500">Retrieval Time:</span>
                              <span className="font-medium">
                                {evaluation.results[0].retrieval_time?.toFixed(2)}s
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-500">Total Time:</span>
                              <span className="font-medium">
                                {evaluation.results[0].total_time?.toFixed(2)}s
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-500">Chunks:</span>
                              <span className="font-medium">
                                {evaluation.results[0].num_chunks}
                              </span>
                            </div>
                          </>
                        )}
                      </div>
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

