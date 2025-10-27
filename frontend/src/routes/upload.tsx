import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { api } from '../lib/api'

export const Route = createFileRoute('/upload')({
  component: UploadPage,
})

type UploadType = 'datasource' | 'dataset'
type ProcessorType = 'pypdf2' | 'pdfplumber' | 'docling'

function UploadPage() {
  const navigate = useNavigate()
  const [uploadType, setUploadType] = useState<UploadType>('datasource')
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [processorType, setProcessorType] = useState<ProcessorType>('pdfplumber')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      if (!name) {
        setName(selectedFile.name.replace(/\.[^/.]+$/, ''))
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!file) {
      setError('Please select a file')
      return
    }

    setUploading(true)
    setError(null)

    try {
      if (uploadType === 'datasource') {
        await api.uploadDataSource(file, name, description || undefined, processorType)
        navigate({ to: '/datasources' } as any)
      } else {
        await api.uploadDataset(file, name, description || undefined)
        navigate({ to: '/datasets' } as any)
      }
    } catch (err) {
      if (err instanceof Error) {
        // Handle 409 Conflict specifically
        if (err.message.includes('409') || err.message.includes('already exists')) {
          setError(err.message + ' You can upload the same file with a different processor to compare results.')
        } else {
          setError(err.message)
        }
      } else {
        setError('Upload failed')
      }
    } finally {
      setUploading(false)
    }
  }

  const getAcceptedFileTypes = () => {
    if (uploadType === 'datasource') {
      return '.txt,.pdf,.json'
    }
    return '.json'
  }

  const getFileTypeDescription = () => {
    if (uploadType === 'datasource') {
      return 'TXT, PDF, or JSON files'
    }
    return 'JSON files with queries and documents'
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Upload Files</h1>

      <div className="max-w-3xl mx-auto">
        {/* Upload Type Selection */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Select Upload Type</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <button
              onClick={() => setUploadType('datasource')}
              className={`p-6 border-2 rounded-lg text-left transition-all ${
                uploadType === 'datasource'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-start space-x-3">
                <div className="text-3xl">📁</div>
                <div className="flex-1">
                  <h3 className="font-semibold text-lg mb-2">Data Source</h3>
                  <p className="text-sm text-gray-600">
                    Upload files to be indexed with RAG configurations. These files will be chunked, embedded, and stored in Qdrant.
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Supports: TXT, PDF, JSON
                  </p>
                </div>
              </div>
            </button>

            <button
              onClick={() => setUploadType('dataset')}
              className={`p-6 border-2 rounded-lg text-left transition-all ${
                uploadType === 'dataset'
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-start space-x-3">
                <div className="text-3xl">📊</div>
                <div className="flex-1">
                  <h3 className="font-semibold text-lg mb-2">Evaluation Dataset</h3>
                  <p className="text-sm text-gray-600">
                    Upload benchmark datasets for evaluating RAG performance. Must contain queries and ground truth documents.
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Supports: JSON (BEIR format)
                  </p>
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* Upload Form */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-6">
            Upload {uploadType === 'datasource' ? 'Data Source' : 'Dataset'}
          </h2>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                File *
              </label>
              <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md hover:border-gray-400 transition-colors">
                <div className="space-y-1 text-center">
                  {file ? (
                    <div className="flex items-center space-x-3">
                      <span className="text-4xl">
                        {file.type.includes('pdf') ? '📄' : file.type.includes('json') ? '📋' : '📝'}
                      </span>
                      <div className="text-left">
                        <p className="text-sm font-medium text-gray-900">{file.name}</p>
                        <p className="text-xs text-gray-500">
                          {(file.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setFile(null)}
                        className="text-red-600 hover:text-red-800"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <>
                      <svg
                        className="mx-auto h-12 w-12 text-gray-400"
                        stroke="currentColor"
                        fill="none"
                        viewBox="0 0 48 48"
                      >
                        <path
                          d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                          strokeWidth={2}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      <div className="flex text-sm text-gray-600">
                        <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500">
                          <span>Upload a file</span>
                          <input
                            type="file"
                            className="sr-only"
                            accept={getAcceptedFileTypes()}
                            onChange={handleFileChange}
                          />
                        </label>
                        <p className="pl-1">or drag and drop</p>
                      </div>
                      <p className="text-xs text-gray-500">{getFileTypeDescription()}</p>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter a descriptive name"
                required
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description (Optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Add a description..."
              />
            </div>

            {/* PDF Processor Selection (only for datasources with PDF files) */}
            {uploadType === 'datasource' && file?.type === 'application/pdf' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  PDF Processing Method
                </label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    type="button"
                    onClick={() => setProcessorType('pypdf2')}
                    className={`p-4 border-2 rounded-lg text-left transition-all ${
                      processorType === 'pypdf2'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="text-2xl mb-2">⚡</div>
                    <h4 className="font-semibold text-sm mb-1">PyPDF2</h4>
                    <p className="text-xs text-gray-600">Fast & Simple</p>
                    <p className="text-xs text-gray-500 mt-1">Basic text extraction</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setProcessorType('pdfplumber')}
                    className={`p-4 border-2 rounded-lg text-left transition-all ${
                      processorType === 'pdfplumber'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="text-2xl mb-2">✅</div>
                    <h4 className="font-semibold text-sm mb-1">pdfplumber</h4>
                    <p className="text-xs text-gray-600">Balanced</p>
                    <p className="text-xs text-gray-500 mt-1">Good quality + tables</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setProcessorType('docling')}
                    className={`p-4 border-2 rounded-lg text-left transition-all ${
                      processorType === 'docling'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="text-2xl mb-2">🚀</div>
                    <h4 className="font-semibold text-sm mb-1">Docling</h4>
                    <p className="text-xs text-gray-600">Best Quality</p>
                    <p className="text-xs text-gray-500 mt-1">Layout + structure</p>
                  </button>
                </div>
                
                {/* Processor Description */}
                <div className="mt-3 p-3 bg-gray-50 rounded-md">
                  <p className="text-xs text-gray-700">
                    {processorType === 'pypdf2' && (
                      <>⚡ <strong>PyPDF2</strong>: Fastest option for basic text extraction. Best for simple documents.</>
                    )}
                    {processorType === 'pdfplumber' && (
                      <>✅ <strong>pdfplumber</strong>: Recommended for most cases. Preserves tables and has good quality.</>
                    )}
                    {processorType === 'docling' && (
                      <>🚀 <strong>Docling</strong>: Advanced layout understanding with structure preservation. Perfect for complex documents, papers, and technical docs.</>
                    )}
                  </p>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div className="flex space-x-3">
              <button
                type="submit"
                disabled={uploading || !file}
                className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 font-medium"
              >
                {uploading ? 'Uploading...' : 'Upload'}
              </button>
              <button
                type="button"
                onClick={() => navigate({ to: '/' })}
                className="px-6 py-3 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>

        {/* Info Box */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">
            ℹ️ Upload Guidelines
          </h3>
          <div className="space-y-2 text-sm text-blue-800">
            {uploadType === 'datasource' ? (
              <>
                <p><strong>Data Sources</strong> are files you want to index and search through.</p>
                <ul className="list-disc ml-6 space-y-1">
                  <li>TXT files: Plain text documents</li>
                  <li>PDF files: PDF documents (text extraction)</li>
                  <li>JSON files: Structured data</li>
                </ul>
                <p className="mt-2">After uploading, go to the Sync page to index the file with a RAG configuration.</p>
              </>
            ) : (
              <>
                <p><strong>Evaluation Datasets</strong> are used to measure RAG performance.</p>
                <p>Required JSON format:</p>
                <pre className="bg-blue-100 p-2 rounded text-xs mt-2 overflow-x-auto">
{`{
  "queries": [
    {"id": "q1", "text": "query text"}
  ],
  "documents": [
    {"id": "d1", "text": "document text"}
  ],
  "qrels": {
    "q1": {"d1": 1}
  }
}`}
                </pre>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
