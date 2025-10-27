import { createFileRoute, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type EvaluationDataset, type AvailableDataset } from '../lib/api'

export const Route = createFileRoute('/datasets/')({
  component: DatasetsPage,
})

function DatasetsPage() {
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([])
  const [availableDatasets, setAvailableDatasets] = useState<AvailableDataset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  useEffect(() => {
    loadDatasets()
    loadAvailableDatasets()
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

  const loadAvailableDatasets = async () => {
    try {
      const data = await api.listAvailableDatasets()
      setAvailableDatasets(data)
    } catch (err) {
      console.error('Failed to load available datasets:', err)
    }
  }

  const handleDownload = async (datasetId: string) => {
    setDownloadingId(datasetId)
    setError(null)
    
    try {
      const result = await api.downloadDataset(datasetId)
      
      if (result.success) {
        // Background download started successfully
        alert(`✅ ${result.message}\n\n💡 You can continue using the app while the download completes in the background.`)
        // Keep the downloading state for a moment, then clear
        setTimeout(() => {
          setDownloadingId(null)
        }, 2000)
      } else {
        setError(result.message)
        setDownloadingId(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start download')
      setDownloadingId(null)
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
        <div className="flex gap-3">
          <button
            onClick={() => {
              loadDatasets()
              loadAvailableDatasets()
            }}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <Link
            to="/upload"
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Upload Dataset
          </Link>
        </div>
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

              {/* File Path */}
              <div className="mb-4">
                <p className="text-xs text-gray-500 mb-1">File Path:</p>
                <p className="text-xs font-mono bg-gray-50 p-2 rounded break-all">
                  {dataset.dataset_uri}
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

      {/* Download Section */}
      {availableDatasets.length > 0 && (
        <div className="mt-12">
          <div className="mb-6">
            <h2 className="text-2xl font-bold mb-2">📥 Download Benchmark Datasets</h2>
            <p className="text-gray-600">
              Click to download and automatically register popular evaluation datasets
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {availableDatasets.map((dataset) => {
              const isDownloading = downloadingId === dataset.id
              const existingDataset = datasets.find(d => d.name === dataset.name)
              const isDownloaded = existingDataset?.status === 'ready'
              const isBeingDownloaded = existingDataset?.status === 'downloading'
              const hasFailed = existingDataset?.status === 'failed'

              return (
                <div key={dataset.id} className="bg-white shadow rounded-lg p-6 border border-gray-200">
                  {/* Badge */}
                  <div className="flex justify-between items-start mb-3">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      dataset.size === 'small' ? 'bg-green-100 text-green-700' :
                      dataset.size === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-orange-100 text-orange-700'
                    }`}>
                      {dataset.size.toUpperCase()}
                    </span>
                    {isDownloaded && (
                      <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-700 font-medium">
                        ✓ Ready
                      </span>
                    )}
                    {isBeingDownloaded && (
                      <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700 font-medium animate-pulse">
                        ⏳ Downloading
                      </span>
                    )}
                    {hasFailed && (
                      <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-700 font-medium">
                        ❌ Failed
                      </span>
                    )}
                  </div>

                  {/* Name & Description */}
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {dataset.name}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4 min-h-12">
                    {dataset.description}
                  </p>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="bg-gray-50 rounded p-2">
                      <p className="text-xs text-gray-500">Queries</p>
                      <p className="text-lg font-bold text-gray-900">{dataset.num_queries.toLocaleString()}</p>
                    </div>
                    <div className="bg-gray-50 rounded p-2">
                      <p className="text-xs text-gray-500">Documents</p>
                      <p className="text-lg font-bold text-gray-900">{dataset.num_documents.toLocaleString()}</p>
                    </div>
                  </div>

                  {/* Time Estimate */}
                  <p className="text-xs text-gray-500 mb-4">
                    ⏱️ Estimated: {dataset.estimated_time}
                  </p>

                  {/* Download Button */}
                  {hasFailed && existingDataset?.download_error && (
                    <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                      Error: {existingDataset.download_error}
                    </div>
                  )}
                  
                  <button
                    onClick={() => handleDownload(dataset.id)}
                    disabled={isDownloading || isDownloaded || isBeingDownloaded}
                    className={`w-full px-4 py-2 rounded-md font-medium transition-colors ${
                      isDownloaded
                        ? 'bg-green-100 text-green-700 cursor-not-allowed'
                        : isBeingDownloaded
                        ? 'bg-blue-100 text-blue-700 cursor-not-allowed'
                        : hasFailed
                        ? 'bg-orange-600 text-white hover:bg-orange-700'
                        : isDownloading
                        ? 'bg-blue-400 text-white cursor-wait'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    {isDownloading ? (
                      <span className="flex items-center justify-center">
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Starting...
                      </span>
                    ) : isDownloaded ? (
                      '✓ Downloaded'
                    ) : isBeingDownloaded ? (
                      '⏳ Downloading in Background...'
                    ) : hasFailed ? (
                      '🔄 Retry Download'
                    ) : (
                      'Download Dataset'
                    )}
                  </button>
                </div>
              )
            })}
          </div>
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
          
          <p className="mt-3"><strong>Option 2: Download via buttons above</strong></p>
          <p className="ml-4">Click the download button on any available dataset to automatically download and register it.</p>
        </div>
      </div>
    </div>
  )
}

