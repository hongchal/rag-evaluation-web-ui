import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">
          Welcome to RAG Evaluation
        </h1>
        <p className="text-lg text-muted-foreground">
          A comprehensive tool for evaluating and comparing different RAG
          strategies
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h3 className="mb-2 text-lg font-semibold">1. Upload Documents</h3>
          <p className="text-sm text-muted-foreground">
            Upload your PDF or TXT files to get started with evaluation
          </p>
        </div>

        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h3 className="mb-2 text-lg font-semibold">
            2. Configure Strategies
          </h3>
          <p className="text-sm text-muted-foreground">
            Choose chunking, embedding, and reranking strategies for your RAG
            pipeline
          </p>
        </div>

        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h3 className="mb-2 text-lg font-semibold">3. Compare Results</h3>
          <p className="text-sm text-muted-foreground">
            Analyze performance metrics and compare different configurations
          </p>
        </div>
      </div>

      <div className="rounded-lg border bg-accent p-6">
        <h3 className="mb-3 text-xl font-semibold">Features</h3>
        <ul className="space-y-2 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-primary">✓</span>
            <span>
              Multiple chunking strategies (Recursive, Hierarchical, Semantic)
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary">✓</span>
            <span>Various embedding models (BGE-M3, Matryoshka, and more)</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary">✓</span>
            <span>Real-time evaluation progress monitoring</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary">✓</span>
            <span>
              Comprehensive metrics (NDCG@K, MRR, Precision, Recall, etc.)
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary">✓</span>
            <span>Visual comparison dashboards with charts</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

