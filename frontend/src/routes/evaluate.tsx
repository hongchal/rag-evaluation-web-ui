import { createFileRoute, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api } from '../lib/api'

export const Route = createFileRoute('/evaluate')({
  component: EvaluatePage,
})

function EvaluatePage() {
  // State
  const [datasets, setDatasets] = useState<any[]>([])
  const [pipelines, setPipelines] = useState<any[]>([])
  const [evaluations, setEvaluations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string>('')

  // Form state
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null)
  const [selectedPipelineIds, setSelectedPipelineIds] = useState<Set<number>>(new Set())
  const [evaluationName, setEvaluationName] = useState('')

  // Load initial data
  useEffect(() => {
    loadInitialData()
  }, [])

  // Load pipelines when dataset changes
  useEffect(() => {
    if (selectedDatasetId) {
      loadPipelines(selectedDatasetId)
    } else {
      setPipelines([])
      setSelectedPipelineIds(new Set())
    }
  }, [selectedDatasetId])

  const loadInitialData = async () => {
    try {
      setLoading(true)
      const [datasetsData, evalsData] = await Promise.all([
        api.listDatasets(),
        api.listEvaluations(),
      ])
      
      setDatasets(datasetsData.filter((d: any) => d.status === 'ready'))
      setEvaluations(evalsData)

      // Auto-select first dataset
      if (datasetsData.length > 0) {
        setSelectedDatasetId(datasetsData[0].id)
      }
    } catch (err: any) {
      console.error('Failed to load data:', err)
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const loadPipelines = async (datasetId: number) => {
    try {
      const params = new URLSearchParams()
      params.append('dataset_id', datasetId.toString())
      params.append('pipeline_type', 'test')
      
      const pipelinesData = await api.listPipelines(`?${params.toString()}`)
      setPipelines(pipelinesData.filter((p: any) => p.status === 'ready'))
      setSelectedPipelineIds(new Set())
    } catch (err) {
      console.error('Failed to load pipelines:', err)
      setPipelines([])
    }
  }

  const togglePipeline = (pipelineId: number) => {
    const newSelected = new Set(selectedPipelineIds)
    if (newSelected.has(pipelineId)) {
      newSelected.delete(pipelineId)
    } else {
      newSelected.add(pipelineId)
    }
    setSelectedPipelineIds(newSelected)
  }

  const selectAllPipelines = () => {
    setSelectedPipelineIds(new Set(pipelines.map(p => p.id)))
  }

  const deselectAllPipelines = () => {
    setSelectedPipelineIds(new Set())
  }

  const handleRunEvaluation = async () => {
    if (!selectedDatasetId || selectedPipelineIds.size === 0) {
      setError('Please select a dataset and at least one pipeline')
      return
    }

    setSubmitting(true)
    setError('')

    try {
      // Run evaluation for all selected pipelines in one request
      const pipelineIdArray = Array.from(selectedPipelineIds)
      const name = evaluationName 
        ? evaluationName
        : `Evaluation - ${new Date().toLocaleString()}`
      
      await api.runEvaluation({
        pipeline_ids: pipelineIdArray,
        name: name,
        description: undefined
      })
      
      alert(`Successfully started evaluation for ${selectedPipelineIds.size} pipeline(s)!`)
      
      // Reload evaluations
      const evalsData = await api.listEvaluations()
      setEvaluations(evalsData)
      
      // Reset form
      setEvaluationName('')
      setSelectedPipelineIds(new Set())
      
    } catch (err: any) {
      console.error('Failed to run evaluation:', err)
      setError(err.message || 'Failed to run evaluation')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto p-6 max-w-7xl">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-600">Loading...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Evaluation</h1>
        <p className="text-gray-600">
          Select a dataset and pipelines to compare their performance
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Evaluation Setup */}
        <div className="lg:col-span-2 space-y-6">
          {/* Dataset Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              1. Select Dataset
            </h2>
            
            {datasets.length === 0 ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 text-yellow-800">
                <p className="font-medium">No datasets available</p>
                <p className="text-sm mt-1">
                  Please download a dataset from the{' '}
                  <Link to="/datasets" className="underline hover:text-yellow-900">
                    Datasets page
                  </Link>
                  {' '}first.
                </p>
              </div>
            ) : (
              <select
                value={selectedDatasetId || ''}
                onChange={(e) => setSelectedDatasetId(Number(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.name} ({dataset.num_queries} queries)
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Pipeline Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                2. Select Pipelines to Compare
              </h2>
              {pipelines.length > 0 && (
                <div className="flex gap-2">
                  <button
                    onClick={selectAllPipelines}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    Select All
                  </button>
                  <span className="text-gray-400">|</span>
                  <button
                    onClick={deselectAllPipelines}
                    className="text-sm text-gray-600 hover:text-gray-800"
                  >
                    Clear
                  </button>
                </div>
              )}
            </div>

            {!selectedDatasetId ? (
              <div className="text-gray-500 text-center py-8">
                Please select a dataset first
              </div>
            ) : pipelines.length === 0 ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 text-yellow-800">
                <p className="font-medium">No pipelines found for this dataset</p>
                <p className="text-sm mt-1">
                  Create test pipelines with this dataset from the{' '}
                  <Link to="/pipelines" className="underline hover:text-yellow-900">
                    Pipelines page
                  </Link>
                  .
                </p>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {pipelines.map((pipeline) => (
                  <label
                    key={pipeline.id}
                    className="flex items-start p-3 border border-gray-200 rounded-md hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedPipelineIds.has(pipeline.id)}
                      onChange={() => togglePipeline(pipeline.id)}
                      className="mt-1 mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">
                        {pipeline.name}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        RAG: {pipeline.rag?.name || `ID ${pipeline.rag_id}`}
                      </div>
                      {pipeline.description && (
                        <div className="text-xs text-gray-400 mt-1">
                          {pipeline.description}
                        </div>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            )}

            <div className="mt-4 text-sm text-gray-600">
              {selectedPipelineIds.size} pipeline(s) selected
            </div>
          </div>

          {/* Evaluation Name */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              3. Evaluation Name (Optional)
            </h2>
            <input
              type="text"
              value={evaluationName}
              onChange={(e) => setEvaluationName(e.target.value)}
              placeholder="Auto-generated if empty"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
              {error}
            </div>
          )}

          {/* Run Button */}
          <button
            onClick={handleRunEvaluation}
            disabled={submitting || selectedPipelineIds.size === 0 || !selectedDatasetId}
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium text-lg flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                Running Evaluation...
              </>
            ) : (
              <>
                🚀 Run Evaluation ({selectedPipelineIds.size} pipeline{selectedPipelineIds.size !== 1 ? 's' : ''})
              </>
            )}
          </button>
        </div>

        {/* Right Panel - Recent Evaluations */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow p-6 sticky top-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Recent Evaluations
            </h2>
            
            {evaluations.length === 0 ? (
              <p className="text-gray-500 text-sm">No evaluations yet</p>
            ) : (
              <div className="space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto">
                {evaluations.slice(0, 10).map((evaluation) => (
                  <div
                    key={evaluation.id}
                    className="relative group border border-gray-200 rounded-md hover:border-blue-300 transition-colors"
                  >
                    <Link
                      to="/evaluations/$id"
                      params={{ id: String(evaluation.id) }}
                      className="block p-3 hover:bg-blue-50 transition-colors"
                    >
                      <div className="font-medium text-gray-900 text-sm truncate pr-8">
                        {evaluation.name || `Evaluation #${evaluation.id}`}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {new Date(evaluation.created_at).toLocaleDateString()}
                      </div>
                      <div className={`text-xs mt-1 font-medium ${
                        evaluation.status === 'completed' ? 'text-green-600' :
                        evaluation.status === 'failed' ? 'text-red-600' :
                        'text-yellow-600'
                      }`}>
                        {evaluation.status}
                      </div>
                    </Link>
                    <button
                      onClick={async (e) => {
                        e.preventDefault()
                        if (confirm(`Delete "${evaluation.name || `Evaluation #${evaluation.id}`}"?`)) {
                          try {
                            await api.deleteEvaluation(evaluation.id)
                            const evalsData = await api.listEvaluations()
                            setEvaluations(evalsData)
                          } catch (err) {
                            console.error('Failed to delete evaluation:', err)
                            alert('Failed to delete evaluation')
                          }
                        }
                      }}
                      className="absolute top-2 right-2 p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-all"
                      title="Delete evaluation"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
