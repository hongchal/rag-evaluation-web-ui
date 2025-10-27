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
  const [editingRAG, setEditingRAG] = useState<RAGConfiguration | null>(null)
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    embedding_model_name: '',
    embedding_base_url: '',
    embedding_dim: '',
    chunking_params: '',
    reranking_params: '',
  })

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

  const handleEdit = (rag: RAGConfiguration) => {
    setEditingRAG(rag)
    setEditForm({
      name: rag.name,
      description: rag.description || '',
      embedding_model_name: rag.embedding_params.model_name || '',
      embedding_base_url: rag.embedding_params.base_url || '',
      embedding_dim: rag.embedding_params.embedding_dim?.toString() || '',
      chunking_params: JSON.stringify(rag.chunking_params, null, 2),
      reranking_params: JSON.stringify(rag.reranking_params, null, 2),
    })
  }

  const handleSaveEdit = async () => {
    if (!editingRAG) return

    try {
      const updates: any = {}
      
      if (editForm.name !== editingRAG.name) {
        updates.name = editForm.name
      }
      
      if (editForm.description !== (editingRAG.description || '')) {
        updates.description = editForm.description
      }

      // Handle embedding params (individual fields)
      const embeddingChanges: any = {}
      if (editForm.embedding_model_name !== (editingRAG.embedding_params.model_name || '')) {
        embeddingChanges.model_name = editForm.embedding_model_name
      }
      if (editForm.embedding_base_url !== (editingRAG.embedding_params.base_url || '')) {
        embeddingChanges.base_url = editForm.embedding_base_url
      }
      if (editForm.embedding_dim) {
        const newDim = parseInt(editForm.embedding_dim, 10)
        if (!isNaN(newDim) && newDim !== (editingRAG.embedding_params.embedding_dim || 0)) {
          embeddingChanges.embedding_dim = newDim
        }
      }
      if (Object.keys(embeddingChanges).length > 0) {
        // 경고: embedding_params 변경은 기존 파이프라인에 영향
        if (!confirm(
          '⚠️ Embedding 파라미터를 변경하면 기존 파이프라인이 작동하지 않을 수 있습니다.\n\n' +
          '해결 방법:\n' +
          '1. 기존 파이프라인 삭제\n' +
          '2. 새 파이프라인 생성\n\n' +
          '계속하시겠습니까?'
        )) {
          return
        }
        updates.embedding_params = embeddingChanges
      }

      // Parse JSON params for chunking
      try {
        const newChunkingParams = JSON.parse(editForm.chunking_params)
        if (JSON.stringify(newChunkingParams) !== JSON.stringify(editingRAG.chunking_params)) {
          updates.chunking_params = newChunkingParams
        }
      } catch (e) {
        alert('Invalid JSON in chunking_params')
        return
      }

      // Parse JSON params for reranking
      try {
        const newRerankingParams = JSON.parse(editForm.reranking_params)
        if (JSON.stringify(newRerankingParams) !== JSON.stringify(editingRAG.reranking_params)) {
          updates.reranking_params = newRerankingParams
        }
      } catch (e) {
        alert('Invalid JSON in reranking_params')
        return
      }

      if (Object.keys(updates).length === 0) {
        alert('No changes detected')
        setEditingRAG(null)
        return
      }

      await api.updateRAG(editingRAG.id, updates)
      setEditingRAG(null)
      await loadRAGs()
      alert('RAG configuration updated successfully!')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update RAG')
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
                  onClick={() => handleEdit(rag)}
                  className="px-3 py-1 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700"
                >
                  Edit
                </button>
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

      {/* Edit Modal */}
      {editingRAG && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">RAG 설정 수정</h2>
                <button
                  onClick={() => setEditingRAG(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Name *
                  </label>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <textarea
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Module Types (Read-only) */}
                <div className="bg-gray-50 p-4 rounded-md">
                  <h3 className="font-medium text-gray-700 mb-2">모듈 타입 (읽기 전용)</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Chunking Module:</span>
                      <span className="font-mono">{editingRAG.chunking_module}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Embedding Module:</span>
                      <span className="font-mono">{editingRAG.embedding_module}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Reranking Module:</span>
                      <span className="font-mono">{editingRAG.reranking_module}</span>
                    </div>
                  </div>
                </div>

                {/* Embedding Params */}
                <div className="bg-blue-50 p-4 rounded-md space-y-3">
                  <h3 className="font-medium text-gray-700 mb-2">Embedding 파라미터</h3>
                  
                  {/* Model Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Model Name *
                    </label>
                    <input
                      type="text"
                      value={editForm.embedding_model_name}
                      onChange={(e) => setEditForm({ ...editForm, embedding_model_name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="예: Qwen/Qwen3-Embedding-0.6B"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      💡 vLLM 서버에 로드된 모델 이름을 입력하세요
                    </p>
                  </div>

                  {/* Base URL (vllm_http only) */}
                  {editingRAG?.embedding_module === 'vllm_http' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Base URL
                        </label>
                        <input
                          type="text"
                          value={editForm.embedding_base_url}
                          onChange={(e) => setEditForm({ ...editForm, embedding_base_url: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="예: https://example.com:8000"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Embedding Dimension *
                        </label>
                        <input
                          type="number"
                          value={editForm.embedding_dim}
                          onChange={(e) => setEditForm({ ...editForm, embedding_dim: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="예: 512, 768, 1024, 4096"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          💡 일반적인 값: 512, 768, 1024, 1536, 4096
                        </p>
                      </div>
                    </>
                  )}

                  {/* Current params display */}
                  <div className="text-xs text-gray-600 bg-white p-2 rounded border border-gray-200">
                    <div className="font-medium mb-1">현재 전체 설정:</div>
                    <pre className="overflow-x-auto">{JSON.stringify(editingRAG?.embedding_params, null, 2)}</pre>
                  </div>
                </div>

                {/* Chunking Params */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Chunking Parameters (JSON) *
                  </label>
                  <textarea
                    value={editForm.chunking_params}
                    onChange={(e) => setEditForm({ ...editForm, chunking_params: e.target.value })}
                    rows={4}
                    className="w-full px-3 py-2 font-mono text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder='{"chunk_size": 512, "chunk_overlap": 50}'
                  />
                </div>

                {/* Reranking Params */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Reranking Parameters (JSON) *
                  </label>
                  <textarea
                    value={editForm.reranking_params}
                    onChange={(e) => setEditForm({ ...editForm, reranking_params: e.target.value })}
                    rows={4}
                    className="w-full px-3 py-2 font-mono text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder='{"model_name": "...", "top_k": 10}'
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setEditingRAG(null)}
                  className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

