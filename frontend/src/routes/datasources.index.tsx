import { createFileRoute, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type DataSource } from '../lib/api'

export const Route = createFileRoute('/datasources/')({
  component: DataSourcesPage,
})

function DataSourcesPage() {
  const [datasources, setDatasources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDataSources()
  }, [])

  const loadDataSources = async () => {
    try {
      setLoading(true)
      const data = await api.listDataSources()
      setDatasources(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data sources')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this data source? This will also remove all associated syncs.')) {
      return
    }

    try {
      await api.deleteDataSource(id)
      await loadDataSources()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete data source')
    }
  }

  const getFileIcon = (fileType: string) => {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return '📄'
      case 'txt':
        return '📝'
      case 'json':
        return '📋'
      default:
        return '📁'
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Data Sources</h1>
          <p className="text-gray-600">
            Manage uploaded files for RAG indexing
          </p>
        </div>
        <Link
          to="/upload"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Upload File
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* Data Sources List */}
      {datasources.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No data sources yet</h3>
          <p className="text-gray-500 mb-4">
            Upload files (TXT, PDF, JSON) to index them with your RAG configurations.
          </p>
          <Link
            to="/upload"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Upload File
          </Link>
        </div>
      ) : (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  File
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Uploaded
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {datasources.map((ds) => (
                <tr key={ds.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <span className="text-2xl mr-3">{getFileIcon(ds.file_type)}</span>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{ds.name}</p>
                        {ds.description && (
                          <p className="text-xs text-gray-500 line-clamp-1">{ds.description}</p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                      {ds.file_type.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatFileSize(ds.file_size)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(ds.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                    <Link
                      to="/sync"
                      search={{ datasourceId: ds.id } as any}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      Sync
                    </Link>
                    <button
                      onClick={() => handleDelete(ds.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Stats */}
      {datasources.length > 0 && (
        <div className="mt-6 grid md:grid-cols-4 gap-4">
          <div className="bg-white shadow rounded-lg p-4">
            <p className="text-sm text-gray-500 mb-1">Total Files</p>
            <p className="text-2xl font-bold text-gray-900">{datasources.length}</p>
          </div>
          <div className="bg-white shadow rounded-lg p-4">
            <p className="text-sm text-gray-500 mb-1">Total Size</p>
            <p className="text-2xl font-bold text-gray-900">
              {formatFileSize(datasources.reduce((sum, ds) => sum + ds.file_size, 0))}
            </p>
          </div>
          <div className="bg-white shadow rounded-lg p-4">
            <p className="text-sm text-gray-500 mb-1">PDF Files</p>
            <p className="text-2xl font-bold text-gray-900">
              {datasources.filter(ds => ds.file_type === 'pdf').length}
            </p>
          </div>
          <div className="bg-white shadow rounded-lg p-4">
            <p className="text-sm text-gray-500 mb-1">TXT Files</p>
            <p className="text-2xl font-bold text-gray-900">
              {datasources.filter(ds => ds.file_type === 'txt').length}
            </p>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">
          💡 How to Use Data Sources
        </h3>
        <div className="space-y-2 text-sm text-blue-800">
          <p><strong>Step 1: Upload</strong></p>
          <p className="ml-4">Upload your files (TXT, PDF, JSON) via the Upload page.</p>
          
          <p className="mt-3"><strong>Step 2: Sync</strong></p>
          <p className="ml-4">Click "Sync" to index the file with a RAG configuration. This will chunk the content, generate embeddings, and store them in Qdrant.</p>
          
          <p className="mt-3"><strong>Step 3: Query</strong></p>
          <p className="ml-4">Use the Query page to search through your indexed data.</p>
        </div>
      </div>
    </div>
  )
}

