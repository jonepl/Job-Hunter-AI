import { useState } from "react";

import {
  generationDownloadUrl,
  type GenerationKind,
  type GenerationOut,
} from "../api/client";
import {
  useGenerate,
  useGeneration,
  useJobGenerations,
} from "../hooks/useGeneration";

// The generation chip (ui-spec §5.4) — one component, five visual states — now
// live (W6). Generation is async: clicking starts a background task; the chip polls
// the row until a terminal status, then offers the download. HARD privacy rule
// (CLAUDE.md #2, ADR-034 §3): document content is NEVER rendered — only provenance,
// the download link, and, for needs_review, the structural locations to check.

interface Props {
  jobId: number;
  kind: GenerationKind;
}

const LABEL: Record<GenerationKind, string> = {
  resume: "Resume",
  cover_letter: "Cover letter",
};

/** Format an ISO timestamp as a compact "Jul 5". */
function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function GenerationChip({ jobId, kind }: Props) {
  const { data: generations } = useJobGenerations(jobId);
  const generate = useGenerate(jobId);
  const [pollId, setPollId] = useState<string | null>(null);
  const poll = useGeneration(pollId, jobId);
  const [expanded, setExpanded] = useState(false);

  // Newest-first list → the first match is the latest for this kind. A live poll of
  // a just-started generation wins over the (possibly stale) list entry.
  const latest = generations?.find((g) => g.kind === kind);
  const current: GenerationOut | undefined = poll.data ?? latest;

  function start() {
    setExpanded(false);
    generate.mutate(kind, { onSuccess: (g) => setPollId(g.id) });
  }

  const label = LABEL[kind];
  const pending = generate.isPending || current?.status === "pending";

  // --- pending: spinner + label, disabled, polling ---
  if (pending) {
    return (
      <Chip kind={kind} state="pending">
        <Spinner /> {label}
      </Chip>
    );
  }

  // --- failed: retry ---
  if (current?.status === "failed") {
    return (
      <Chip kind={kind} state="failed">
        <Trigger onClick={start} label={`⚠ Retry ${label.toLowerCase()}`}>
          <span aria-hidden>⚠</span> Retry
        </Trigger>
      </Chip>
    );
  }

  // --- ready / needs_review: download (+ review disclosure) ---
  if (current?.status === "ready") {
    const needsReview = current.outcome === "needs_review";
    const repaired = current.outcome === "repaired";
    return (
      <Chip kind={kind} state={needsReview ? "needs_review" : "ready"}>
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <a
              href={generationDownloadUrl(current.id)}
              download
              className="inline-flex items-center gap-2 text-control text-text transition-colors duration-fast hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
            >
              <span aria-hidden>{needsReview ? "⚠" : "✓"}</span>
              {label} · {shortDate(current.createdAt)}
              <span aria-hidden>↓</span>
            </a>
            {needsReview && current.reviewLocations.length > 0 && (
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                aria-expanded={expanded}
                className="rounded-pill bg-nearmiss-soft px-2 py-0.5 text-label text-nearmiss transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
              >
                {current.reviewLocations.length} to check
              </button>
            )}
          </div>
          {repaired && (
            <p className="text-caption text-text-3">Auto-fixed a formatting issue.</p>
          )}
          {needsReview && expanded && (
            <ul className="mt-1 space-y-0.5" data-testid="review-locations">
              {current.reviewLocations.map((location) => (
                <li key={location} className="text-caption text-text-2">
                  • {location}
                </li>
              ))}
            </ul>
          )}
        </div>
      </Chip>
    );
  }

  // --- empty: generate ---
  return (
    <Chip kind={kind} state="empty">
      <Trigger onClick={start} label={`Generate ${label.toLowerCase()}`}>
        <span aria-hidden>○</span> {label}
      </Trigger>
    </Chip>
  );
}

function Chip({
  kind,
  state,
  children,
}: {
  kind: GenerationKind;
  state: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className="inline-flex items-center gap-2 rounded-control border border-border bg-surface-2 px-3 py-1.5 text-small text-text-2"
      data-testid="generation-chip"
      data-kind={kind}
      data-state={state}
    >
      {children}
    </span>
  );
}

function Trigger({
  onClick,
  label,
  children,
}: {
  onClick: () => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="inline-flex items-center gap-2 text-control text-text transition-colors duration-fast hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
    >
      {children}
    </button>
  );
}

function Spinner() {
  return (
    <span
      aria-hidden
      data-testid="generation-spinner"
      className="inline-block h-3 w-3 animate-spin rounded-pill border border-text-3 border-t-transparent motion-reduce:animate-none"
    />
  );
}
