import { createFileRoute, Link } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: Index,
})

function Index() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-4">RAG Evaluation System</h1>
        <p className="text-xl text-gray-600 mb-8">
          Create, test, and evaluate RAG configurations
        </p>

        <div className="grid md:grid-cols-2 gap-6 mb-12">
          <Link
            to="/rags/create"
            className="block bg-white shadow-lg rounded-lg p-8 hover:shadow-xl transition-shadow"
          >
            <h2 className="text-2xl font-semibold mb-3">🎯 Create RAG</h2>
            <p className="text-gray-600">
              Configure chunking, embedding, and reranking modules
            </p>
          </Link>

          <Link
            to="/retrieve"
            className="block bg-white shadow-lg rounded-lg p-8 hover:shadow-xl transition-shadow"
          >
            <h2 className="text-2xl font-semibold mb-3">🔍 Test Query</h2>
            <p className="text-gray-600">
              Search and test your RAG configurations
            </p>
          </Link>

          <Link
            to="/evaluate"
            className="block bg-white shadow-lg rounded-lg p-8 hover:shadow-xl transition-shadow"
          >
            <h2 className="text-2xl font-semibold mb-3">📊 Evaluate</h2>
            <p className="text-gray-600">
              Run evaluations on benchmark datasets
            </p>
          </Link>

          <Link
            to="/upload"
            className="block bg-white shadow-lg rounded-lg p-8 hover:shadow-xl transition-shadow"
          >
            <h2 className="text-2xl font-semibold mb-3">📁 Upload Data</h2>
            <p className="text-gray-600">
              Upload documents and datasets
            </p>
          </Link>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-3">Quick Start</h3>
          <ol className="list-decimal list-inside space-y-2 text-gray-700">
            <li>Create a new RAG configuration</li>
            <li>Upload documents to create a data source</li>
            <li>Sync the data source with your RAG</li>
            <li>Test queries or run evaluations</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
