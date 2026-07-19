import { MasterResumePanel } from "../components/MasterResumePanel";

// The Settings screen (ui-spec §14.2). W5 ships a MINIMAL shell: the left
// CONFIGURATION rail lists every section, but only "Master resume" is live — the
// other five are disabled placeholders that W7 wires up. A "← Back to search"
// control returns to the job list (App owns the view state; no router yet).

interface Props {
  onBack: () => void;
}

// The six configuration sections in rail order. Only Master resume is active in
// W5; the rest are non-interactive until W7.
const SECTIONS = [
  { id: "voice", label: "Voice & tone" },
  { id: "threshold", label: "Match threshold" },
  { id: "schedule", label: "Run schedule" },
  { id: "profiles", label: "Search profiles" },
  { id: "provider", label: "Evaluator provider" },
  { id: "resume", label: "Master resume", active: true },
] as const;

export function Settings({ onBack }: Props) {
  return (
    <div data-testid="settings-screen">
      <div className="mb-6 flex items-center gap-4">
        <h1 className="font-mono text-label uppercase tracking-[0.08em] text-text-3">
          Settings
        </h1>
        <button
          type="button"
          onClick={onBack}
          className="text-small text-text-2 transition-colors duration-fast hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          ← Back to search
        </button>
      </div>

      <div className="lg:grid lg:grid-cols-[minmax(0,14rem)_minmax(0,1fr)] lg:gap-8">
        <nav aria-label="Configuration" className="mb-6 lg:mb-0">
          <h2 className="mb-3 font-mono text-label uppercase tracking-[0.05em] text-text-3">
            Configuration
          </h2>
          <ul className="space-y-1">
            {SECTIONS.map((section) => {
              const active = "active" in section && section.active;
              return (
                <li key={section.id}>
                  <button
                    type="button"
                    disabled={!active}
                    aria-current={active ? "page" : undefined}
                    className={`w-full rounded-control px-3 py-2 text-left text-control transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ${
                      active
                        ? "bg-accent-soft text-accent"
                        : "cursor-not-allowed text-text-3"
                    }`}
                  >
                    {section.label}
                    {!active && (
                      <span className="ml-2 font-mono text-label uppercase tracking-[0.05em] text-text-3">
                        Soon
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <MasterResumePanel />
      </div>
    </div>
  );
}
