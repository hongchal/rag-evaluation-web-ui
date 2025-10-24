import { createFileRoute, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api, type RAGConfiguration } from '../lib/api'

export const Route = createFileRoute('/rags/')({
  component: RAGList,
})

function RAGList() {
  const [rags, setRags] = useState<RAGConfiguration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRAGs()
  }, [])

  const loadRAGs = async () => {
    try {
      setLoading(true)
      const data = await api.listRAGs()
      setRags(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load RAGs')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this RAG configuration?')) {
      return
    }

    try {
      await api.deleteRAG(id)
      await loadRAGs()
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
        <h1 className="text-3xl font-bold">RAG Configurations</h1>
        <Link
          to="/rags/create"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Create New RAG
        </Link>
      </div>

      {rags.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-8 text-center">
          <p className="text-gray-500 mb-4">No RAG configurations yet</p>
          <Link
            to="/rags/create"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Create Your First RAG
          </Link>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {rags.map((rag) => (
            <div key={rag.id} className="bg-white shadow rounded-lg p-6">
              <h3 className="text-xl font-semibold mb-2">{rag.name}</h3>
              {rag.description && (
                <p className="text-gray-600 text-sm mb-4">{rag.description}</p>
              )}

              <div className="space-y-2 text-sm mb-4">
                <div className="flex justify-between">
                  <span className="text-gray-500">Chunking:</span>
                  <span className="font-medium">{rag.chunking_module}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Embedding:</span>
                  <span className="font-medium">{rag.embedding_module}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Reranking:</span>
                  <span className="font-medium">{rag.reranking_module}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Collection:</span>
                  <span className="font-mono text-xs">{rag.collection_name}</span>
                </div>
              </div>

              <div className="flex justify-end space-x-2">
                <Link
                  to="/query"
                  search={{ ragId: rag.id }}
                  className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Test
                </Link>
                <Link
                  to="/rags/$id"
                  params={{ id: rag.id.toString() }}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  View
                </Link>
                <button
                  onClick={() => handleDelete(rag.id)}
                  className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
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

