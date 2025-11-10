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
    description: '의미 기반 분할 (embedder 필요)',
    defaultParams: { 
      similarity_threshold: 0.75,
      min_chunk_tokens: 100,
      max_chunk_tokens: 800,
      embedder_module: 'bge_m3',
      embedder_params: {}
    },
  },
  {
    value: 'late_chunking',
    label: 'Late Chunking ⚡',
    description: 'Jina v3 전용 (자동 선택, 10배 빠름)',
    defaultParams: { 
      sentences_per_chunk: 3,
      min_chunk_tokens: 50,
      max_chunk_tokens: 512
    },
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
    defaultParams: { 
      model_name: 'Qwen/Qwen3-Embedding-0.6B',
      embedding_dim: 4096 
    },
  },
  {
    value: 'jina_late_chunking',
    label: 'Jina v3 (Late Chunking 최적화 지원) ⚡',
    description: 'Late Chunking과 함께 사용 시 10배 빠름',
    defaultParams: {
      model_name: 'jinaai/jina-embeddings-v3'
    },
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
    defaultParams: { 
      model_name: 'BAAI/bge-reranker-v2-m3' 
    },
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
    
    // Late Chunking 선택 시 Jina embedder 강제
    let newConfig = {
      ...config,
      chunking_module: value,
      chunking_params: module?.defaultParams || {},
    }
    
    if (value === 'late_chunking') {
      const jinaModule = EMBEDDING_MODULES.find((m) => m.value === 'jina_late_chunking')
      newConfig = {
        ...newConfig,
        embedding_module: 'jina_late_chunking',
        embedding_params: jinaModule?.defaultParams || {},
      }
    }
    
    setConfig(newConfig)
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

              {/* Semantic Chunking: Special UI for embedder selection */}
              {config.chunking_module === 'semantic' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Embedder Module (for semantic chunking) *
                  </label>
                  <select
                    value={config.chunking_params.embedder_module || 'bge_m3'}
                    onChange={(e) => {
                      const embedderModule = EMBEDDING_MODULES.find((m) => m.value === e.target.value)
                      setConfig({
                        ...config,
                        chunking_params: {
                          ...config.chunking_params,
                          embedder_module: e.target.value,
                          embedder_params: embedderModule?.defaultParams || {},
                        },
                      })
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {EMBEDDING_MODULES.map((module) => (
                      <option key={module.value} value={module.value}>
                        {module.label} - {module.description}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-gray-500">
                    💡 Chunking용 임베더를 선택하세요 (Retrieval과 다를 수 있음)
                  </p>
                </div>
              )}

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
                  rows={config.chunking_module === 'semantic' ? 6 : 4}
                />
                {config.chunking_module === 'semantic' && (
                  <p className="mt-1 text-xs text-gray-500">
                    ℹ️ embedder_module과 embedder_params는 위 드롭다운으로 관리됩니다
                  </p>
                )}
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

              {/* vLLM HTTP: Special UI for common parameters */}
              {config.embedding_module === 'vllm_http' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Model Name *
                    </label>
                    <input
                      type="text"
                      value={config.embedding_params.model_name || ''}
                      onChange={(e) => setConfig({
                        ...config,
                        embedding_params: {
                          ...config.embedding_params,
                          model_name: e.target.value
                        }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="예: Qwen/Qwen3-Embedding-0.6B"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      💡 vLLM 서버에 로드된 모델 이름을 입력하세요
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Base URL (선택사항)
                    </label>
                    <input
                      type="text"
                      value={config.embedding_params.base_url || ''}
                      onChange={(e) => setConfig({
                        ...config,
                        embedding_params: {
                          ...config.embedding_params,
                          base_url: e.target.value
                        }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="비워두면 환경변수 기본값 사용 (예: http://localhost:8000)"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      💡 비워두면 backend의 VLLM_EMBEDDING_URL 환경변수 사용
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Embedding Dimension *
                    </label>
                    <input
                      type="number"
                      value={config.embedding_params.embedding_dim || ''}
                      onChange={(e) => setConfig({
                        ...config,
                        embedding_params: {
                          ...config.embedding_params,
                          embedding_dim: parseInt(e.target.value, 10) || 1024
                        }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="예: 512, 768, 1024, 4096"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      💡 일반적인 값: 512, 768, 1024, 1536, 4096
                    </p>
                  </div>
                </>
              )}

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
                {config.embedding_module === 'vllm_http' && (
                  <p className="mt-1 text-xs text-gray-500">
                    ℹ️ model_name, base_url, embedding_dim은 위 필드로 관리됩니다
                  </p>
                )}
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

              {/* vLLM HTTP: Special UI for common parameters */}
              {config.reranking_module === 'vllm_http' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Model Name *
                    </label>
                    <input
                      type="text"
                      value={config.reranking_params.model_name || ''}
                      onChange={(e) => setConfig({
                        ...config,
                        reranking_params: {
                          ...config.reranking_params,
                          model_name: e.target.value
                        }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="예: BAAI/bge-reranker-v2-m3"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      💡 vLLM 서버에 로드된 리랭킹 모델 이름을 입력하세요
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Base URL (선택사항)
                    </label>
                    <input
                      type="text"
                      value={config.reranking_params.base_url || ''}
                      onChange={(e) => setConfig({
                        ...config,
                        reranking_params: {
                          ...config.reranking_params,
                          base_url: e.target.value
                        }
                      })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="비워두면 환경변수 기본값 사용 (예: http://localhost:8002)"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      💡 비워두면 backend의 VLLM_RERANKING_URL 환경변수 사용
                    </p>
                  </div>
                </>
              )}

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
                {config.reranking_module === 'vllm_http' && (
                  <p className="mt-1 text-xs text-gray-500">
                    ℹ️ model_name, base_url은 위 필드로 관리됩니다
                  </p>
                )}
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

