import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/evaluate")({
  component: Evaluate,
});

function Evaluate() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Configure Evaluation
        </h1>
        <p className="mt-2 text-muted-foreground">
          Select your document and RAG strategies to begin evaluation
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4 rounded-lg border bg-card p-6">
          <h3 className="text-lg font-semibold">Chunking Strategy</h3>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="chunking"
                value="recursive"
                defaultChecked
              />
              <span>Recursive Character</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="chunking" value="hierarchical" />
              <span>Hierarchical</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="chunking" value="semantic" />
              <span>Semantic</span>
            </label>
          </div>
        </div>

        <div className="space-y-4 rounded-lg border bg-card p-6">
          <h3 className="text-lg font-semibold">Embedding Strategy</h3>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="embedding"
                value="bge-m3"
                defaultChecked
              />
              <span>BGE-M3</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="embedding" value="matryoshka" />
              <span>Matryoshka</span>
            </label>
          </div>
        </div>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 text-lg font-semibold">Select Document</h3>
        <select className="w-full rounded-md border border-input bg-background px-3 py-2">
          <option value="">Choose a document...</option>
        </select>
      </div>

      <div className="flex justify-end">
        <button className="rounded-md bg-primary px-6 py-2 font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90">
          Start Evaluation
        </button>
      </div>
    </div>
  );
}

