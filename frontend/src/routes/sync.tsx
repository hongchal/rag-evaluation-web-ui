import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type RAGConfiguration, type DataSource, type DataSourceSync } from '../lib/api'

export const Route = createFileRoute('/sync')({
  component: SyncPage,
  validateSearch: (search: Record<string, unknown>) => ({
    ragId: search.ragId as number | undefined,
  }),
})

function SyncPage() {
  const navigate = useNavigate()
  const search = Route.useSearch() as any
  const { ragId: preselectedRagId } = search
  
  const [rags, setRags] = useState<RAGConfiguration[]>([])
  const [datasources, setDatasources] = useState<DataSource[]>([])
  const [syncs, setSyncs] = useState<DataSourceSync[]>([])
  const [loading, setLoading] = useState(true)

  // Form state
  const [selectedRagId, setSelectedRagId] = useState<number | null>(preselectedRagId || null)
  const [selectedDatasourceId, setSelectedDatasourceId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Auto-refresh for in-progress syncs
  useEffect(() => {
    const interval = setInterval(() => {
      if (syncs.some(s => s.status === 'in_progress')) {
        loadSyncs()
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [syncs])

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [ragsData, datasourcesData] = await Promise.all([
        api.listRAGs(),
        api.listDataSources(),
      ])
      setRags(ragsData)
      setDatasources(datasourcesData)

      if (ragsData.length > 0 && !selectedRagId) {
        setSelectedRagId(ragsData[0].id)
      }
      if (datasourcesData.length > 0) {
        setSelectedDatasourceId(datasourcesData[0].id)
      }

      await loadSyncs()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const loadSyncs = async () => {
    try {
      const syncsData = await api.listSyncs()
      setSyncs(syncsData)
    } catch (err) {
      console.error('Failed to load syncs:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedRagId || !selectedDatasourceId) {
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      await api.startSync(selectedRagId, selectedDatasourceId)
      await loadSyncs()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start sync')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRetry = async (syncId: number) => {
    try {
      await api.rebuildSync(syncId)
      await loadSyncs()
    } catch (err) {
      alert('Failed to retry sync')
    }
  }

  const handleDelete = async (syncId: number) => {
    if (!confirm('Delete this sync? This will remove all indexed chunks from Qdrant.')) {
      return
    }

    try {
      await api.deleteSync(syncId)
      await loadSyncs()
    } catch (err) {
      alert('Failed to delete sync')
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
      <h1 className="text-3xl font-bold mb-8">Data Source Synchronization</h1>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Sync Form */}
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg p-6 sticky top-8">
            <h2 className="text-xl font-semibold mb-6">Start New Sync</h2>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6 text-sm">
                {error}
              </div>
            )}

            {rags.length === 0 || datasources.length === 0 ? (
              <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded text-sm">
                {rags.length === 0 && <p>⚠️ No RAG configurations. Create one first.</p>}
                {datasources.length === 0 && <p>⚠️ No data sources. Upload data first.</p>}
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    RAG Configuration *
                  </label>
                  <select
                    value={selectedRagId || ''}
                    onChange={(e) => setSelectedRagId(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    required
                  >
                    {rags.map((rag) => (
                      <option key={rag.id} value={rag.id}>
                        {rag.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Data Source *
                  </label>
                  <select
                    value={selectedDatasourceId || ''}
                    onChange={(e) => setSelectedDatasourceId(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    required
                  >
                    {datasources.map((ds) => (
                      <option key={ds.id} value={ds.id}>
                        {ds.name} ({ds.file_type})
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={submitting || !selectedRagId || !selectedDatasourceId}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 font-medium text-sm"
                >
                  {submitting ? 'Starting...' : 'Start Sync'}
                </button>

                <p className="text-xs text-gray-500 mt-2">
                  This will chunk the data source, generate embeddings, and store them in Qdrant.
                </p>
              </form>
            )}
          </div>
        </div>

        {/* Sync List */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-6">Synchronization History</h2>

            {syncs.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                No synchronizations yet. Start one to get started.
              </p>
            ) : (
              <div className="space-y-4">
                {syncs.map((sync) => {
                  const rag = rags.find(r => r.id === sync.rag_id)
                  const datasource = datasources.find(d => d.id === sync.datasource_id)

                  return (
                    <div key={sync.id} className="border border-gray-200 rounded-lg p-5">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <span className={`px-2.5 py-1 rounded text-xs font-medium ${
                              sync.status === 'completed' ? 'bg-green-100 text-green-800' :
                              sync.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                              sync.status === 'failed' ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {sync.status}
                            </span>
                            <span className="text-sm font-medium text-gray-900">
                              {rag?.name || `RAG #${sync.rag_id}`}
                            </span>
                            <span className="text-sm text-gray-500">→</span>
                            <span className="text-sm text-gray-600">
                              {datasource?.name || `DataSource #${sync.datasource_id}`}
                            </span>
                          </div>

                          {sync.status === 'in_progress' && (
                            <div className="mb-3">
                              <div className="flex justify-between text-xs text-gray-600 mb-1">
                                <span>{sync.current_step}</span>
                                <span>{sync.progress.toFixed(0)}%</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2.5">
                                <div
                                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                                  style={{ width: `${sync.progress}%` }}
                                />
                              </div>
                            </div>
                          )}

                          {sync.status === 'completed' && (
                            <div className="flex items-center space-x-4 text-sm text-gray-600">
                              <span>✓ {sync.num_chunks} chunks indexed</span>
                              <span>• {sync.sync_time?.toFixed(2)}s</span>
                              <span className="text-xs text-gray-400">
                                {new Date(sync.completed_at || sync.updated_at).toLocaleString()}
                              </span>
                            </div>
                          )}

                          {sync.error_message && (
                            <p className="text-sm text-red-600 mt-2 bg-red-50 p-2 rounded">
                              {sync.error_message}
                            </p>
                          )}
                        </div>

                        <div className="flex space-x-2 ml-4">
                          {sync.status === 'failed' && (
                            <button
                              onClick={() => handleRetry(sync.id)}
                              className="px-3 py-1.5 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700"
                            >
                              Retry
                            </button>
                          )}
                          {sync.status !== 'in_progress' && (
                            <button
                              onClick={() => handleDelete(sync.id)}
                              className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                            >
                              Delete
                            </button>
                          )}
                          {rag && (
                            <button
                              onClick={() => navigate({ to: '/rags/$id', params: { id: rag.id.toString() } })}
                              className="px-3 py-1.5 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                            >
                              View RAG
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

