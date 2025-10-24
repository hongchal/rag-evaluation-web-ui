import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/upload")({
  component: Upload,
});

function Upload() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upload Documents</h1>
        <p className="mt-2 text-muted-foreground">
          Upload PDF or TXT files to evaluate with different RAG strategies
        </p>
      </div>

      <div className="rounded-lg border-2 border-dashed border-border bg-accent p-12 text-center transition-colors hover:border-primary">
        <div className="space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-primary"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" x2="12" y1="3" y2="15" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium">
              Click to upload or drag and drop
            </p>
            <p className="text-xs text-muted-foreground">
              PDF or TXT files (max 50MB)
            </p>
          </div>
          <input
            type="file"
            accept=".pdf,.txt"
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="inline-flex cursor-pointer items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90"
          >
            Select Files
          </label>
        </div>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 text-lg font-semibold">Uploaded Files</h3>
        <div className="text-center text-sm text-muted-foreground">
          No files uploaded yet
        </div>
      </div>
    </div>
  );
}

