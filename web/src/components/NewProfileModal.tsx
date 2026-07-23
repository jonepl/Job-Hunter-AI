import { useEffect, useRef, useState } from "react";

import { useCreateProfile } from "../hooks/useProfiles";
import { useSettings } from "../hooks/useSettings";
import { platformName } from "../lib/platforms";

// New-profile modal (redesign Part G). Posts to POST /api/profiles via
// useCreateProfile. The mock has inputs only for name/query/location/platforms; the
// remaining ProfileIn fields are sent as schema defaults, and the footer shows the
// REAL schedule + threshold (not the mock's fabricated copy). Accessibility the mock
// lacked is mandatory: role="dialog", focus trap, Escape, and focus restoration.

const PLATFORMS = ["linkedin", "indeed", "glassdoor", "ziprecruiter"] as const;

// Defaults for the fields the modal doesn't expose (mirrors ProfileIn).
const DEFAULT_THRESHOLD = 75;

interface Props {
  onClose: () => void;
}

export function NewProfileModal({ onClose }: Props) {
  const create = useCreateProfile();
  const { data: settings } = useSettings();

  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [platforms, setPlatforms] = useState<string[]>(["linkedin", "indeed"]);

  const dialogRef = useRef<HTMLDivElement>(null);
  const firstFieldRef = useRef<HTMLInputElement>(null);

  // Validation mirrors the mock: name OR query, plus at least one platform.
  const valid = (name.trim() !== "" || query.trim() !== "") && platforms.length > 0;

  // Focus management: focus the first field on open, trap Tab within the dialog,
  // close on Escape, and restore focus to the trigger on unmount.
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    firstFieldRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus();
    };
  }, [onClose]);

  function togglePlatform(platform: string) {
    setPlatforms((current) =>
      current.includes(platform)
        ? current.filter((p) => p !== platform)
        : [...current, platform],
    );
  }

  function submit() {
    if (!valid) return;
    create.mutate(
      {
        name: name.trim(),
        query: query.trim(),
        location: location.trim() || null,
        activeScrapers: platforms,
        // Fields the modal doesn't expose — send the schema defaults.
        workTypes: null,
        datePosted: "3days",
        scoreThreshold: DEFAULT_THRESHOLD,
        topResults: null,
        enabled: true,
      },
      { onSuccess: () => onClose() }, // never close on failure
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-text/40 p-4"
      onClick={onClose}
      data-testid="new-profile-backdrop"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-profile-heading"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-[480px] rounded-card border border-border bg-surface p-6"
      >
        <h2 id="new-profile-heading" className="font-display text-h2">
          New search profile
        </h2>

        <div className="mt-5 space-y-4">
          <Field label="Profile name" htmlFor="np-name">
            <input
              id="np-name"
              ref={firstFieldRef}
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Role / keywords" htmlFor="np-query">
            <input
              id="np-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className={`${inputClass} font-mono`}
            />
          </Field>
          <Field label="Location" htmlFor="np-location">
            <input
              id="np-location"
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              placeholder="United States"
              className={inputClass}
            />
          </Field>

          <fieldset>
            <legend className="mb-2 block text-label font-semibold text-text">Platforms</legend>
            <div className="flex flex-wrap gap-2">
              {PLATFORMS.map((platform) => {
                const on = platforms.includes(platform);
                return (
                  <button
                    key={platform}
                    type="button"
                    aria-pressed={on}
                    onClick={() => togglePlatform(platform)}
                    className={`rounded-pill border px-3 py-1 text-caption transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ${
                      on
                        ? "border-accent bg-accent-soft text-accent"
                        : "border-border bg-surface text-text-2 hover:text-text"
                    }`}
                  >
                    {platformName(platform)}
                  </button>
                );
              })}
            </div>
          </fieldset>
        </div>

        {create.isError && (
          <p className="mt-4 text-small text-danger" role="alert">
            {create.error.message}
          </p>
        )}

        <p className="mt-5 text-caption text-text-3">
          Runs on the global schedule
          {settings?.scheduleCron ? (
            <>
              {" "}
              (<span className="font-mono">{settings.scheduleCron}</span>)
            </>
          ) : null}{" "}
          · threshold <span className="font-mono">{DEFAULT_THRESHOLD}</span>
        </p>

        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-control px-4 py-2 text-control text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={!valid || create.isPending}
            className="rounded-control bg-accent px-4 py-2 text-control text-accent-on transition-colors duration-fast hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
          >
            {create.isPending ? "Creating…" : "Create profile"}
          </button>
        </div>
      </div>
    </div>
  );
}

const inputClass =
  "w-full rounded-control border border-border-strong bg-bg px-3 py-2 text-control text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2";

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1 block text-label font-semibold text-text">
        {label}
      </label>
      {children}
    </div>
  );
}
