import { useState, useEffect } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { api } from '../lib/api'

export const Route = createFileRoute('/prompts')({
  component: PromptsPage,
})

interface PromptTemplate {
  id: number
  name: string
  system_prompt: string
  description?: string
  created_at: string
  updated_at: string
}

function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [editingPrompt, setEditingPrompt] = useState<PromptTemplate | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  
  // Form state
  const [formName, setFormName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formSystemPrompt, setFormSystemPrompt] = useState('')

  useEffect(() => {
    loadPrompts()
  }, [])

  const loadPrompts = async () => {
    try {
      setLoading(true)
      const response = await api.listPromptTemplates()
      setPrompts(response.items)
    } catch (err) {
      console.error('Failed to load prompts:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!formName || !formSystemPrompt) {
      alert('Please enter both name and system prompt')
      return
    }

    try {
      await api.createPromptTemplate({
        name: formName,
        system_prompt: formSystemPrompt,
        description: formDescription,
      })
      
      resetForm()
      setShowCreateForm(false)
      await loadPrompts()
    } catch (err: any) {
      console.error('Failed to create prompt:', err)
      alert(`Failed to create: ${err.message}`)
    }
  }

  const handleUpdate = async () => {
    if (!editingPrompt || !formName || !formSystemPrompt) {
      alert('Please enter both name and system prompt')
      return
    }

    try {
      await api.updatePromptTemplate(editingPrompt.id, {
        name: formName,
        system_prompt: formSystemPrompt,
        description: formDescription,
      })
      
      resetForm()
      setEditingPrompt(null)
      await loadPrompts()
    } catch (err: any) {
      console.error('Failed to update prompt:', err)
      alert(`Failed to update: ${err.message}`)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this prompt template?')) return

    try {
      await api.deletePromptTemplate(id)
      await loadPrompts()
    } catch (err: any) {
      console.error('Failed to delete prompt:', err)
      alert(`Failed to delete: ${err.message}`)
    }
  }

  const startEdit = (prompt: PromptTemplate) => {
    setEditingPrompt(prompt)
    setFormName(prompt.name)
    setFormDescription(prompt.description || '')
    setFormSystemPrompt(prompt.system_prompt)
    setShowCreateForm(false)
  }

  const startCreate = () => {
    resetForm()
    setShowCreateForm(true)
    setEditingPrompt(null)
  }

  const resetForm = () => {
    setFormName('')
    setFormDescription('')
    setFormSystemPrompt('')
  }

  const cancelEdit = () => {
    resetForm()
    setEditingPrompt(null)
    setShowCreateForm(false)
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Prompt Library</h1>
          <p className="text-gray-600">Manage your system prompt templates</p>
        </div>
        <button
          onClick={startCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors shadow-sm"
        >
          ➕ New Prompt
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form Panel */}
        {(showCreateForm || editingPrompt) && (
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6 sticky top-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                {editingPrompt ? '✏️ Edit Prompt' : '➕ New Prompt'}
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Name *
                  </label>
                  <input
                    type="text"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="e.g., Technical Expert"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <input
                    type="text"
                    value={formDescription}
                    onChange={(e) => setFormDescription(e.target.value)}
                    placeholder="e.g., For technical documentation"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    System Prompt *
                  </label>
                  <textarea
                    value={formSystemPrompt}
                    onChange={(e) => setFormSystemPrompt(e.target.value)}
                    placeholder="Enter your system prompt instructions..."
                    rows={12}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {formSystemPrompt.length} characters
                  </p>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={editingPrompt ? handleUpdate : handleCreate}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
                  >
                    {editingPrompt ? '💾 Update' : '✅ Create'}
                  </button>
                  <button
                    onClick={cancelEdit}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Prompts List */}
        <div className={showCreateForm || editingPrompt ? 'lg:col-span-2' : 'lg:col-span-3'}>
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mx-auto"></div>
              <p className="text-gray-600 mt-4">Loading prompts...</p>
            </div>
          ) : prompts.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <div className="text-6xl mb-4">📝</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No prompts yet</h3>
              <p className="text-gray-600 mb-4">Create your first system prompt template</p>
              <button
                onClick={startCreate}
                className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                ➕ Create First Prompt
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {prompts.map((prompt) => (
                <div
                  key={prompt.id}
                  className={`bg-white rounded-lg shadow p-6 transition-all ${
                    editingPrompt?.id === prompt.id ? 'ring-2 ring-blue-500' : 'hover:shadow-md'
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900">{prompt.name}</h3>
                      {prompt.description && (
                        <p className="text-sm text-gray-600 mt-1">{prompt.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={() => startEdit(prompt)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                        title="Edit"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDelete(prompt.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="Delete"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-md p-4 border border-gray-200">
                    <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
                      {prompt.system_prompt}
                    </pre>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                    <span>
                      Created: {new Date(prompt.created_at).toLocaleDateString()}
                    </span>
                    <span>{prompt.system_prompt.length} characters</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

