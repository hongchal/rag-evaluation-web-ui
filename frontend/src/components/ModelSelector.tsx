import { useState, useEffect } from 'react'
import type { ModelConfig } from '../hooks/useChatSession'
import { api } from '../lib/api'

interface ModelSelectorProps {
  config: ModelConfig
  onChange: (config: ModelConfig) => void
  disabled?: boolean
}

interface ClaudeModel {
  id: string
  name: string
  description: string
  context_window: number
  max_output: number
}

export function ModelSelector({ config, onChange, disabled }: ModelSelectorProps) {
  const [localConfig, setLocalConfig] = useState<ModelConfig>(config)
  const [showPrompt, setShowPrompt] = useState(false)
  const [claudeModels, setClaudeModels] = useState<ClaudeModel[]>([])
  const [systemPrompt, setSystemPrompt] = useState<string>('')
  const [isLoadingModels, setIsLoadingModels] = useState(true)

  useEffect(() => {
    setLocalConfig(config)
  }, [config])

  // Load Claude models and system prompt on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [modelsData, promptData] = await Promise.all([
          api.listClaudeModels(),
          api.getSystemPrompt(),
        ])
        setClaudeModels(modelsData.models)
        setSystemPrompt(promptData.prompt)
      } catch (error) {
        console.error('Failed to load model data:', error)
      } finally {
        setIsLoadingModels(false)
      }
    }
    loadData()
  }, [])

  const handleModelTypeChange = (type: 'claude' | 'vllm') => {
    const newConfig: ModelConfig = {
      ...localConfig,
      type,
      apiKey: type === 'claude' ? localConfig.apiKey : undefined,
      endpoint: type === 'vllm' ? localConfig.endpoint : undefined,
    }
    setLocalConfig(newConfig)
    onChange(newConfig)
  }

  const handleFieldChange = (field: keyof ModelConfig, value: any) => {
    const newConfig = { ...localConfig, [field]: value }
    setLocalConfig(newConfig)
    onChange(newConfig)
  }

  const handleParamChange = (param: keyof ModelConfig['parameters'], value: number) => {
    const newConfig = {
      ...localConfig,
      parameters: { ...localConfig.parameters, [param]: value },
    }
    setLocalConfig(newConfig)
    onChange(newConfig)
  }

  return (
    <div className="space-y-4">
      {/* Model Type Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Model Type
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => handleModelTypeChange('claude')}
            disabled={disabled}
            className={`flex-1 px-4 py-2 rounded-md font-medium transition-colors ${
              localConfig.type === 'claude'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            Claude
          </button>
          <button
            type="button"
            onClick={() => handleModelTypeChange('vllm')}
            disabled={disabled}
            className={`flex-1 px-4 py-2 rounded-md font-medium transition-colors ${
              localConfig.type === 'vllm'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            vLLM
          </button>
        </div>
      </div>

      {/* Model Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Model Name
        </label>
        {localConfig.type === 'claude' ? (
          <>
            {isLoadingModels ? (
              <div className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500">
                Loading models...
              </div>
            ) : claudeModels.length > 0 ? (
              <select
                value={localConfig.modelName}
                onChange={(e) => handleFieldChange('modelName', e.target.value)}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                {claudeModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={localConfig.modelName}
                onChange={(e) => handleFieldChange('modelName', e.target.value)}
                disabled={disabled}
                placeholder="claude-3-5-sonnet-20241022"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            )}
            {!isLoadingModels && claudeModels.length > 0 && (
              <p className="mt-1 text-xs text-gray-500">
                {claudeModels.find((m) => m.id === localConfig.modelName)?.description}
              </p>
            )}
          </>
        ) : (
          <input
            type="text"
            value={localConfig.modelName}
            onChange={(e) => handleFieldChange('modelName', e.target.value)}
            disabled={disabled}
            placeholder="llama-2-70b"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        )}
      </div>

      {/* Claude API Key */}
      {localConfig.type === 'claude' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            API Key
          </label>
          <input
            type="password"
            value={localConfig.apiKey || ''}
            onChange={(e) => handleFieldChange('apiKey', e.target.value)}
            disabled={disabled}
            placeholder="sk-ant-xxxxxxxxxxxxx"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <p className="mt-1 text-xs text-gray-500">
            Your API key is never stored on the server
          </p>
        </div>
      )}

      {/* vLLM Endpoint */}
      {localConfig.type === 'vllm' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Endpoint URL
          </label>
          <input
            type="url"
            value={localConfig.endpoint || ''}
            onChange={(e) => handleFieldChange('endpoint', e.target.value)}
            disabled={disabled}
            placeholder="http://localhost:8001/v1/completions"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        </div>
      )}

      {/* Generation Parameters */}
      <div className="pt-4 border-t border-gray-200">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Parameters</h3>
        {localConfig.type === 'claude' && 
         (localConfig.modelName.includes('-4-') || localConfig.modelName.includes('-4.')) && (
          <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded p-2 mb-3">
            ℹ️ Claude 4.x 모델은 Temperature만 사용합니다 (Top P는 무시됨)
          </p>
        )}
        
        {/* Temperature */}
        <div className="mb-4">
          <div className="flex justify-between mb-2">
            <label className="text-sm text-gray-600">Temperature</label>
            <span className="text-sm font-medium text-gray-900">
              {localConfig.parameters.temperature.toFixed(1)}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={localConfig.parameters.temperature}
            onChange={(e) => handleParamChange('temperature', parseFloat(e.target.value))}
            disabled={disabled}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer disabled:cursor-not-allowed"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Deterministic</span>
            <span>Creative</span>
          </div>
        </div>

        {/* Max Tokens */}
        <div className="mb-4">
          <div className="flex justify-between mb-2">
            <label className="text-sm text-gray-600">Max Tokens</label>
            <span className="text-sm font-medium text-gray-900">
              {localConfig.parameters.maxTokens}
            </span>
          </div>
          <input
            type="range"
            min="100"
            max="4000"
            step="100"
            value={localConfig.parameters.maxTokens}
            onChange={(e) => handleParamChange('maxTokens', parseInt(e.target.value))}
            disabled={disabled}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer disabled:cursor-not-allowed"
          />
        </div>

        {/* Top P */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm text-gray-600">Top P</label>
            <span className="text-sm font-medium text-gray-900">
              {localConfig.parameters.topP.toFixed(2)}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={localConfig.parameters.topP}
            onChange={(e) => handleParamChange('topP', parseFloat(e.target.value))}
            disabled={disabled}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer disabled:cursor-not-allowed"
          />
        </div>
      </div>

      {/* System Prompt Preview */}
      <div className="pt-4 border-t border-gray-200">
        <button
          type="button"
          onClick={() => setShowPrompt(!showPrompt)}
          className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 bg-gray-50 rounded-md hover:bg-gray-100 transition-colors"
        >
          <span>📝 View System Prompt</span>
          <svg
            className={`w-4 h-4 transition-transform ${showPrompt ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {showPrompt && (
          <div className="mt-3">
            {systemPrompt ? (
              <>
                <div className="bg-gray-50 border border-gray-200 rounded-md p-3 max-h-64 overflow-y-auto">
                  <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                    {systemPrompt}
                  </pre>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  This prompt guides the AI to answer questions based only on provided context.
                </p>
              </>
            ) : (
              <div className="text-sm text-gray-500 p-3">
                Loading prompt...
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

