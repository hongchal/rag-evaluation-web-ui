import { useState, useCallback } from 'react'

export interface RetrievedChunk {
  chunk_id: string
  datasource_id: number
  content: string
  score: number
  metadata?: Record<string, any>
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: RetrievedChunk[]
  timestamp: Date
}

export interface GenerationParams {
  temperature: number
  maxTokens: number
  topP: number
}

export interface ModelConfig {
  type: 'claude' | 'vllm'
  modelName: string
  apiKey?: string
  endpoint?: string
  parameters: GenerationParams
}

export interface ChatSession {
  id: string
  pipelineId: number
  modelConfig: ModelConfig
  messages: Message[]
  createdAt: Date
}

export function useChatSession(pipelineId: number, modelConfig: ModelConfig) {
  const [session, setSession] = useState<ChatSession>({
    id: crypto.randomUUID(),
    pipelineId,
    modelConfig,
    messages: [],
    createdAt: new Date(),
  })

  const addMessage = useCallback((message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: crypto.randomUUID(),
      timestamp: new Date(),
    }
    
    setSession(prev => {
      const newMessages = [...prev.messages, newMessage]
      
      // Keep only last 50 messages to prevent memory issues
      if (newMessages.length > 50) {
        return {
          ...prev,
          messages: newMessages.slice(-50),
        }
      }
      
      return {
        ...prev,
        messages: newMessages,
      }
    })
  }, [])

  const clearSession = useCallback(() => {
    setSession({
      id: crypto.randomUUID(),
      pipelineId,
      modelConfig,
      messages: [],
      createdAt: new Date(),
    })
  }, [pipelineId, modelConfig])

  const updateModelConfig = useCallback((newConfig: ModelConfig) => {
    setSession(prev => ({
      ...prev,
      modelConfig: newConfig,
    }))
  }, [])

  return { 
    session, 
    addMessage, 
    clearSession,
    updateModelConfig,
  }
}

