import { JobList } from "./screens/JobList";
import { ThemeToggle } from "./components/ThemeToggle";

export function App() {
  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="font-display text-h2">Job Hunter AI</span>
          <ThemeToggle />
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <JobList />
      </main>
    </div>
  );
}
