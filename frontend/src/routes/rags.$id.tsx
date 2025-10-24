import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type RAGConfiguration } from '../lib/api'

export const Route = createFileRoute('/rags/$id')({
  component: RAGDetail,
})

function RAGDetail() {
  const params = Route.useParams() as any
  const { id } = params
  const navigate = useNavigate()
  const [rag, setRag] = useState<RAGConfiguration | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRAG()
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