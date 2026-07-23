import { useEffect, useRef, useState } from "react";

import {
  generationDownloadUrl,
  type GenerationKind,
  type GenerationOut,
} from "../api/client";
import { useGenerate, useJobGenerations } from "../hooks/useGeneration";
import { generationState, isDownloadable, type GenState } from "../lib/generation";

// The document split-button + dropdown (redesign Part I.1). "Generate documents" is
// the detail pane's single primary action; the adjoining ▾ opens a 340px menu with
// one row per kind (state icon + mono meta + contextual action) and "Generate all
// missing". The two halves share one radius via overflow-hidden, split by the
// --menu-divider token. Fully keyboarded: aria-haspopup/expanded, arrow-key nav,
// Escape, outside-click close, focus returns to the trigger.

const KINDS: { kind: GenerationKind; label: string }[] = [
  { kind: "resume", label: "Tailored resume" },
  { kind: "cover_letter", label: "Cover letter" },
];

const STATE_ICON: Record<GenState, string> = {
  none: "○",
  generating: "…",
  ready: "✓",
  repaired: "✓",
  needs_review: "⚠",
  failed: "⚠",
};

/** "Jul 5" — compact provenance date. */
function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function metaLine(state: GenState, gen: GenerationOut | undefined): string {
  switch (state) {
    case "none":
      return "Not generated";
    case "generating":
      return "Generating…";
    case "failed":
      return "Failed";
    default:
      return gen ? `Generated ${shortDate(gen.createdAt)}` : "";
  }
}

interface Props {
  jobId: number;
}

export function GenerationMenu({ jobId }: Props) {
  const { data: generations } = useJobGenerations(jobId);
  const generate = useGenerate(jobId);
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const byKind = KINDS.map(({ kind, label }) => {
    const gen = generations?.find((g) => g.kind === kind);
    return { kind, label, gen, state: generationState(gen) };
  });
  const missingKinds = byKind.filter((k) => k.state === "none").map((k) => k.kind);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        toggleRef.current?.focus();
      }
    }
    function onClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        !toggleRef.current?.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onClickOutside);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onClickOutside);
    };
  }, [open]);

  function generateAllMissing() {
    missingKinds.forEach((kind) => generate.mutate(kind));
  }

  /** Roving focus across menu items with the arrow keys. */
  function onMenuKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const items = Array.from(
      menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [],
    );
    if (items.length === 0) return;
    const index = items.indexOf(document.activeElement as HTMLElement);
    const next =
      event.key === "ArrowDown"
        ? (index + 1) % items.length
        : (index - 1 + items.length) % items.length;
    items[next].focus();
  }

  return (
    <div className="relative">
      <div className="inline-flex overflow-hidden rounded-control">
        <button
          type="button"
          onClick={generateAllMissing}
          disabled={missingKinds.length === 0 || generate.isPending}
          className="bg-accent px-3 py-2 text-control text-accent-on transition-colors duration-fast hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
        >
          Generate documents
        </button>
        <button
          ref={toggleRef}
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-label="Document options"
          className="border-l border-menu-divider bg-accent px-2 py-2 text-accent-on transition-colors duration-fast hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          <span aria-hidden="true">▾</span>
        </button>
      </div>

      {open && (
        <div
          ref={menuRef}
          role="menu"
          onKeyDown={onMenuKeyDown}
          className="absolute left-0 z-40 mt-1 w-[340px] rounded-card border border-border bg-surface p-2"
        >
          {byKind.map(({ kind, label, gen, state }) => (
            <MenuRow
              key={kind}
              label={label}
              icon={STATE_ICON[state]}
              meta={metaLine(state, gen)}
              action={
                isDownloadable(state) && gen ? (
                  <a
                    role="menuitem"
                    href={generationDownloadUrl(gen.id)}
                    download
                    className="text-caption text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
                  >
                    Download ↓
                  </a>
                ) : (
                  <button
                    role="menuitem"
                    type="button"
                    onClick={() => generate.mutate(kind)}
                    disabled={state === "generating"}
                    className="text-caption text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
                  >
                    {state === "failed" ? "Retry" : state === "none" ? "Generate" : "Regenerate"}
                  </button>
                )
              }
            />
          ))}

          <hr className="my-2 border-t border-border" />

          <button
            role="menuitem"
            type="button"
            onClick={generateAllMissing}
            disabled={missingKinds.length === 0}
            className="flex w-full items-center gap-2 rounded-control px-2 py-2 text-left text-small text-text transition-colors duration-fast hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
          >
            <span aria-hidden="true" className="text-accent">
              ✦
            </span>
            Generate all missing
          </button>
        </div>
      )}
    </div>
  );
}

function MenuRow({
  label,
  icon,
  meta,
  action,
}: {
  label: string;
  icon: string;
  meta: string;
  action: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-control px-2 py-2">
      <span className="flex items-center gap-2">
        <span aria-hidden="true" className="text-text-3">
          {icon}
        </span>
        <span className="flex flex-col">
          <span className="text-small text-text">{label}</span>
          <span className="font-mono text-caption text-text-3">{meta}</span>
        </span>
      </span>
      {action}
    </div>
  );
}
