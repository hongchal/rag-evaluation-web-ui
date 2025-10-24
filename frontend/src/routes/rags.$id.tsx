import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type RAGConfiguration, type DataSourceSync } from '../lib/api'

export const Route = createFileRoute('/rags/$id')({
  component: RAGDetail,
})

function RAGDetail() {
  const params = Route.useParams() as any
  const { id } = params
  const navigate = useNavigate()
  const [rag, setRag] = useState<RAGConfiguration | null>(null)
  const [syncs, setSyncs] = useState<DataSourceSync[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRAG()
    loadSyncs()
  }, [id])

  const loadRAG = async () => {
    try {
      setLoading(true)
      const data = await api.getRAG(Number(id))
      setRag(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load RAG')
    } finally {
      setLoading(false)
    }
  }

  const loadSyncs = async () => {
    try {
      const data = await api.listSyncs(Number(id))
      setSyncs(data)
    } catch (err) {
      console.error('Failed to load syncs:', err)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this RAG configuration?')) {
      return
    }

    try {
      await api.deleteRAG(Number(id))
      navigate({ to: '/rags' })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete RAG')
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  if (error || !rag) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error || 'RAG not found'}
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">{rag.name}</h1>
          {rag.description && (
            <p className="text-gray-600">{rag.description}</p>
          )}
          <p className="text-sm text-gray-500 mt-2">
            Collection: <span className="font-mono">{rag.collection_name}</span>
          </p>
        </div>
        <div className="flex space-x-2">
          <Link
            to="/query"
            search={{ ragId: rag.id } as any}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
          >
            Test Query
          </Link>
          <button
            onClick={handleDelete}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Configuration */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {/* Chunking */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Chunking Module</h2>
          <p className="text-lg font-medium text-blue-600 mb-3">{rag.chunking_module}</p>
          <div className="bg-gray-50 rounded p-3">
            <p className="text-xs text-gray-500 mb-1">Parameters:</p>
            <pre className="text-xs overflow-x-auto">
              {JSON.stringify(rag.chunking_params, null, 2)}
            </pre>
          </div>
        </div>

        {/* Embedding */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Embedding Module</h2>
          <p className="text-lg font-medium text-green-600 mb-3">{rag.embedding_module}</p>
          <div className="bg-gray-50 rounded p-3">
            <p className="text-xs text-gray-500 mb-1">Parameters:</p>
            <pre className="text-xs overflow-x-auto">
              {JSON.stringify(rag.embedding_params, null, 2)}
            </pre>
          </div>
        </div>

        {/* Reranking */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Reranking Module</h2>
          <p className="text-lg font-medium text-purple-600 mb-3">{rag.reranking_module}</p>
          <div className="bg-gray-50 rounded p-3">
            <p className="text-xs text-gray-500 mb-1">Parameters:</p>
            <pre className="text-xs overflow-x-auto">
              {JSON.stringify(rag.reranking_params, null, 2)}
            </pre>
          </div>
        </div>
      </div>

      {/* Synced Data Sources */}
      <div className="bg-white shadow rounded-lg p-6 mb-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Synced Data Sources</h2>
          <Link
            to="/sync"
            search={{ ragId: rag.id } as any}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Add Data Source
          </Link>
        </div>

        {syncs.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No data sources synced yet. Add a data source to get started.
          </p>
        ) : (
          <div className="space-y-3">
            {syncs.map((sync) => (
              <div key={sync.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        sync.status === 'completed' ? 'bg-green-100 text-green-800' :
                        sync.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                        sync.status === 'failed' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {sync.status}
                      </span>
                      <span className="text-sm text-gray-500">
                        DataSource ID: {sync.datasource_id}
                      </span>
                    </div>

                    {sync.status === 'in_progress' && (
                      <div className="mb-2">
                        <div className="flex justify-between text-xs text-gray-600 mb-1">
                          <span>{sync.current_step}</span>
                          <span>{sync.progress.toFixed(0)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${sync.progress}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {sync.status === 'completed' && (
                      <div className="text-sm text-gray-600">
                        {sync.num_chunks} chunks • {sync.sync_time?.toFixed(2)}s
                      </div>
                    )}

                    {sync.error_message && (
                      <p className="text-sm text-red-600 mt-1">{sync.error_message}</p>
                    )}
                  </div>

                  <div className="flex space-x-2">
                    {sync.status === 'failed' && (
                      <button
                        onClick={async () => {
                          try {
                            await api.rebuildSync(sync.id)
                            await loadSyncs()
                          } catch (err) {
                            alert('Failed to retry sync')
                          }
                        }}
                        className="px-3 py-1 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700"
                      >
                        Retry
                      </button>
                    )}
                    <button
                      onClick={async () => {
                        if (confirm('Delete this sync?')) {
                          try {
                            await api.deleteSync(sync.id)
                            await loadSyncs()
                          } catch (err) {
                            alert('Failed to delete sync')
                          }
                        }
                      }}
                      className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Metadata */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Metadata</h2>
        <div className="grid md:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Created At</p>
            <p className="font-medium">{new Date(rag.created_at).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-gray-500">Updated At</p>
            <p className="font-medium">{new Date(rag.updated_at).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-gray-500">ID</p>
            <p className="font-mono">{rag.id}</p>
          </div>
          <div>
            <p className="text-gray-500">Collection Name</p>
            <p className="font-mono">{rag.collection_name}</p>
          </div>
        </div>
      </div>
    </div>
  )
}