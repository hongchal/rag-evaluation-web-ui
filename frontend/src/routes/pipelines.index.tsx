import { createFileRoute, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type Pipeline } from '../lib/api'

export const Route = createFileRoute('/pipelines/')({
  component: PipelineList,
})

function PipelineList() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'normal' | 'test'>('all')
  
  // Search and Sort states
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'name-asc' | 'name-desc' | 'created-asc' | 'created-desc' | 'status'>('created-desc')

  useEffect(() => {
    loadPipelines(false) // Initial load or filter change with loading state
  }, [filter])

  // Auto-refresh when there are indexing/pending pipelines
  useEffect(() => {
    const hasIndexingPipelines = pipelines.some(
      (p) => p.status === 'indexing' || p.status === 'pending'
    )

    if (!hasIndexingPipelines) return

    const interval = setInterval(() => {
      loadPipelines(true) // Silent refresh without loading state
    }, 5000) // Refresh every 5 seconds

    return () => clearInterval(interval)
  }, [pipelines, filter])

  const loadPipelines = async (silent: boolean = false) => {
    try {
      if (!silent) {
        setLoading(true)
      }
      const data = await api.listPipelines(filter === 'all' ? undefined : filter)
      setPipelines(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pipelines')
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-700'
      case 'indexing':
        return 'bg-blue-100 text-blue-700'
      case 'ready':
        return 'bg-green-100 text-green-700'
      case 'failed':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'pending':
        return '대기 중'
      case 'indexing':
        return '인덱싱 중'
      case 'ready':
        return '사용 가능'
      case 'failed':
        return '실패'
      default:
        return status
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this pipeline? This will remove all indexed data for this pipeline.')) {
      return
    }

    try {
      await api.deletePipeline(id)
      await loadPipelines()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete pipeline')
    }
  }

  // Filter and sort pipelines
  const filteredAndSortedPipelines = pipelines
    .filter((pipeline) => {
      if (!searchQuery) return true
      const query = searchQuery.toLowerCase()
      return (
        pipeline.name.toLowerCase().includes(query) ||
        (pipeline.description && pipeline.description.toLowerCase().includes(query)) ||
        pipeline.rag.name.toLowerCase().includes(query) ||
        (pipeline.pipeline_type === 'normal' && 
          pipeline.datasources?.some(ds => ds.name.toLowerCase().includes(query))) ||
        (pipeline.pipeline_type === 'test' && 
          pipeline.dataset?.name.toLowerCase().includes(query))
      )
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'name-asc':
          return a.name.localeCompare(b.name)
        case 'name-desc':
          return b.name.localeCompare(a.name)
        case 'created-asc':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        case 'created-desc':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'status': {
          // Status priority: ready > indexing > pending > failed
          const statusOrder: Record<string, number> = {
            'ready': 0,
            'indexing': 1,
            'pending': 2,
            'failed': 3,
          }
          return (statusOrder[a.status] || 99) - (statusOrder[b.status] || 99)
        }
        default:
          return 0
      }
    })

  if (loading) {
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

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Pipelines</h1>
          <p className="text-gray-600 mt-2">
            Manage your RAG pipelines (RAG + Data Sources/Datasets)
          </p>
        </div>
        <Link
          to="/pipelines/create"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Create New Pipeline
        </Link>
      </div>

      {/* Filter */}
      <div className="mb-6 flex gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-md ${
            filter === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-white border border-gray-300 hover:bg-gray-50'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setFilter('normal')}
          className={`px-4 py-2 rounded-md ${
            filter === 'normal'
              ? 'bg-blue-600 text-white'
              : 'bg-white border border-gray-300 hover:bg-gray-50'
          }`}
        >
          Normal
        </button>
        <button
          onClick={() => setFilter('test')}
          className={`px-4 py-2 rounded-md ${
            filter === 'test'
              ? 'bg-blue-600 text-white'
              : 'bg-white border border-gray-300 hover:bg-gray-50'
          }`}
        >
          Test
        </button>
      </div>

      {/* Search and Sort Controls */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        {/* Search Input */}
        <div className="flex-1">
          <div className="relative">
            <input
              type="text"
              placeholder="Search by name, description, RAG, or data sources..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <svg
              className="absolute left-3 top-2.5 h-5 w-5 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        {/* Sort Dropdown */}
        <div className="sm:w-64">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="created-desc">최신순</option>
            <option value="created-asc">오래된순</option>
            <option value="name-asc">이름 (A-Z)</option>
            <option value="name-desc">이름 (Z-A)</option>
            <option value="status">상태별 (Ready → Failed)</option>
          </select>
        </div>
      </div>

      {/* Results count */}
      {searchQuery && (
        <div className="mb-4 text-sm text-gray-600">
          {filteredAndSortedPipelines.length}개의 결과를 찾았습니다 (전체 {pipelines.length}개 중)
        </div>
      )}

      {pipelines.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-8 text-center">
          <p className="text-gray-500 mb-4">No pipelines yet</p>
          <Link
            to="/pipelines/create"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Create Your First Pipeline
          </Link>
        </div>
      ) : filteredAndSortedPipelines.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-8 text-center">
          <p className="text-gray-500 mb-4">검색 결과가 없습니다</p>
          <button
            onClick={() => setSearchQuery('')}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            검색 초기화
          </button>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filteredAndSortedPipelines.map((pipeline) => (
            <div
              key={pipeline.id}
              className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <h2 className="text-xl font-semibold">{pipeline.name}</h2>
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        pipeline.pipeline_type === 'normal'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-purple-100 text-purple-700'
                      }`}
                    >
                      {pipeline.pipeline_type === 'normal' ? 'NORMAL' : 'TEST'}
                    </span>
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${getStatusColor(
                        pipeline.status
                      )}`}
                    >
                      {getStatusLabel(pipeline.status)}
                    </span>
                  </div>
                  {pipeline.description && (
                    <p className="text-sm text-gray-600 mb-3">
                      {pipeline.description}
                    </p>
                  )}
                  
                  {/* Indexing progress bar */}
                  {pipeline.status === 'indexing' && pipeline.indexing_progress != null && (
                    <div className="mb-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-gray-600">인덱싱 진행률:</span>
                        <span className="text-xs font-medium text-blue-600">
                          {pipeline.indexing_progress.toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all"
                          style={{ width: `${pipeline.indexing_progress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                  
                  {/* Error message */}
                  {pipeline.status === 'failed' && pipeline.indexing_error && (
                    <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                      <strong>에러:</strong> {pipeline.indexing_error}
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex items-center text-sm">
                  <span className="text-gray-500 w-20">RAG:</span>
                  <Link
                    to={`/rags/${pipeline.rag.id}` as any}
                    className="text-blue-600 hover:underline"
                  >
                    {pipeline.rag.name}
                  </Link>
                </div>

                {pipeline.pipeline_type === 'normal' && pipeline.datasources && (
                  <div className="flex items-start text-sm">
                    <span className="text-gray-500 w-20">Sources:</span>
                    <div className="flex-1">
                      {pipeline.datasources.length > 0 ? (
                        <ul className="list-disc list-inside">
                          {pipeline.datasources.map((ds) => (
                            <li key={ds.id} className="text-gray-700">
                              {ds.name}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-gray-400">No data sources</span>
                      )}
                    </div>
                  </div>
                )}

                {pipeline.pipeline_type === 'test' && pipeline.dataset && (
                  <div className="flex items-center text-sm">
                    <span className="text-gray-500 w-20">Dataset:</span>
                    <Link
                      to={`/datasets/${pipeline.dataset.id}` as any}
                      className="text-blue-600 hover:underline"
                    >
                      {pipeline.dataset.name}
                    </Link>
                  </div>
                )}

                <div className="flex items-center text-sm text-gray-500">
                  <span className="w-20">Created:</span>
                  <span>{new Date(pipeline.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t">
                <Link
                  to={`/pipelines/${pipeline.id}` as any}
                  className="flex-1 px-3 py-2 text-center bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  View
                </Link>
                {pipeline.pipeline_type === 'normal' && (
                  <Link
                    to="/retrieve"
                    search={{ pipelineId: pipeline.id }}
                    className="flex-1 px-3 py-2 text-center bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  >
                    Query
                  </Link>
                )}
                {pipeline.pipeline_type === 'test' && (
                  <Link
                    to="/evaluate"
                    search={{ pipeline_ids: [pipeline.id] }}
                    className="flex-1 px-3 py-2 text-center bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                  >
                    Evaluate
                  </Link>
                )}
                <button
                  onClick={() => handleDelete(pipeline.id)}
                  className="px-3 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

