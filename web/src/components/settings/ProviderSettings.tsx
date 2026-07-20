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
} from "./shared";

// Evaluator provider section: the global provider + model + pre-filter mode, plus the
// three API-key secrets. Provider and pre-filter are radio cards (design: Settings.dc.html);
// the configured token rates come from settings.pricing (read-only, .env-owned). Secrets are
// write-only (ADR-031) — the panel shows only a masked suffix, never a key value or prefix.

type ProviderValue = "openai" | "anthropic";

// Display metadata for the two provider cards. The default-model strings mirror `_MODEL`
// in openai_evaluator.py:19 / anthropic_evaluator.py:20 — they are display only, not the
// source of truth for behavior. Bump both places together on a model change.
const PROVIDERS: {
  value: ProviderValue;
  name: string;
  description: string;
  defaultModel: string;
}[] = [
  {
    value: "openai",
    name: "OpenAI",
    description: "Strict JSON response format.",
    defaultModel: "gpt-4o",
  },
  {
    value: "anthropic",
    name: "Anthropic",
    description: "Prompt-enforced JSON.",
    defaultModel: "claude-sonnet-4-5",
  },
];

const PREFILTER_MODES: { value: "shadow" | "enforce"; name: string; description: string }[] = [
  { value: "shadow", name: "Shadow", description: "Log what would be skipped, score everything" },
  { value: "enforce", name: "Enforce", description: "Skip pre-filtered jobs before scoring" },
];

const SECRET_LABELS: Record<string, string> = {
  openai_api_key: "OpenAI API key",
  anthropic_api_key: "Anthropic API key",
  gemini_api_key: "Gemini API key",
};

// The key each provider requires — used only for the honest "used by the current provider"
// hint; never to reorder or hide a key.
const PROVIDER_SECRET: Record<ProviderValue, string> = {
  openai: "openai_api_key",
  anthropic: "anthropic_api_key",
};

const badgeClass =
  "rounded-pill bg-accent-soft px-[7px] py-0.5 font-mono text-[9px] uppercase tracking-[0.05em] text-accent";

/** The 18px radio dot shared by the provider and pre-filter cards. */
function RadioDot({ active }: { active: boolean }) {
  return (
    <span
      className={
        "flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border-2 " +
        (active ? "border-accent" : "border-border-strong")
      }
    >
      {active && <span className="h-2 w-2 rounded-full bg-accent" />}
    </span>
  );
}

function formatRate(n: number): string {
  return `$${n.toFixed(2)}`;
}

export function ProviderSettings() {
  const { data: settings, isLoading, isError } = useSettings();
  const update = useUpdateSettings();
  const [provider, setProvider] = useState<ProviderValue | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [mode, setMode] = useState<"shadow" | "enforce" | null>(null);

  if (isLoading) return <PanelStatus>Loading settings…</PanelStatus>;
  if (isError || !settings) return <PanelError />;

  const providerValue = provider ?? (settings.evaluatorProvider as ProviderValue);
  const modelValue = model ?? settings.evaluatorModel ?? "";
  const modeValue = mode ?? (settings.enrichmentMode as "shadow" | "enforce");
  const defaultProvider = settings.envDefaults.evaluatorProvider;
  const selectedDefaultModel =
    PROVIDERS.find((p) => p.value === providerValue)?.defaultModel ?? "gpt-4o";

  function save() {
    update.mutate({
      ...settingsToUpdate(settings!),
      evaluatorProvider: providerValue,
      evaluatorModel: modelValue || null,
      enrichmentMode: modeValue,
    });
  }

  return (
    <section data-testid="provider-settings" className="space-y-6">
      <PanelHeader
        title="Evaluator provider"
        subtitle="Which LLM scores each job, and the keys the run uses."
      />

      {/* Provider radio cards */}
      <div>
        <div role="radiogroup" aria-label="Provider" className="space-y-3">
          {PROVIDERS.map((p) => {
            const active = providerValue === p.value;
            const rates = settings.pricing[p.value];
            return (
              <button
                key={p.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setProvider(p.value)}
                className={
                  "flex w-full items-center gap-3.5 rounded-card border p-4 text-left transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 " +
                  (active ? "border-accent bg-accent-soft" : "border-border bg-surface")
                }
              >
                <RadioDot active={active} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-control font-semibold text-text">{p.name}</span>
                    {p.value === defaultProvider && <span className={badgeClass}>Default</span>}
                  </div>
                  <p className="mt-0.5 text-small text-text-2">{p.description}</p>
                  <p className="mt-0.5 font-mono text-label text-text-3">{p.defaultModel}</p>
                </div>
                <span className="shrink-0 text-right font-mono text-label text-text-3">
                  {formatRate(rates.inputPer1M)} / {formatRate(rates.outputPer1M)}
                  <br />
                  per 1M in / out
                </span>
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-caption text-text-3">
          {settings.pricing.showCostEstimate
            ? "Configured input / output token rates per 1M tokens."
            : "Cost tracking is off — rates apply only when SHOW_COST_ESTIMATE is enabled."}
        </p>
      </div>

      <Field
        label="Model override"
        htmlFor="model"
        hint="Blank uses the provider default."
      >
        <input
          id="model"
          value={modelValue}
          onChange={(e) => setModel(e.target.value)}
          placeholder={selectedDefaultModel}
          className={inputClass + " font-mono"}
        />
      </Field>

      {/* Pre-filter radio card */}
      <div className="max-w-md rounded-card border border-border bg-surface p-4">
        <h3 className="text-control font-semibold text-text">Pre-filter mode</h3>
        <p className="mt-1 text-small text-text-2">
          A cheap upstream model skips obvious non-matches before paid scoring. Shadow mode
          measures its accuracy before you trust it.
        </p>
        <div role="radiogroup" aria-label="Pre-filter mode" className="mt-3 space-y-2">
          {PREFILTER_MODES.map((m) => {
            const active = modeValue === m.value;
            return (
              <button
                key={m.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setMode(m.value)}
                className={
                  "flex w-full items-center gap-3.5 rounded-control border p-3 text-left transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 " +
                  (active ? "border-accent bg-accent-soft" : "border-border bg-surface")
                }
              >
                <RadioDot active={active} />
                <div className="min-w-0 flex-1">
                  <span className="text-control font-semibold text-text">{m.name}</span>
                  <p className="mt-0.5 text-small text-text-2">{m.description}</p>
                </div>
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-caption text-text-3">
          The pre-filter runs on Gemini and uses the Gemini API key below.
        </p>
      </div>

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
            <SecretRow
              key={secret.name}
              secret={secret}
              usedByCurrent={PROVIDER_SECRET[providerValue] === secret.name}
            />
          ))}
        </ul>
      </div>
    </section>
  );
}

function SecretRow({
  secret,
  usedByCurrent,
}: {
  secret: SecretStatus;
  usedByCurrent: boolean;
}) {
  const setSecret = useSetSecret();
  const clearSecret = useClearSecret();
  const [value, setValue] = useState("");

  return (
    <li className="rounded-card border border-border bg-surface p-4" data-testid={`secret-${secret.name}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-control text-text">
          {SECRET_LABELS[secret.name] ?? secret.name}
          {usedByCurrent && (
            <span className="ml-2 text-caption text-text-3">used by the current provider</span>
          )}
        </span>
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
