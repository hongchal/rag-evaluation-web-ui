import type { RetrievedChunk } from '../hooks/useChatSession'

interface SourceViewerProps {
  sources: RetrievedChunk[]
  onClose: () => void
}

export function SourceViewer({ sources, onClose }: SourceViewerProps) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            Source Documents ({sources.length})
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            {sources.map((source, index) => (
              <div
                key={source.chunk_id}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
              >
                {/* Source Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-semibold text-sm">
                      {index + 1}
                    </span>
                    <div>
                      <div className="text-sm text-gray-500">
                        Score: <span className="font-medium text-gray-900">{source.score.toFixed(4)}</span>
                      </div>
                      {source.datasource_id && (
                        <div className="text-xs text-gray-400">
                          DataSource ID: {source.datasource_id}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {source.content}
                </div>

                {/* Metadata */}
                {source.metadata && Object.keys(source.metadata).length > 0 && (
                  <details className="mt-3">
                    <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700 select-none">
                      Metadata
                    </summary>
                    <pre className="mt-2 text-xs bg-gray-50 p-3 rounded overflow-x-auto border border-gray-200">
                      {JSON.stringify(source.metadata, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

