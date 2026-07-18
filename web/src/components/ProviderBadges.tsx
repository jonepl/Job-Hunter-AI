import { platformName } from "../lib/platforms";

// A SET — dedup collapses the same posting across platforms, so never assume
// length 1 (ui-spec §5.3). Two forms: the card shows "via LinkedIn, Indeed"
// (inline text); the detail pane (later) shows uppercase mono badges.

interface Props {
  platforms: string[];
  variant?: "inline" | "badges";
}

export function ProviderBadges({ platforms, variant = "badges" }: Props) {
  if (platforms.length === 0) return null;

  if (variant === "inline") {
    return (
      <span data-testid="provider-badges" data-variant="inline">
        via {platforms.map(platformName).join(", ")}
      </span>
    );
  }

  return (
    <span className="inline-flex flex-wrap gap-1" data-testid="provider-badges" data-variant="badges">
      {platforms.map((platform) => (
        <span
          key={platform}
          className="rounded-control bg-surface-2 px-2 py-0.5 font-mono text-label uppercase tracking-[0.05em] text-text-2"
        >
          {platformName(platform)}
        </span>
      ))}
    </span>
  );
}
