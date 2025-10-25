import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type RAGConfiguration, type DataSource, type EvaluationDataset } from '../lib/api'

export const Route = createFileRoute('/pipelines/create')({
  component: CreatePipeline,
})

type PipelineType = 'normal' | 'test'

function CreatePipeline() {
  const navigate = useNavigate()
  const [pipelineType, setPipelineType] = useState<PipelineType>('normal')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [ragId, setRagId] = useState<number | null>(null)
  const [datasourceIds, setDatasourceIds] = useState<number[]>([])
  const [datasetId, setDatasetId] = useState<number | null>(null)

  const [rags, setRags] = useState<RAGConfiguration[]>([])
  const [datasources, setDatasources] = useState<DataSource[]>([])
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [ragsData, datasourcesData, datasetsData] = await Promise.all([
        api.listRAGs(),
        api.listDataSources(),
        api.listDatasets(),
      ])
      setRags(ragsData)
      setDatasources(datasourcesData)
      setDatasets(datasetsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Pipeline name is required')
      return
    }

    if (!ragId) {
      setError('Please select a RAG configuration')
      return
    }

    if (pipelineType === 'normal' && datasourceIds.length === 0) {
      setError('Please select at least one data source')
      return
    }

    if (pipelineType === 'test' && !datasetId) {
      setError('Please select a dataset')
      return
    }

    try {
      setSubmitting(true)
      const pipelineData =
        pipelineType === 'normal'
          ? {
              pipeline_type: 'normal' as const,
              name: name.trim(),
              description: description.trim() || undefined,
              rag_id: ragId,
              datasource_ids: datasourceIds,
            }
          : {
              pipeline_type: 'test' as const,
              name: name.trim(),
              description: description.trim() || undefined,
              rag_id: ragId,
              dataset_id: datasetId!,
            }

      await api.createPipeline(pipelineData)
      navigate({ to: '/pipelines' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create pipeline')
    } finally {
      setSubmitting(false)
    }
  }

  const toggleDatasource = (id: number) => {
    setDatasourceIds((prev) =>
      prev.includes(id) ? prev.filter((dsId) => dsId !== id) : [...prev, id]
    )
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-3xl font-bold mb-8">Create New Pipeline</h1>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Pipeline Type Selection */}
        <div>
          <label className="block text-sm font-medium mb-2">Pipeline Type</label>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setPipelineType('normal')}
              className={`p-4 rounded-lg border-2 text-left transition ${
                pipelineType === 'normal'
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <div className="font-semibold mb-1">Normal Pipeline</div>
              <div className="text-sm text-gray-600">
                For querying with data sources (files, URLs, etc.)
              </div>
            </button>
            <button
              type="button"
              onClick={() => setPipelineType('test')}
              className={`p-4 rounded-lg border-2 text-left transition ${
                pipelineType === 'test'
                  ? 'border-purple-600 bg-purple-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <div className="font-semibold mb-1">Test Pipeline</div>
              <div className="text-sm text-gray-600">
                For evaluation with test datasets
              </div>
            </button>
          </div>
        </div>

        {/* Basic Info */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium mb-2">
            Pipeline Name *
          </label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="My RAG Pipeline"
            required
          />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium mb-2">
            Description (Optional)
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={3}
            placeholder="Pipeline description..."
          />
        </div>

        {/* RAG Selection */}
        <div>
          <label htmlFor="rag" className="block text-sm font-medium mb-2">
            RAG Configuration *
          </label>
          <select
            id="rag"
            value={ragId || ''}
            onChange={(e) => setRagId(Number(e.target.value) || null)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="">Select a RAG configuration</option>
            {rags.map((rag) => (
              <option key={rag.id} value={rag.id}>
                {rag.name} ({rag.chunking_module} + {rag.embedding_module})
              </option>
            ))}
          </select>
          {rags.length === 0 && (
            <p className="mt-2 text-sm text-red-600">
              No RAG configurations available. Please create one first.
            </p>
          )}
        </div>

        {/* Normal Pipeline: Data Sources */}
        {pipelineType === 'normal' && (
          <div>
            <label className="block text-sm font-medium mb-2">
              Data Sources * (Select one or more)
            </label>
            <div className="border border-gray-300 rounded-md p-4 max-h-60 overflow-y-auto">
              {datasources.length === 0 ? (
                <p className="text-sm text-red-600">
                  No data sources available. Please create one first.
                </p>
              ) : (
                <div className="space-y-2">
                  {datasources.map((ds) => (
                    <label
                      key={ds.id}
                      className="flex items-start gap-3 p-3 rounded hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={datasourceIds.includes(ds.id)}
                        onChange={() => toggleDatasource(ds.id)}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className="font-medium">{ds.name}</div>
                        <div className="text-sm text-gray-600">
                          Type: {ds.source_type} | Status: {ds.status}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
            <p className="mt-2 text-sm text-gray-500">
              Selected: {datasourceIds.length} data source(s)
            </p>
          </div>
        )}

        {/* Test Pipeline: Dataset */}
        {pipelineType === 'test' && (
          <div>
            <label htmlFor="dataset" className="block text-sm font-medium mb-2">
              Evaluation Dataset *
            </label>
            <select
              id="dataset"
              value={datasetId || ''}
              onChange={(e) => setDatasetId(Number(e.target.value) || null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select a dataset</option>
              {datasets.map((ds) => (
                <option key={ds.id} value={ds.id}>
                  {ds.name} ({ds.queries?.length || 0} queries, {ds.documents?.length || 0} docs)
                </option>
              ))}
            </select>
            {datasets.length === 0 && (
              <p className="mt-2 text-sm text-red-600">
                No datasets available. Please create one first.
              </p>
            )}
          </div>
        )}

        {/* Submit Buttons */}
        <div className="flex gap-4 pt-4">
          <button
            type="button"
            onClick={() => navigate({ to: '/pipelines' })}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300"
            disabled={submitting}
          >
            {submitting ? 'Creating...' : 'Create Pipeline'}
          </button>
        </div>
      </form>

      {submitting && (
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
          <p className="text-sm text-blue-700">
            ⏳ Creating pipeline and indexing data... This may take a few moments.
          </p>
        </div>
      )}
    </div>
  )
}

