import { useState, useRef, useEffect } from 'react'
import type { Pipeline } from '../lib/api'

interface PipelineComboboxProps {
  pipelines: Pipeline[]
  selectedPipelineId: number | null
  onSelect: (pipelineId: number) => void
  disabled?: boolean
  placeholder?: string
  className?: string
}

export function PipelineCombobox({
  pipelines,
  selectedPipelineId,
  onSelect,
  disabled = false,
  placeholder = 'Select Pipeline...',
  className = '',
}: PipelineComboboxProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)

  const selectedPipeline = pipelines.find((p) => p.id === selectedPipelineId)

  // Filter and group pipelines based on search query
  const filteredPipelines = pipelines.filter((pipeline) => {
    const query = searchQuery.toLowerCase()
    return (
      pipeline.name.toLowerCase().includes(query) ||
      pipeline.pipeline_type.toLowerCase().includes(query) ||
      pipeline.datasource?.name?.toLowerCase().includes(query)
    )
  })

  // Group pipelines by type
  const normalPipelines = filteredPipelines.filter((p) => p.pipeline_type === 'normal')
  const testPipelines = filteredPipelines.filter((p) => p.pipeline_type === 'test')

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Reset highlighted index when filtered list changes
  useEffect(() => {
    setHighlightedIndex(0)
  }, [searchQuery])

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && listRef.current) {
      const highlightedElement = listRef.current.children[highlightedIndex] as HTMLElement
      if (highlightedElement) {
        highlightedElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [highlightedIndex, isOpen])

  const handleSelect = (pipeline: Pipeline) => {
    onSelect(pipeline.id)
    setIsOpen(false)
    setSearchQuery('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setHighlightedIndex((prev) =>
          prev < filteredPipelines.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0))
        break
      case 'Enter':
        e.preventDefault()
        if (isOpen && filteredPipelines[highlightedIndex]) {
          handleSelect(filteredPipelines[highlightedIndex])
        } else {
          setIsOpen(true)
        }
        break
      case 'Escape':
        e.preventDefault()
        setIsOpen(false)
        setSearchQuery('')
        break
      case 'Tab':
        if (isOpen) {
          e.preventDefault()
        }
        break
    }
  }

  const handleInputClick = () => {
    if (!disabled) {
      setIsOpen(!isOpen)
      if (!isOpen) {
        setTimeout(() => inputRef.current?.focus(), 0)
      }
    }
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Input/Display Area */}
      <div
        className={`
          w-full px-3 py-2 border border-gray-300 rounded-md
          bg-white cursor-pointer
          focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500
          ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'hover:border-gray-400'}
          transition-colors
        `}
        onClick={handleInputClick}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex-1 min-w-0">
            {isOpen ? (
              <input
                ref={inputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                placeholder="Search pipelines..."
                className="w-full outline-none bg-transparent text-gray-900 placeholder-gray-400"
                autoFocus
              />
            ) : selectedPipeline ? (
              <div className="flex items-center gap-2">
                <span 
                  className="text-gray-900 font-medium truncate"
                  title={selectedPipeline.name}
                >
                  {selectedPipeline.name}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded shrink-0 ${
                    selectedPipeline.pipeline_type === 'normal'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-purple-100 text-purple-700'
                  }`}
                >
                  {selectedPipeline.pipeline_type === 'normal' ? '📄' : '🧪'}{' '}
                  {selectedPipeline.pipeline_type}
                </span>
              </div>
            ) : (
              <span className="text-gray-400">{placeholder}</span>
            )}
          </div>
          
          {/* Dropdown Arrow */}
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform shrink-0 ${
              isOpen ? 'rotate-180' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Dropdown List */}
      {isOpen && !disabled && (
        <div className="absolute z-50 w-full min-w-[500px] mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-80 overflow-hidden">
          {filteredPipelines.length > 0 ? (
            <ul ref={listRef} className="overflow-y-auto max-h-80">
              {/* Normal Pipelines Section */}
              {normalPipelines.length > 0 && (
                <>
                  <li className="px-3 py-2 bg-blue-50 border-b border-blue-200">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-blue-800 uppercase tracking-wide">
                        📄 Normal Pipelines
                      </span>
                      <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                        {normalPipelines.length}
                      </span>
                    </div>
                  </li>
                  {normalPipelines.map((pipeline, index) => {
                    const isSelected = pipeline.id === selectedPipelineId
                    const isHighlighted = index === highlightedIndex

                    return (
                      <li
                        key={pipeline.id}
                        onClick={() => handleSelect(pipeline)}
                        className={`
                          px-3 py-2.5 cursor-pointer transition-colors
                          ${isHighlighted ? 'bg-blue-50' : ''}
                          ${isSelected ? 'bg-blue-100' : ''}
                          hover:bg-blue-50
                          border-b border-gray-100
                        `}
                        onMouseEnter={() => setHighlightedIndex(index)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-gray-900 break-words">
                                {pipeline.name}
                              </span>
                              {isSelected && (
                                <svg
                                  className="w-4 h-4 text-blue-600 shrink-0"
                                  fill="currentColor"
                                  viewBox="0 0 20 20"
                                >
                                  <path
                                    fillRule="evenodd"
                                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                    clipRule="evenodd"
                                  />
                                </svg>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                              {pipeline.datasource && (
                                <span className="break-words">
                                  📁 {pipeline.datasource.name}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </li>
                    )
                  })}
                </>
              )}

              {/* Test Pipelines Section */}
              {testPipelines.length > 0 && (
                <>
                  <li className="px-3 py-2 bg-purple-50 border-b border-purple-200">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-purple-800 uppercase tracking-wide">
                        🧪 Test Pipelines
                      </span>
                      <span className="text-xs text-purple-600 bg-purple-100 px-2 py-0.5 rounded-full">
                        {testPipelines.length}
                      </span>
                    </div>
                  </li>
                  {testPipelines.map((pipeline, index) => {
                    const globalIndex = normalPipelines.length + index
                    const isSelected = pipeline.id === selectedPipelineId
                    const isHighlighted = globalIndex === highlightedIndex

                    return (
                      <li
                        key={pipeline.id}
                        onClick={() => handleSelect(pipeline)}
                        className={`
                          px-3 py-2.5 cursor-pointer transition-colors
                          ${isHighlighted ? 'bg-purple-50' : ''}
                          ${isSelected ? 'bg-purple-100' : ''}
                          hover:bg-purple-50
                          border-b border-gray-100 last:border-b-0
                        `}
                        onMouseEnter={() => setHighlightedIndex(globalIndex)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-gray-900 break-words">
                                {pipeline.name}
                              </span>
                              {isSelected && (
                                <svg
                                  className="w-4 h-4 text-purple-600 shrink-0"
                                  fill="currentColor"
                                  viewBox="0 0 20 20"
                                >
                                  <path
                                    fillRule="evenodd"
                                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                    clipRule="evenodd"
                                  />
                                </svg>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                              {pipeline.dataset && (
                                <span className="break-words">
                                  📊 {pipeline.dataset.name}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </li>
                    )
                  })}
                </>
              )}
            </ul>
          ) : (
            <div className="px-4 py-8 text-center text-gray-500">
              <div className="text-4xl mb-2">🔍</div>
              <p className="text-sm">No pipelines found</p>
              {searchQuery && (
                <p className="text-xs text-gray-400 mt-1">
                  Try a different search term
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

