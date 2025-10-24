import { createFileRoute, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type EvaluationDataset } from '../lib/api'

export const Route = createFileRoute('/datasets/')({
  component: DatasetsPage,
})

function DatasetsPage() {
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDatasets()
  }, [])

  const loadDatasets = async () => {
    try {
      setLoading(true)
      const data = await api.listDatasets()
      setDatasets(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load datasets')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this dataset? This cannot be undone.')) {
      return
    }

    try {
      await api.deleteDataset(id)
      await loadDatasets()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete dataset')
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
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Evaluation Datasets</h1>
          <p className="text-gray-600">
            Manage datasets for RAG evaluation (BEIR, FRAMES, etc.)
          </p>
        </div>
        <Link
          to="/upload"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Upload Dataset
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* Datasets Grid */}
      {datasets.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No datasets yet</h3>
          <p className="text-gray-500 mb-4">
            Upload a dataset or download benchmark datasets using the scripts.
          </p>
          <div className="flex justify-center space-x-3">
            <Link
              to="/upload"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Upload Dataset
            </Link>
            <button
              onClick={() => {
                alert('Run: python backend/scripts/download_frames.py\nor: python backend/scripts/prepare_dataset.py')
              }}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Download Scripts
            </button>
          </div>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {datasets.map((dataset) => (
            <div key={dataset.id} className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow">
              {/* Header */}
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">
                    {dataset.name}
                  </h3>
                  {dataset.description && (
                    <p className="text-sm text-gray-600 line-clamp-2">
                      {dataset.description}
                    </p>
                  )}
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="bg-blue-50 rounded-lg p-3">
                  <p className="text-xs text-blue-600 font-medium mb-1">Queries</p>
                  <p className="text-2xl font-bold text-blue-900">{dataset.num_queries}</p>
                </div>
                <div className="bg-green-50 rounded-lg p-3">
                  <p className="text-xs text-green-600 font-medium mb-1">Documents</p>
                  <p className="text-2xl font-bold text-green-900">{dataset.num_documents}</p>
                </div>
              </div>

              {/* Metadata */}
              <div className="space-y-2 mb-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Format:</span>
                  <span className="font-medium text-gray-900">{dataset.format}</span>
                </div>
                {dataset.source && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Source:</span>
                    <span className="font-medium text-gray-900">{dataset.source}</span>
                  </div>
                )}
                {dataset.language && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Language:</span>
                    <span className="font-medium text-gray-900">{dataset.language}</span>
                  </div>
                )}
              </div>

              {/* File Path */}
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-1">File Path:</p>
                <p className="text-xs font-mono bg-gray-50 p-2 rounded break-all">
                  {dataset.file_path}
                </p>
              </div>

              {/* Actions */}
              <div className="flex space-x-2">
                <Link
                  to="/evaluate"
                  className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-center text-sm"
                >
                  Use for Evaluation
                </Link>
                <button
                  onClick={() => handleDelete(dataset.id)}
                  className="px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm"
                >
                  Delete
                </button>
              </div>

              {/* Footer */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-xs text-gray-400">
                  Created: {new Date(dataset.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Info Box */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">
          📚 How to Add Datasets
        </h3>
        <div className="space-y-2 text-sm text-blue-800">
          <p><strong>Option 1: Upload via UI</strong></p>
          <p className="ml-4">Click "Upload Dataset" and select a JSON file with queries and documents.</p>
          
          <p className="mt-3"><strong>Option 2: Download Benchmark Datasets</strong></p>
          <div className="ml-4 space-y-1 font-mono text-xs bg-blue-100 p-3 rounded">
            <p># Download FRAMES dataset</p>
            <p>python backend/scripts/download_frames.py</p>
            <p className="mt-2"># Download BEIR datasets</p>
            <p>python backend/scripts/prepare_dataset.py beir download-all</p>
          </div>
        </div>
      </div>
    </div>
  )
}

