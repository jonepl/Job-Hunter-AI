import { useState } from "react";

import type { SecretStatus } from "../../api/client";
import {
  useClearSecret,
  useSetSecret,
  useSettings,
  useUpdateSettings,
} from "../../hooks/useSettings";
import { settingsToUpdate } from "../../lib/settings";
import { DiffBadge } from "./DiffBadge";
import {
  Field,
  PanelError,
  PanelHeader,
  PanelStatus,
  ghostClass,
  inputClass,
  primaryClass,
  secondaryClass,
  selectClass,
} from "./shared";

// Evaluator provider section: the global provider + model + pre-filter mode, plus the
// three API-key secrets. Secrets are write-only (ADR-031) — the panel shows only a
// masked suffix and a differs-from-.env badge, never a key value.

const SECRET_LABELS: Record<string, string> = {
  openai_api_key: "OpenAI API key",
  anthropic_api_key: "Anthropic API key",
  gemini_api_key: "Gemini API key",
};

export function ProviderSettings() {
  const { data: settings, isLoading, isError } = useSettings();
  const update = useUpdateSettings();
  const [provider, setProvider] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [mode, setMode] = useState<string | null>(null);

  if (isLoading) return <PanelStatus>Loading settings…</PanelStatus>;
  if (isError || !settings) return <PanelError />;

  const providerValue = provider ?? settings.evaluatorProvider;
  const modelValue = model ?? settings.evaluatorModel ?? "";
  const modeValue = mode ?? settings.enrichmentMode;

  function save() {
    update.mutate({
      ...settingsToUpdate(settings!),
      evaluatorProvider: providerValue as "openai" | "anthropic",
      evaluatorModel: modelValue || null,
      enrichmentMode: modeValue as "shadow" | "enforce",
    });
  }

  return (
    <section data-testid="provider-settings" className="space-y-6">
      <PanelHeader
        title="Evaluator provider"
        subtitle="Which LLM scores each job, and the keys the run uses."
      />

      <Field label="Provider" htmlFor="provider">
        <select
          id="provider"
          value={providerValue}
          onChange={(e) => setProvider(e.target.value)}
          className={selectClass}
        >
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
        </select>
      </Field>

      <Field label="Model override" htmlFor="model" hint="Blank uses the provider default.">
        <input
          id="model"
          value={modelValue}
          onChange={(e) => setModel(e.target.value)}
          placeholder="e.g. gpt-4o"
          className={inputClass + " font-mono"}
        />
      </Field>

      <Field label="Pre-filter mode" htmlFor="mode">
        <select
          id="mode"
          value={modeValue}
          onChange={(e) => setMode(e.target.value)}
          className={selectClass}
        >
          <option value="shadow">Shadow (measure only)</option>
          <option value="enforce">Enforce (skip flagged jobs)</option>
        </select>
      </Field>

      <button type="button" onClick={save} disabled={update.isPending} className={primaryClass}>
        {update.isPending ? "Saving…" : "Save provider settings"}
      </button>

      <div className="border-t border-border pt-6">
        <h3 className="font-display text-body font-semibold">API keys</h3>
        <p className="mt-1 text-small text-text-2">
          Keys are write-only — stored securely and never shown. Leave blank to keep the
          current value.
        </p>
        <ul className="mt-4 space-y-4" data-testid="secret-list">
          {settings.secrets.map((secret) => (
            <SecretRow key={secret.name} secret={secret} />
          ))}
        </ul>
      </div>
    </section>
  );
}

function SecretRow({ secret }: { secret: SecretStatus }) {
  const setSecret = useSetSecret();
  const clearSecret = useClearSecret();
  const [value, setValue] = useState("");

  return (
    <li className="rounded-card border border-border bg-surface p-4" data-testid={`secret-${secret.name}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-control text-text">{SECRET_LABELS[secret.name] ?? secret.name}</span>
        <div className="flex items-center gap-2">
          <span className="font-mono text-small text-text-2">
            {secret.configured ? `••••${secret.masked}` : "Not set"}
          </span>
          <DiffBadge show={secret.overridden} />
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="New value"
          aria-label={`Replace ${SECRET_LABELS[secret.name] ?? secret.name}`}
          className={inputClass + " max-w-xs font-mono"}
        />
        <button
          type="button"
          disabled={!value || setSecret.isPending}
          onClick={() => {
            setSecret.mutate({ name: secret.name, value });
            setValue("");
          }}
          className={secondaryClass}
        >
          Replace
        </button>
        {secret.overridden && (
          <button
            type="button"
            onClick={() => clearSecret.mutate(secret.name)}
            className={ghostClass}
          >
            Reset to .env
          </button>
        )}
      </div>
    </li>
  );
}
