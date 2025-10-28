import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message, RetrievedChunk } from '../hooks/useChatSession'

interface ChatMessageProps {
  message: Message
  onViewSources?: (sources: RetrievedChunk[]) => void
}

export function ChatMessage({ message, onViewSources }: ChatMessageProps) {
  const isUser = message.role === 'user'
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-white border border-gray-200 text-gray-900'
          }`}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap wrap-break-word">{message.content}</div>
          ) : (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // 코드 블록 스타일링
                  code: ({ node, inline, className, children, ...props }: any) => {
                    return inline ? (
                      <code className="bg-gray-100 text-red-600 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                        {children}
                      </code>
                    ) : (
                      <code className="block bg-gray-900 text-gray-100 p-3 rounded-md overflow-x-auto text-sm font-mono" {...props}>
                        {children}
                      </code>
                    )
                  },
                  // 헤딩 스타일링
                  h1: ({ node, ...props }) => <h1 className="text-2xl font-bold mt-6 mb-4" {...props} />,
                  h2: ({ node, ...props }) => <h2 className="text-xl font-bold mt-5 mb-3" {...props} />,
                  h3: ({ node, ...props }) => <h3 className="text-lg font-semibold mt-4 mb-2" {...props} />,
                  // 리스트 스타일링
                  ul: ({ node, ...props }) => <ul className="list-disc pl-6 my-3 space-y-2" {...props} />,
                  ol: ({ node, ...props }) => <ol className="list-decimal pl-6 my-3 space-y-2" {...props} />,
                  li: ({ node, ...props }) => <li className="pl-2" {...props} />,
                  // 링크 스타일링
                  a: ({ node, ...props }) => <a className="text-blue-600 hover:text-blue-800 underline" {...props} />,
                  // 단락 스타일링
                  p: ({ node, ...props }) => <p className="my-3 leading-relaxed" {...props} />,
                  // 인용문 스타일링
                  blockquote: ({ node, ...props }) => (
                    <blockquote className="border-l-4 border-gray-300 pl-4 italic my-3 text-gray-700" {...props} />
                  ),
                  // 표 스타일링
                  table: ({ node, ...props }) => (
                    <div className="overflow-x-auto my-5">
                      <table className="min-w-full border-collapse border border-gray-300" {...props} />
                    </div>
                  ),
                  th: ({ node, ...props }) => (
                    <th className="border border-gray-300 bg-gray-100 px-4 py-2 text-left font-semibold" {...props} />
                  ),
                  td: ({ node, ...props }) => (
                    <td className="border border-gray-300 px-4 py-2" {...props} />
                  ),
                  // 강조 텍스트 스타일링
                  strong: ({ node, ...props }) => <strong className="font-bold text-gray-900" {...props} />,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
          
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <button
                onClick={() => message.sources && onViewSources?.(message.sources)}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                📎 View {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
              </button>
            </div>
          )}
        </div>
        
        <div className={`text-xs text-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}

