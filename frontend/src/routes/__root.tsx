import { createRootRoute, Link, Outlet } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";

const RootLayout = () => (
  <div className="min-h-screen bg-background">
    <nav className="border-b bg-card">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">R</span>
              </div>
              <h1 className="text-xl font-bold">RAG Evaluation</h1>
            </Link>
          </div>
          <div className="flex gap-1">
            <Link
              to="/"
              className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent [&.active]:bg-accent [&.active]:text-accent-foreground"
            >
              Home
            </Link>
            <Link
              to="/rags"
              className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent [&.active]:bg-accent [&.active]:text-accent-foreground"
            >
              RAGs
            </Link>
            <Link
              to="/datasources"
              className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent [&.active]:bg-accent [&.active]:text-accent-foreground"
            >
              Data Sources
            </Link>
            <Link
              to="/datasets"
              className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent [&.active]:bg-accent [&.active]:text-accent-foreground"
            >
              Datasets
            </Link>
            <Link
              to="/query"
              className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent [&.active]:bg-accent [&.active]:text-accent-foreground"
            >
              Query
            </Link>
            <Link
              to="/evaluate"
              className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent [&.active]:bg-accent [&.active]:text-accent-foreground"
            >
              Evaluate
            </Link>
            <Link
              to="/upload"
              className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent [&.active]:bg-accent [&.active]:text-accent-foreground"
            >
              Upload
            </Link>
          </div>
        </div>
      </div>
    </nav>
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <Outlet />
    </main>
    <TanStackRouterDevtools />
  </div>
);

export const Route = createRootRoute({ component: RootLayout });

