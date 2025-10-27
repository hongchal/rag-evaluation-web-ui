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

      const createdPipeline = await api.createPipeline(pipelineData)
      // Navigate to the created pipeline's detail page to show indexing status
      navigate({ to: '/pipelines/$id', params: { id: String(createdPipeline.id) } })
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
                      className="flex items-start gap-3 p-3 rounded hover:bg-gray-50 cursor-pointer border border-transparent hover:border-gray-200 transition"
                    >
                      <input
                        type="checkbox"
                        checked={datasourceIds.includes(ds.id)}
                        onChange={() => toggleDatasource(ds.id)}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        {/* Data Source Name */}
                        <div className="font-medium text-gray-900 mb-1">{ds.name}</div>
                        
                        {/* File Path (if different from name) */}
                        {ds.source_uri && ds.source_uri.split('/').pop() !== ds.name && (
                          <div className="text-xs text-gray-500 mb-1 truncate" title={ds.source_uri}>
                            📄 {ds.source_uri.split('/').pop()}
                          </div>
                        )}
                        
                        {/* Metadata Line */}
                        <div className="flex items-center gap-2 flex-wrap text-xs">
                          {/* Processor Badge */}
                          {ds.processor_type && (
                            <span className={`px-2 py-0.5 rounded-full font-medium ${
                              ds.processor_type === 'docling' 
                                ? 'bg-purple-100 text-purple-800' 
                                : ds.processor_type === 'pdfplumber' 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {ds.processor_type === 'pypdf2' && '⚡ PyPDF2'}
                              {ds.processor_type === 'pdfplumber' && '✅ pdfplumber'}
                              {ds.processor_type === 'docling' && '🚀 Docling'}
                            </span>
                          )}
                          
                          {/* Type Badge */}
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full font-medium">
                            {ds.source_type}
                          </span>
                          
                          {/* Status Badge */}
                          <span className={`px-2 py-0.5 rounded-full font-medium ${
                            ds.status === 'active' 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-gray-100 text-gray-600'
                          }`}>
                            {ds.status}
                          </span>
                          
                          {/* File Size */}
                          {ds.file_size && (
                            <span className="text-gray-500">
                              {ds.file_size < 1024 * 1024 
                                ? `${(ds.file_size / 1024).toFixed(1)} KB`
                                : `${(ds.file_size / (1024 * 1024)).toFixed(1)} MB`
                              }
                            </span>
                          )}
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
                  {ds.name} ({ds.num_queries || 0} queries, {ds.num_documents || 0} docs)
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
          <div className="flex items-start gap-3">
            <div className="animate-spin text-2xl">⚙️</div>
            <div className="flex-1">
              <p className="font-semibold text-blue-900 mb-2">
                파이프라인 생성 및 데이터 인덱싱 중...
              </p>
              <div className="space-y-1 text-sm text-blue-700">
                <p>✅ 1. 파이프라인 설정 저장 중...</p>
                <p>📄 2. 데이터 소스 로딩 중...</p>
                <p>✂️ 3. 문서 청킹 (Chunking) 진행 중...</p>
                <p>🔢 4. 임베딩 (Embedding) 생성 중...</p>
                <p>💾 5. Qdrant 벡터 DB에 저장 중...</p>
              </div>
              <p className="mt-3 text-xs text-blue-600">
                💡 대용량 문서의 경우 수 분이 소요될 수 있습니다. 잠시만 기다려주세요.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

