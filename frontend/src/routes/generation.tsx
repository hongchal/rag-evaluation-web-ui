import { useState, useRef, useEffect } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { api } from '../lib/api'
import { useChatSession, type ModelConfig } from '../hooks/useChatSession'
import { ChatMessage } from '../components/ChatMessage'
import { ModelSelector } from '../components/ModelSelector'
import { SourceViewer } from '../components/SourceViewer'
import { PipelineCombobox } from '../components/PipelineCombobox'
import type { RetrievedChunk } from '../hooks/useChatSession'

export const Route = createFileRoute('/generation')({
  component: GenerationTab,
})

function GenerationTab() {
  // State
  const [pipelines, setPipelines] = useState<any[]>([])
  const [selectedPipelineId, setSelectedPipelineId] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [inputMessage, setInputMessage] = useState('')
  const [viewingSources, setViewingSources] = useState<RetrievedChunk[] | null>(null)
  const [showModelConfig, setShowModelConfig] = useState(false)
  const [showSessions, setShowSessions] = useState(false)
  const [savedSessions, setSavedSessions] = useState<any[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const [sessionTitle, setSessionTitle] = useState<string>('')
  const [isSaving, setIsSaving] = useState(false)
  const [promptTemplates, setPromptTemplates] = useState<any[]>([])
  const [selectedPromptId, setSelectedPromptId] = useState<number | null>(null)
  const [customSystemPrompt, setCustomSystemPrompt] = useState('')
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Default model configuration
  const [modelConfig, setModelConfig] = useState<ModelConfig>({
    type: 'claude',
    modelName: 'claude-sonnet-4-5-20250929', // Latest Claude Sonnet 4.5
    apiKey: '',
    parameters: {
      temperature: 0.7,
      maxTokens: 1000,
      topP: 0.9,
    },
  })

  const { session, addMessage, clearSession, updateModelConfig } = useChatSession(
    selectedPipelineId || 0,
    modelConfig
  )

  // Load pipelines on mount
  useEffect(() => {
    loadPipelines()
  }, [])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [session.messages])

  // Focus input when pipeline is selected
  useEffect(() => {
    if (selectedPipelineId && inputRef.current) {
      inputRef.current.focus()
    }
  }, [selectedPipelineId])

  const loadPipelines = async () => {
    try {
      const data = await api.listPipelines()
      setPipelines(data)
      if (data.length > 0 && !selectedPipelineId) {
        setSelectedPipelineId(data[0].id)
      }
    } catch (err) {
      console.error('Failed to load pipelines:', err)
      setError('Failed to load pipelines')
    }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !selectedPipelineId || isLoading) return

    // Validate model configuration
    if (modelConfig.type === 'claude' && !modelConfig.apiKey) {
      setError('Please provide Claude API key in model configuration')
      setShowModelConfig(true)
      return
    }

    if (modelConfig.type === 'vllm' && !modelConfig.endpoint) {
      setError('Please provide vLLM endpoint in model configuration')
      setShowModelConfig(true)
      return
    }

    const userMessage = inputMessage.trim()
    setInputMessage('')
    setError('')
    setIsLoading(true)

    // Add user message
    addMessage({
      role: 'user',
      content: userMessage,
    })

    try {
      const response = await api.answer({
        pipeline_id: selectedPipelineId,
        query: userMessage,
        top_k: 10,
        system_prompt: customSystemPrompt || undefined,
        llm_config: {
          type: modelConfig.type,
          model_name: modelConfig.modelName,
          api_key: modelConfig.apiKey,
          endpoint: modelConfig.endpoint,
          parameters: {
            temperature: modelConfig.parameters.temperature,
            max_tokens: modelConfig.parameters.maxTokens,
            top_p: modelConfig.parameters.topP,
          },
        },
      })

      // Add assistant message
      addMessage({
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      })
    } catch (err: any) {
      console.error('Failed to generate answer:', err)
      const errorMessage = err.message || 'Failed to generate answer. Please try again.'
      setError(errorMessage)
      
      // Add error message to chat
      addMessage({
        role: 'assistant',
        content: `❌ Error: ${errorMessage}`,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleModelConfigChange = (newConfig: ModelConfig) => {
    setModelConfig(newConfig)
    updateModelConfig(newConfig)
  }

  const handleClearChat = () => {
    if (confirm('Are you sure you want to clear the chat history?')) {
      clearSession()
      setCurrentSessionId(null)
      setSessionTitle('')
      setError('')
    }
  }

  const handleSaveSession = async () => {
    if (!selectedPipelineId || session.messages.length === 0) {
      setError('No messages to save')
      return
    }

    const title = sessionTitle.trim() || `Chat - ${new Date().toLocaleString()}`
    setIsSaving(true)
    setError('')

    try {
      const sessionData = {
        title,
        pipeline_id: selectedPipelineId,
        model_type: modelConfig.type,
        model_name: modelConfig.modelName,
        llm_config: modelConfig,
        messages: session.messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          sources: msg.sources,
        })),
      }

      if (currentSessionId) {
        // Update existing session
        await api.updateChatSession(currentSessionId, {
          title,
          messages: session.messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            sources: msg.sources,
          })),
        })
      } else {
        // Create new session
        const response = await api.createChatSession(sessionData)
        setCurrentSessionId(response.id)
      }

      alert('Session saved successfully!')
      await loadSessions()
    } catch (err: any) {
      console.error('Failed to save session:', err)
      setError(`Failed to save session: ${err.message}`)
    } finally {
      setIsSaving(false)
    }
  }

  const loadSessions = async () => {
    try {
      const sessions = await api.listChatSessions()
      setSavedSessions(sessions)
    } catch (err) {
      console.error('Failed to load sessions:', err)
    }
  }

  const handleLoadSession = async (sessionId: number) => {
    try {
      const sessionData = await api.getChatSession(sessionId)
      
      // Check if pipeline still exists
      if (!sessionData.pipeline_id) {
        alert('⚠️ Warning: The pipeline associated with this chat session has been deleted.\n\nYou can view the chat history, but you cannot send new messages.')
      }
      
      // Update pipeline
      setSelectedPipelineId(sessionData.pipeline_id)
      
      // Update model config
      if (sessionData.llm_config) {
        setModelConfig(sessionData.llm_config)
        updateModelConfig(sessionData.llm_config)
      }
      
      // Clear current session and load messages
      clearSession()
      setTimeout(() => {
        sessionData.messages.forEach((msg: any) => {
          addMessage({
            role: msg.role,
            content: msg.content,
            sources: msg.sources,
          })
        })
      }, 100)
      
      setCurrentSessionId(sessionData.id)
      setSessionTitle(sessionData.title)
      setShowSessions(false)
      
    } catch (err: any) {
      console.error('Failed to load session:', err)
      setError(`Failed to load session: ${err.message}`)
    }
  }

  const handleDeleteSession = async (sessionId: number) => {
    if (!confirm('Are you sure you want to delete this session?')) return

    try {
      await api.deleteChatSession(sessionId)
      await loadSessions()
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null)
        setSessionTitle('')
      }
    } catch (err: any) {
      console.error('Failed to delete session:', err)
      setError(`Failed to delete session: ${err.message}`)
    }
  }

  // Prompt Template Functions
  const loadPromptTemplates = async () => {
    try {
      const response = await api.listPromptTemplates()
      setPromptTemplates(response.items)
    } catch (err) {
      console.error('Failed to load prompt templates:', err)
    }
  }

  const handleSelectPrompt = (promptId: number) => {
    const prompt = promptTemplates.find(p => p.id === promptId)
    if (prompt) {
      setSelectedPromptId(promptId)
      setCustomSystemPrompt(prompt.system_prompt)
    }
  }

  useEffect(() => {
    loadPromptTemplates()
  }, [])

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Generation</h1>
        <p className="text-gray-600">Chat with your documents using LLM-powered generation</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Panel - Configuration */}
        <div className="lg:col-span-1 space-y-6">
          {/* Pipeline Selection */}
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline</h2>
            <PipelineCombobox
              pipelines={pipelines}
              selectedPipelineId={selectedPipelineId}
              onSelect={setSelectedPipelineId}
              disabled={isLoading}
              placeholder="Select a pipeline"
            />
          </div>

          {/* Model Configuration */}
          <div className="bg-white rounded-lg shadow">
            <button
              onClick={() => setShowModelConfig(!showModelConfig)}
              className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 transition-colors rounded-t-lg"
            >
              <h2 className="text-lg font-semibold text-gray-900">Model Config</h2>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform ${
                  showModelConfig ? 'rotate-180' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {showModelConfig && (
              <div className="px-4 pb-4 border-t border-gray-200">
                <div className="pt-4">
                  <ModelSelector
                    config={modelConfig}
                    onChange={handleModelConfigChange}
                    disabled={isLoading}
                  />
                </div>
              </div>
            )}
          </div>

          {/* System Prompt Selector */}
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">System Prompt</h2>
            
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Template
                </label>
                <select
                  value={selectedPromptId || ''}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value) {
                      handleSelectPrompt(Number(value))
                    } else {
                      setSelectedPromptId(null)
                      setCustomSystemPrompt('')
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                >
                  <option value="">Default (None)</option>
                  {promptTemplates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Manage prompts in the{' '}
                  <a href="/prompts" className="text-blue-600 hover:text-blue-700 underline">
                    Prompts tab
                  </a>
                </p>
              </div>

              {customSystemPrompt && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Current Prompt
                  </label>
                  <div className="bg-gray-50 rounded-md p-3 border border-gray-200">
                    <p className="text-xs text-gray-700 whitespace-pre-wrap font-mono line-clamp-4">
                      {customSystemPrompt}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Chat Actions */}
          <div className="space-y-2">
            {session.messages.length > 0 && (
              <>
                {/* Session Title Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Session Title
                  </label>
                  <input
                    type="text"
                    value={sessionTitle}
                    onChange={(e) => setSessionTitle(e.target.value)}
                    placeholder="Auto-generated if empty"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Save Session Button */}
                <button
                  onClick={handleSaveSession}
                  disabled={isSaving || isLoading}
                  className="w-full px-4 py-2 bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  {isSaving ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
                      Saving...
                    </>
                  ) : (
                    <>
                      💾 {currentSessionId ? 'Update' : 'Save'} Session
                    </>
                  )}
                </button>

                {/* Clear Chat Button */}
                <button
                  onClick={handleClearChat}
                  disabled={isLoading}
                  className="w-full px-4 py-2 bg-red-50 text-red-600 rounded-md hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  🗑️ Clear Chat
                </button>
              </>
            )}

            {/* Load Sessions Button */}
            <button
              onClick={() => {
                setShowSessions(!showSessions)
                if (!showSessions) loadSessions()
              }}
              className="w-full px-4 py-2 bg-gray-50 text-gray-700 rounded-md hover:bg-gray-100 transition-colors font-medium"
            >
              📋 {showSessions ? 'Hide' : 'Show'} Saved Sessions
            </button>

            {/* Saved Sessions List */}
            {showSessions && (
              <div className="bg-white border border-gray-200 rounded-md max-h-64 overflow-y-auto">
                {savedSessions.length === 0 ? (
                  <p className="p-4 text-sm text-gray-500 text-center">No saved sessions</p>
                ) : (
                  <div className="divide-y divide-gray-200">
                    {savedSessions.map((sess: any) => (
                      <div
                        key={sess.id}
                        className="p-3 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <button
                            onClick={() => handleLoadSession(sess.id)}
                            className="flex-1 text-left"
                          >
                            <div className="font-medium text-sm text-gray-900 mb-1">
                              {sess.title}
                            </div>
                            <div className="text-xs text-gray-500">
                              {sess.message_count} messages • {new Date(sess.created_at).toLocaleDateString()}
                            </div>
                          </button>
                          <button
                            onClick={() => handleDeleteSession(sess.id)}
                            className="text-red-600 hover:text-red-800 text-xs px-2 py-1"
                          >
                            ×
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Chat Interface */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-lg shadow h-[calc(100vh-200px)] flex flex-col">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6">
              {session.messages.length === 0 ? (
                <div className="flex items-center justify-center h-full text-center">
                  <div>
                    <div className="text-6xl mb-4">💬</div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      Start a Conversation
                    </h3>
                    <p className="text-gray-600 max-w-md">
                      Select a pipeline and ask questions about your documents.
                      The AI will retrieve relevant context and generate answers.
                    </p>
                    {!selectedPipelineId && (
                      <p className="text-red-600 mt-4 font-medium">
                        ⚠️ Please select a pipeline first
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <>
                  {session.messages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      message={message}
                      onViewSources={setViewingSources}
                    />
                  ))}
                  {isLoading && (
                    <div className="flex justify-start mb-4">
                      <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
                          <span className="text-gray-600">Generating answer...</span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* Error Display */}
            {error && (
              <div className="px-6 py-3 bg-red-50 border-t border-red-100">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* Input Area */}
            <div className="border-t border-gray-200 p-4">
              {/* Show warning if session exists but pipeline was deleted */}
              {currentSessionId && !selectedPipelineId && (
                <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    ⚠️ <strong>Pipeline Deleted:</strong> This chat session is read-only because its associated pipeline has been deleted.
                  </p>
                </div>
              )}
              
              <div className="flex gap-2">
                <textarea
                  ref={inputRef}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading || !selectedPipelineId}
                  placeholder={
                    selectedPipelineId
                      ? "Ask a question... (Shift+Enter for new line)"
                      : currentSessionId
                      ? "Pipeline deleted - chat is read-only"
                      : "Please select a pipeline first"
                  }
                  rows={3}
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={isLoading || !selectedPipelineId || !inputMessage.trim()}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium self-end"
                >
                  {isLoading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                  ) : (
                    'Send'
                  )}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Press Enter to send, Shift+Enter for new line
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Source Viewer Modal */}
      {viewingSources && (
        <SourceViewer
          sources={viewingSources}
          onClose={() => setViewingSources(null)}
        />
      )}
    </div>
  )
}

