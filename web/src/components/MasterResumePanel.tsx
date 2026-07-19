import { useRef, useState, type DragEvent } from "react";

import type { ResumeOut } from "../api/client";
import { useActivateResumeVersion, useResume, useUploadResume } from "../hooks/useResume";

// The "Master resume" settings section (ui-spec §14.2): the source of truth for
// scoring and tailoring. Shows the active file's provenance (never its content,
// ADR-028), a drop zone to replace it, and the version history with restore.
// Download and per-version notes are deferred — E1 stores extracted text +
// provenance only, not the original bytes or a note field.

const ACCEPT = ".pdf,.docx";

/** Format a byte count as a compact decimal size (e.g. "214 KB", "1.2 MB"). */
function formatSize(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1000))} KB`;
}

/** Format an ISO date as "Jun 28, 2026"; empty when absent. */
function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** The uppercase format badge derived from the stored filename. */
function formatBadge(filename: string): string {
  return filename.toLowerCase().endsWith(".docx") ? "DOCX" : "PDF";
}

/** The mono provenance line: version · date · size · parsed counts. */
function provenanceLine(resume: ResumeOut): string {
  const parts = [`v${resume.version}`];
  const date = formatDate(resume.uploadedAt);
  if (date) parts.push(`uploaded ${date}`);
  parts.push(formatSize(resume.sizeBytes));
  parts.push(`parsed ${resume.skillCount} skills, ${resume.roleCount} roles`);
  return parts.join(" · ");
}

export function MasterResumePanel() {
  const { data, isLoading, isError } = useResume();
  const upload = useUploadResume();
  const activate = useActivateResumeVersion();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function submit(file: File | undefined): void {
    if (file) upload.mutate(file);
  }

  function onDrop(event: DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    setDragging(false);
    submit(event.dataTransfer.files[0]);
  }

  if (isLoading) {
    return (
      <div className="text-small text-text-2" role="status" aria-live="polite">
        Loading resume…
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-card border border-border bg-surface p-6 text-small text-text-2">
        Couldn’t load the master resume. Check that the API is running.
      </div>
    );
  }

  const active = data.active;

  return (
    <section data-testid="master-resume-panel" className="space-y-6">
      <header>
        <div className="flex items-center gap-2">
          <h2 className="font-display text-h2">Master resume</h2>
          {active && (
            <span className="rounded-pill bg-accent-soft px-2 py-0.5 font-mono text-label text-accent">
              v{active.version}
            </span>
          )}
        </div>
        <p className="mt-1 max-w-prose text-small text-text-2">
          The source of truth for scoring and tailoring. Every generated document starts
          from this file.
        </p>
      </header>

      {active ? (
        <div
          data-testid="resume-current-file"
          className="rounded-card border border-border bg-surface p-5"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="rounded-control bg-surface-2 px-2 py-0.5 font-mono text-label uppercase tracking-[0.05em] text-text-2">
                  {formatBadge(active.filename)}
                </span>
                <span className="truncate font-body text-body text-text">{active.filename}</span>
              </div>
              <p className="mt-2 font-mono text-small text-text-2">{provenanceLine(active)}</p>
            </div>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="shrink-0 rounded-control border border-border-strong px-3 py-1.5 text-control text-text transition-colors duration-fast hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
            >
              Replace
            </button>
          </div>
        </div>
      ) : (
        <p className="text-small text-text-2">
          No master resume stored yet. Upload one to start scoring and tailoring.
        </p>
      )}

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        data-testid="resume-dropzone"
        className={`rounded-card border border-dashed p-8 text-center transition-colors duration-fast ${
          dragging ? "border-accent bg-accent-soft" : "border-border bg-surface"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          data-testid="resume-file-input"
          className="sr-only"
          onChange={(event) => {
            submit(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={upload.isPending}
          className="rounded-control bg-accent px-4 py-2 text-control text-accent-on transition-colors duration-fast hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
        >
          {active ? "Choose a replacement" : "Choose a file"}
        </button>
        <p className="mt-3 text-small text-text-3">
          Drop a new .pdf or .docx here to replace — previous versions are kept.
        </p>

        {upload.isPending && (
          <p className="mt-3 text-small text-text-2" role="status" aria-live="polite">
            Parsing resume…
          </p>
        )}
        {upload.isError && (
          <p className="mt-3 text-small text-danger" role="alert">
            {upload.error.message}
          </p>
        )}
      </div>

      {data.versions.length > 0 && (
        <div>
          <h3 className="font-mono text-label uppercase tracking-[0.05em] text-text-3">
            Version history
          </h3>
          <ul data-testid="resume-versions" className="mt-3 divide-y divide-border">
            {data.versions.map((version) => (
              <li
                key={version.version}
                className="flex items-center justify-between gap-4 py-3"
              >
                <div className="min-w-0">
                  <span className="font-mono text-small text-text">v{version.version}</span>
                  <span className="ml-2 truncate text-small text-text-2">
                    {version.filename}
                  </span>
                  <p className="mt-0.5 font-mono text-caption text-text-3">
                    {provenanceLine(version)}
                  </p>
                </div>
                {version.isActive ? (
                  <span className="shrink-0 font-mono text-label uppercase tracking-[0.05em] text-accent">
                    Active
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => activate.mutate(version.version)}
                    disabled={activate.isPending}
                    className="shrink-0 rounded-control border border-border-strong px-3 py-1 text-small text-text transition-colors duration-fast hover:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
                  >
                    Restore
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
