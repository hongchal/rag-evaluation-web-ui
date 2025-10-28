import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type Pipeline } from '../lib/api'

export const Route = createFileRoute('/pipelines/$id')({
  component: PipelineDetail,
})

function PipelineDetail() {
  const { id } = Route.useParams()
  const navigate = useNavigate()
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    loadPipeline(false) // Initial load with loading state
  }, [id])

  // Auto-refresh when pipeline is indexing or pending
  useEffect(() => {
    if (!pipeline || (pipeline.status !== 'indexing' && pipeline.status !== 'pending')) {
      return
    }

    const interval = setInterval(() => {
      loadPipeline(true) // Silent refresh without loading state
    }, 3000) // Refresh every 3 seconds

    return () => clearInterval(interval)
  }, [pipeline])

  const loadPipeline = async (silent: boolean = false) => {
    try {
      if (!silent) {
        setLoading(true)
      }
      const data = await api.getPipeline(Number(id))
      setPipeline(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pipeline')
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this pipeline? This will remove all indexed data for this pipeline.')) {
      return
    }

    try {
      setDeleting(true)
      await api.deletePipeline(Number(id))
      navigate({ to: '/pipelines' })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete pipeline')
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  if (error || !pipeline) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error || 'Pipeline not found'}
        </div>
        <Link
          to="/pipelines"
          className="inline-block mt-4 text-blue-600 hover:underline"
        >
          ← Back to Pipelines
        </Link>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/pipelines"
          className="text-blue-600 hover:underline mb-4 inline-block"
        >
          ← Back to Pipelines
        </Link>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h1 className="text-3xl font-bold">{pipeline.name}</h1>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  pipeline.pipeline_type === 'normal'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-purple-100 text-purple-700'
                }`}
              >
                {pipeline.pipeline_type === 'normal' ? 'NORMAL' : 'TEST'}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  pipeline.status === 'pending'
                    ? 'bg-yellow-100 text-yellow-700'
                    : pipeline.status === 'indexing'
                    ? 'bg-blue-100 text-blue-700'
                    : pipeline.status === 'ready'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700'
                }`}
              >
                {pipeline.status === 'pending' && '⏳ 대기 중'}
                {pipeline.status === 'indexing' && '🔄 인덱싱 중'}
                {pipeline.status === 'ready' && '✅ 사용 가능'}
                {pipeline.status === 'failed' && '❌ 실패'}
              </span>
            </div>
            {pipeline.description && (
              <p className="text-gray-600 mb-3">{pipeline.description}</p>
            )}
            
            {/* Indexing Progress Card */}
            {(pipeline.status === 'indexing' || pipeline.status === 'pending') && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-blue-900">
                    {pipeline.status === 'pending' ? '인덱싱 대기 중...' : '인덱싱 진행 중...'}
                  </span>
                  {pipeline.indexing_progress != null && (
                    <span className="text-sm font-medium text-blue-700">
                      {pipeline.indexing_progress.toFixed(1)}%
                    </span>
                  )}
                </div>
                {pipeline.indexing_progress != null && (
                  <div className="w-full bg-blue-200 rounded-full h-2.5">
                    <div
                      className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                      style={{ width: `${pipeline.indexing_progress}%` }}
                    ></div>
                  </div>
                )}
                <p className="text-xs text-blue-700 mt-2">
                  페이지가 자동으로 새로고침됩니다...
                </p>
              </div>
            )}

            {/* Indexing Error */}
            {pipeline.status === 'failed' && pipeline.indexing_error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm font-medium text-red-900 mb-1">인덱싱 실패</p>
                <p className="text-sm text-red-700">{pipeline.indexing_error}</p>
              </div>
            )}

            {/* Indexing Stats */}
            {pipeline.status === 'ready' && pipeline.indexing_stats && (
              <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm font-medium text-green-900 mb-2">인덱싱 완료</p>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  {pipeline.indexing_stats.total_chunks && (
                    <div>
                      <span className="text-green-700">총 청크:</span>{' '}
                      <span className="font-medium text-green-900">
                        {pipeline.indexing_stats.total_chunks.toLocaleString()}
                      </span>
                    </div>
                  )}
                  {pipeline.indexing_stats.total_documents && (
                    <div>
                      <span className="text-green-700">총 문서:</span>{' '}
                      <span className="font-medium text-green-900">
                        {pipeline.indexing_stats.total_documents.toLocaleString()}
                      </span>
                    </div>
                  )}
                  {pipeline.indexing_stats.elapsed_seconds && (
                    <div>
                      <span className="text-green-700">소요 시간:</span>{' '}
                      <span className="font-medium text-green-900">
                        {pipeline.indexing_stats.elapsed_seconds.toFixed(1)}초
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          <button
            onClick={handleDelete}
            disabled={deleting || pipeline.status === 'indexing'}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {deleting ? 'Deleting...' : 'Delete Pipeline'}
          </button>
        </div>
      </div>

      {/* Pipeline Info */}
      <div className="space-y-6">
        {/* RAG Configuration */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">RAG Configuration</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-500">Name</span>
              <div className="font-medium">
                <Link
                  to={`/rags/${pipeline.rag.id}` as any}
                  className="text-blue-600 hover:underline"
                >
                  {pipeline.rag.name}
                </Link>
              </div>
            </div>
            <div>
              <span className="text-sm text-gray-500">Collection</span>
              <div className="font-medium">{pipeline.rag.collection_name}</div>
            </div>
            <div>
              <span className="text-sm text-gray-500">Chunking</span>
              <div className="font-medium">{pipeline.rag.chunking_module}</div>
            </div>
            <div>
              <span className="text-sm text-gray-500">Embedding</span>
              <div className="font-medium">{pipeline.rag.embedding_module}</div>
            </div>
            <div>
              <span className="text-sm text-gray-500">Reranking</span>
              <div className="font-medium">{pipeline.rag.reranking_module}</div>
            </div>
          </div>
        </div>

        {/* Data Sources (Normal Pipeline) */}
        {pipeline.pipeline_type === 'normal' && pipeline.datasources && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Data Sources</h2>
            {pipeline.datasources.length === 0 ? (
              <p className="text-gray-500">No data sources</p>
            ) : (
              <div className="space-y-3">
                {pipeline.datasources.map((ds) => (
                  <div
                    key={ds.id}
                    className="p-4 border border-gray-200 rounded-lg hover:border-gray-300"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-medium">{ds.name}</div>
                      <span
                        className={`px-2 py-1 text-xs rounded ${
                          ds.status === 'active'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {ds.status}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                      <div>
                        <span className="font-medium">Type:</span> {ds.source_type}
                      </div>
                      <div>
                        <span className="font-medium">Size:</span>{' '}
                        {(ds.file_size / 1024).toFixed(1)} KB
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Dataset (Test Pipeline) */}
        {pipeline.pipeline_type === 'test' && pipeline.dataset && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Evaluation Dataset</h2>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="font-medium mb-2">
                <Link
                  to={`/datasets/${pipeline.dataset.id}` as any}
                  className="text-blue-600 hover:underline"
                >
                  {pipeline.dataset.name}
                </Link>
              </div>
              {pipeline.dataset.description && (
                <p className="text-sm text-gray-600 mb-3">
                  {pipeline.dataset.description}
                </p>
              )}
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-500">Queries:</span>{' '}
                  <span className="font-medium">{pipeline.dataset.num_queries || 0}</span>
                </div>
                <div>
                  <span className="text-gray-500">Documents:</span>{' '}
                  <span className="font-medium">{pipeline.dataset.num_documents || 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Metadata */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Metadata</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Pipeline ID</span>
              <div className="font-medium">{pipeline.id}</div>
            </div>
            <div>
              <span className="text-gray-500">RAG ID</span>
              <div className="font-medium">{pipeline.rag_id}</div>
            </div>
            <div>
              <span className="text-gray-500">Created At</span>
              <div className="font-medium">
                {new Date(pipeline.created_at).toLocaleString()}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Updated At</span>
              <div className="font-medium">
                {new Date(pipeline.updated_at).toLocaleString()}
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Actions</h2>
          {pipeline.status !== 'ready' ? (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
              인덱싱이 완료된 후 파이프라인을 사용할 수 있습니다.
            </div>
          ) : (
            <div className="flex gap-3">
              {pipeline.pipeline_type === 'normal' && (
                <Link
                  to="/retrieve"
                  search={{ pipelineId: pipeline.id }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Query this Pipeline
                </Link>
              )}
              {pipeline.pipeline_type === 'test' && (
                <Link
                  to="/evaluate"
                  search={{ pipeline_ids: [pipeline.id] }}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
                >
                  Evaluate this Pipeline
                </Link>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

