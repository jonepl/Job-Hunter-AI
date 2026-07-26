import { useEffect, useRef, useState } from "react";

import type { ProfileOut } from "../api/client";
import { useUpdateProfile } from "../hooks/useProfiles";
import { profileToInput } from "../lib/settings";
import { platformName } from "../lib/platforms";

// Configure-profile modal (search v2 §F). Opened from the ⚙ gear on a rail row; edits
// just *what a profile searches for* — name, query, location, platforms — via
// PUT /api/profiles/{id}, matching the mock's field set (lines 408–436). Schedule
// editing stays in Settings → Profiles (per-profile-scheduling owns it), so the rest of
// the profile (work types, threshold, schedule) round-trips untouched through
// profileToInput. Accessibility mirrors NewProfileModal: role="dialog", focus trap,
// Escape, and focus restoration.

const PLATFORMS = ["linkedin", "indeed", "glassdoor", "ziprecruiter"] as const;

interface Props {
  profile: ProfileOut;
  onClose: () => void;
}

export function ConfigureProfileModal({ profile, onClose }: Props) {
  const update = useUpdateProfile();

  const [name, setName] = useState(profile.name);
  const [query, setQuery] = useState(profile.query);
  const [location, setLocation] = useState(profile.location);
  const [platforms, setPlatforms] = useState<string[]>(profile.activeScrapers);

  const dialogRef = useRef<HTMLDivElement>(null);
  const firstFieldRef = useRef<HTMLInputElement>(null);

  // Same validation contract as the new-profile modal: name OR query, ≥1 platform.
  const valid = (name.trim() !== "" || query.trim() !== "") && platforms.length > 0;

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
    // Preserve every field the modal doesn't expose (schedule, threshold, work types)
    // by starting from the full profile and overlaying only the edited fields.
    const body = {
      ...profileToInput(profile),
      name: name.trim(),
      query: query.trim(),
      location: location.trim() || null,
      activeScrapers: platforms,
    };
    update.mutate({ id: profile.id, body }, { onSuccess: () => onClose() });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-text/40 p-4"
      onClick={onClose}
      data-testid="configure-profile-backdrop"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="configure-profile-heading"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-[480px] rounded-card border border-border bg-surface p-6"
      >
        <h2 id="configure-profile-heading" className="font-display text-h2">
          Configure profile
        </h2>

        <div className="mt-5 space-y-4">
          <Field label="Profile name" htmlFor="cp-name">
            <input
              id="cp-name"
              ref={firstFieldRef}
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Role / keywords" htmlFor="cp-query">
            <input
              id="cp-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className={`${inputClass} font-mono`}
            />
          </Field>
          <Field label="Location" htmlFor="cp-location">
            <input
              id="cp-location"
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

        {update.isError && (
          <p className="mt-4 text-small text-danger" role="alert">
            {update.error.message}
          </p>
        )}

        <p className="mt-5 text-caption text-text-3">
          Edit the schedule and threshold in Settings → Profiles.
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
            disabled={!valid || update.isPending}
            className="rounded-control bg-accent px-4 py-2 text-control text-accent-on transition-colors duration-fast hover:bg-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-60"
          >
            {update.isPending ? "Saving…" : "Save changes"}
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
