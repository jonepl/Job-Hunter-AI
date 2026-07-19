import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, type SchedulePreview } from "../../api/client";
import { useSettings, useUpdateSettings } from "../../hooks/useSettings";
import { settingsToUpdate } from "../../lib/settings";
import {
  Field,
  PanelError,
  PanelHeader,
  PanelStatus,
  inputClass,
  primaryClass,
} from "./shared";

// Run schedule section: the cron expression + timezone that drive scheduled runs,
// with a live "Next 3 runs" preview computed server-side. The live in-process
// reschedule is a later story, so a saved cron takes effect on the next restart.

/** Debounce a value so the preview query does not fire on every keystroke. */
function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

export function ScheduleSettings() {
  const { data: settings, isLoading, isError } = useSettings();
  const update = useUpdateSettings();
  const [cron, setCron] = useState<string | null>(null);
  const [tz, setTz] = useState<string | null>(null);

  const cronValue = cron ?? settings?.scheduleCron ?? "";
  const tzValue = tz ?? settings?.scheduleTimezone ?? "UTC";
  const debouncedCron = useDebounced(cronValue, 400);

  const preview = useQuery<SchedulePreview>({
    queryKey: ["schedule-preview", debouncedCron, tzValue],
    queryFn: () => api.getSchedulePreview(debouncedCron, tzValue),
    enabled: debouncedCron.trim() !== "",
    retry: false,
  });

  if (isLoading) return <PanelStatus>Loading settings…</PanelStatus>;
  if (isError || !settings) return <PanelError />;

  function save() {
    update.mutate({
      ...settingsToUpdate(settings!),
      scheduleCron: cronValue,
      scheduleTimezone: tzValue,
    });
  }

  return (
    <section data-testid="schedule-settings" className="space-y-6">
      <PanelHeader
        title="Run schedule"
        subtitle="When scheduled searches run. A saved change applies on the next restart."
      />

      <Field label="Cron expression" htmlFor="cron" hint="Five fields, e.g. 0 8 * * 1-5">
        <input
          id="cron"
          value={cronValue}
          onChange={(e) => setCron(e.target.value)}
          placeholder="0 8 * * 1-5"
          className={inputClass + " font-mono"}
        />
      </Field>

      <Field label="Timezone" htmlFor="tz">
        <input
          id="tz"
          value={tzValue}
          onChange={(e) => setTz(e.target.value)}
          placeholder="America/New_York"
          className={inputClass + " font-mono"}
        />
      </Field>

      <div>
        <h3 className="font-mono text-label uppercase tracking-[0.05em] text-text-3">Next 3 runs</h3>
        <div className="mt-2" data-testid="schedule-preview">
          {debouncedCron.trim() === "" ? (
            <p className="text-small text-text-3">Enter a cron expression to preview.</p>
          ) : preview.isError ? (
            <p className="text-small text-danger" role="alert">
              Invalid cron expression.
            </p>
          ) : preview.data ? (
            <ul className="space-y-1">
              {preview.data.nextRuns.map((iso) => (
                <li key={iso} className="font-mono text-small text-text-2">
                  {new Date(iso).toLocaleString()}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-small text-text-3">Computing…</p>
          )}
        </div>
      </div>

      <button type="button" onClick={save} disabled={update.isPending} className={primaryClass}>
        {update.isPending ? "Saving…" : "Save schedule"}
      </button>
    </section>
  );
}
