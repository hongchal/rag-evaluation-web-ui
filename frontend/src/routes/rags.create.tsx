import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { api, type RAGCreateRequest } from '../lib/api'

export const Route = createFileRoute('/rags/create')({
  component: CreateRAG,
})

// Module configurations
const CHUNKING_MODULES = [
  {
    value: 'recursive',
    label: 'Recursive',
    description: '텍스트를 재귀적으로 분할',
    defaultParams: { chunk_size: 512, chunk_overlap: 50 },
  },
  {
    value: 'hierarchical',
    label: 'Hierarchical',
    description: '계층적 구조로 분할',
    defaultParams: { chunk_size: 512, chunk_overlap: 100 },
  },
  {
    value: 'semantic',
    label: 'Semantic',
    description: '의미 기반 분할',
    defaultParams: { threshold: 0.7 },
  },
  {
    value: 'late_chunking',
    label: 'Late Chunking (Jina v3)',
    description: 'Jina v3 모델을 사용한 Late Chunking',
    defaultParams: { chunk_size: 512 },
  },
]

const EMBEDDING_MODULES = [
  {
    value: 'bge_m3',
    label: 'BGE-M3',
    description: 'BAAI/bge-m3 임베딩 모델',
    defaultParams: {},
  },
  {
    value: 'matryoshka',
    label: 'Matryoshka',
    description: 'Matryoshka 임베딩',
    defaultParams: {},
  },
  {
    value: 'vllm_http',
    label: 'vLLM HTTP',
    description: 'vLLM 서버를 통한 임베딩',
    defaultParams: { base_url: 'http://localhost:8001', model_name: 'BAAI/bge-m3' },
  },
]

const RERANKING_MODULES = [
  {
    value: 'none',
    label: 'None',
    description: '리랭킹 없음',
    defaultParams: {},
  },
  {
    value: 'cross_encoder',
    label: 'Cross Encoder',
    description: 'BAAI/bge-reranker-v2-m3',
    defaultParams: { model_name: 'BAAI/bge-reranker-v2-m3' },
  },
  {
    value: 'bm25',
    label: 'BM25',
    description: '키워드 기반 BM25',
    defaultParams: {},
  },
  {
    value: 'vllm_http',
    label: 'vLLM HTTP',
    description: 'vLLM 서버를 통한 리랭킹',
    defaultParams: { base_url: 'http://localhost:8001', model_name: 'BAAI/bge-reranker-v2-m3' },
  },
]

function CreateRAG() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [config, setConfig] = useState<RAGCreateRequest>({
    name: '',
    description: '',
    chunking_module: 'recursive',
    chunking_params: { chunk_size: 512, chunk_overlap: 50 },
    embedding_module: 'bge_m3',
    embedding_params: {},
    reranking_module: 'none',
    reranking_params: {},
  })

  const handleChunkingModuleChange = (value: string) => {
    const module = CHUNKING_MODULES.find((m) => m.value === value)
    setConfig({
      ...config,
      chunking_module: value,
      chunking_params: module?.defaultParams || {},
    })
  }

  const handleEmbeddingModuleChange = (value: string) => {
    const module = EMBEDDING_MODULES.find((m) => m.value === value)
    setConfig({
      ...config,
      embedding_module: value,
      embedding_params: module?.defaultParams || {},
    })
  }

  const handleRerankingModuleChange = (value: string) => {
    const module = RERANKING_MODULES.find((m) => m.value === value)
    setConfig({
      ...config,
      reranking_module: value,
      reranking_params: module?.defaultParams || {},
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const rag = await api.createRAG(config)
      navigate({ to: '/rags/$id', params: { id: rag.id.toString() } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create RAG')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Create New RAG Configuration</h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Basic Info */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Basic Information</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={config.name}
                  onChange={(e) => setConfig({ ...config, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="My RAG Configuration"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={config.description}
                  onChange={(e) => setConfig({ ...config, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="Describe your RAG configuration..."
                />
              </div>
            </div>
          </div>

          {/* Chunking Module */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Chunking Module</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Module *
                </label>
                <select
                  value={config.chunking_module}
                  onChange={(e) => handleChunkingModuleChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {CHUNKING_MODULES.map((module) => (
                    <option key={module.value} value={module.value}>
                      {module.label} - {module.description}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Parameters (JSON)
                </label>
                <textarea
                  value={JSON.stringify(config.chunking_params, null, 2)}
                  onChange={(e) => {
                    try {
                      const params = JSON.parse(e.target.value)
                      setConfig({ ...config, chunking_params: params })
                    } catch (err) {
                      // Invalid JSON, ignore
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  rows={4}
                />
              </div>
            </div>
          </div>

          {/* Embedding Module */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Embedding Module</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Module *
                </label>
                <select
                  value={config.embedding_module}
                  onChange={(e) => handleEmbeddingModuleChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {EMBEDDING_MODULES.map((module) => (
                    <option key={module.value} value={module.value}>
                      {module.label} - {module.description}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Parameters (JSON)
                </label>
                <textarea
                  value={JSON.stringify(config.embedding_params, null, 2)}
                  onChange={(e) => {
                    try {
                      const params = JSON.parse(e.target.value)
                      setConfig({ ...config, embedding_params: params })
                    } catch (err) {
                      // Invalid JSON, ignore
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  rows={4}
                />
              </div>
            </div>
          </div>

          {/* Reranking Module */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Reranking Module</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Module *
                </label>
                <select
                  value={config.reranking_module}
                  onChange={(e) => handleRerankingModuleChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {RERANKING_MODULES.map((module) => (
                    <option key={module.value} value={module.value}>
                      {module.label} - {module.description}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Parameters (JSON)
                </label>
                <textarea
                  value={JSON.stringify(config.reranking_params, null, 2)}
                  onChange={(e) => {
                    try {
                      const params = JSON.parse(e.target.value)
                      setConfig({ ...config, reranking_params: params })
                    } catch (err) {
                      // Invalid JSON, ignore
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  rows={4}
                />
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="flex justify-end space-x-4">
            <button
              type="button"
              onClick={() => navigate({ to: '/' })}
              className="px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading ? 'Creating...' : 'Create RAG'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

