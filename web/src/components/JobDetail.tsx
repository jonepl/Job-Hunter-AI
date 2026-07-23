import { useState } from "react";

import type { JobDetail as JobDetailModel } from "../api/client";
import { useJob, useMarkStatus, useSaved } from "../hooks/useJob";
import { useJobGenerations } from "../hooks/useGeneration";
import { formatPostedAge, formatSalary } from "../lib/salary";
import { scoreState, type ScoreState } from "../lib/score";
import { statusLabel } from "../lib/status";
import { GenerationChip } from "./GenerationChip";
import { GenerationMenu } from "./GenerationMenu";
import { NeedsReviewDisclosure } from "./NeedsReviewDisclosure";
import { ProviderBadges } from "./ProviderBadges";
import { SaveStar } from "./SaveStar";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { ScoreChip } from "./ScoreChip";
import { StatusDropdown } from "./StatusDropdown";
import { ThresholdRail } from "./ThresholdRail";

// The right-hand detail pane (redesign Part H). Header (26px title, provider badges,
// score chip) → secondary mono line (seniority/experience/recommendation) → rail +
// threshold caption → action row (document menu, chips, save, status, view original)
// → Salary/Job type/Posted/Score meta grid → sections (skills, description, score
// breakdown, status history, provenance footer). Score breakdown + timeline are kept
// (conflict #9); they postdate the mock.

interface Props {
  jobId: number;
  onClose?: () => void;
}

const SCORE_TEXT: Record<ScoreState, string> = {
  qualify: "text-qualify",
  nearmiss: "text-nearmiss",
  below: "text-below",
};

const EMPLOYMENT_LABEL: Record<string, string> = {
  FULLTIME: "Full-time",
  PARTTIME: "Part-time",
  CONTRACTOR: "Contract",
  INTERN: "Internship",
  TEMPORARY: "Temporary",
};

function employmentLabel(value: string | null): string | null {
  if (!value) return null;
  return EMPLOYMENT_LABEL[value.toUpperCase()] ?? value;
}

export function JobDetail({ jobId, onClose }: Props) {
  const { data: job, isLoading, isError } = useJob(jobId);
  const markStatus = useMarkStatus(jobId);
  const setSaved = useSaved(jobId);
  const { data: generations } = useJobGenerations(jobId);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  if (isLoading) {
    return (
      <Shell onClose={onClose}>
        <p className="text-small text-text-2" role="status" aria-live="polite">
          Loading job…
        </p>
      </Shell>
    );
  }

  if (isError || !job) {
    return (
      <Shell onClose={onClose}>
        <p className="text-small text-text-2">
          Couldn’t load this job. Select it again to retry.
        </p>
      </Shell>
    );
  }

  // Secondary meta line — each segment omitted when null (conflict #8).
  const secondary = [
    job.seniorityLevel,
    job.yearsExperienceDetected !== null ? `${job.yearsExperienceDetected} yrs experience` : null,
    job.hireRecommendation ? `${job.hireRecommendation} to hire` : null,
  ].filter((segment): segment is string => segment !== null);

  const reviewGens = (generations ?? []).filter(
    (g) => g.status === "ready" && g.outcome === "needs_review" && !dismissed.has(g.id),
  );

  return (
    <Shell onClose={onClose}>
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="font-display text-h1 font-bold tracking-[-0.02em] text-text">
            {job.title}
          </h2>
          <p className="mt-1 text-small text-text-2">
            {job.company} · {job.location}
          </p>
          <div className="mt-3">
            <ProviderBadges platforms={job.platforms} variant="badges" />
          </div>
        </div>
        <ScoreChip
          score={job.score}
          threshold={job.threshold}
          nearMissFloor={job.nearMissFloor}
        />
      </header>

      {secondary.length > 0 && (
        <p className="mt-3 font-mono text-caption text-text-3" data-testid="secondary-meta">
          {secondary.join(" · ")}
        </p>
      )}

      <section className="mt-5">
        <ThresholdRail
          score={job.score}
          threshold={job.threshold}
          nearMissFloor={job.nearMissFloor}
        />
        {job.threshold !== null && (
          <p className="mt-1 text-right font-mono text-caption text-text-3">
            threshold {job.threshold}
          </p>
        )}
      </section>

      <section className="mt-5 flex flex-wrap items-center gap-3">
        <GenerationMenu jobId={jobId} />
        <GenerationChip jobId={jobId} kind="resume" />
        <GenerationChip jobId={jobId} kind="cover_letter" />
        <SaveStar
          saved={job.saved}
          onToggle={(saved) => setSaved.mutate(saved)}
          disabled={setSaved.isPending}
        />
        <StatusDropdown
          value={job.status}
          onChange={(status) => markStatus.mutate({ status })}
          disabled={markStatus.isPending}
        />
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="ml-auto text-control text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          >
            View original posting ↗
          </a>
        )}
      </section>

      {reviewGens.map((gen) => (
        <NeedsReviewDisclosure
          key={gen.id}
          kind={gen.kind}
          locations={gen.reviewLocations}
          onDismiss={() => setDismissed((prev) => new Set(prev).add(gen.id))}
        />
      ))}

      <MetaGrid job={job} />

      {(job.matchedSkills.length > 0 || job.missingSkills.length > 0) && (
        <Section title="Why this matched">
          <SkillPills have={job.matchedSkills} miss={job.missingSkills} />
        </Section>
      )}

      {job.description && (
        <Section title="About the role">
          <p className="whitespace-pre-line text-body leading-relaxed text-text-2 [text-wrap:pretty]">
            {job.description}
          </p>
        </Section>
      )}

      {job.scoreBreakdown && (
        <Section title="Score breakdown">
          <ScoreBreakdown breakdown={job.scoreBreakdown} />
        </Section>
      )}

      <Section title="Status history">
        <Timeline entries={job.statusHistory} />
      </Section>

      <ProvenanceFooter platforms={job.platforms} url={job.url} />
    </Shell>
  );
}

function Shell({ children, onClose }: { children: React.ReactNode; onClose?: () => void }) {
  return (
    <article className="rounded-card border border-border bg-surface p-6" data-testid="job-detail">
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="mb-4 text-control text-accent lg:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          ← Back to jobs
        </button>
      )}
      {children}
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h3 className="font-display text-h3 font-semibold">{title}</h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function MetaGrid({ job }: { job: JobDetailModel }) {
  const state = scoreState(job.score, job.threshold, job.nearMissFloor);
  const cells: { label: string; value: string; className: string }[] = [
    { label: "Salary", value: formatSalary(job) ?? "—", className: "text-body font-semibold text-text" },
    { label: "Job type", value: employmentLabel(job.employmentType) ?? "—", className: "text-body font-semibold text-text" },
    { label: "Posted", value: formatPostedAge(job.postedAt) ?? "—", className: "text-body font-semibold text-text" },
    {
      label: "Score",
      value: job.score !== null ? String(job.score) : "—",
      className: `font-mono text-h2 font-semibold ${SCORE_TEXT[state]}`,
    },
  ];
  return (
    <dl
      className="mt-6 grid grid-cols-2 overflow-hidden rounded-card border border-border sm:grid-cols-4"
      data-testid="meta-grid"
    >
      {cells.map(({ label, value, className }, i) => (
        <div
          key={label}
          className={`p-4 ${i > 0 ? "border-l border-border" : ""} ${i >= 2 ? "border-t border-border sm:border-t-0" : ""}`}
        >
          <dt className="font-mono text-tick uppercase tracking-[0.05em] text-text-3">{label}</dt>
          <dd className={`mt-1 ${className}`}>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function SkillPills({ have, miss }: { have: string[]; miss: string[] }) {
  return (
    <div className="space-y-2">
      {have.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-label uppercase tracking-[0.08em] text-text-3">Matched</span>
          {have.map((skill) => (
            <span
              key={`have-${skill}`}
              className="rounded-pill bg-accent-soft px-2 py-0.5 text-label text-accent"
              data-skill="have"
            >
              {skill}
            </span>
          ))}
        </div>
      )}
      {miss.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-label uppercase tracking-[0.08em] text-text-3">Missing</span>
          {miss.map((skill) => (
            <span
              key={`miss-${skill}`}
              className="rounded-pill bg-surface-2 px-2 py-0.5 text-label text-text-3 line-through"
              data-skill="miss"
            >
              {skill}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function Timeline({
  entries,
}: {
  entries: { fromStatus: string | null; toStatus: string; note: string | null; changedAt: string }[];
}) {
  return (
    <ol className="space-y-2" data-testid="status-timeline">
      {entries.map((entry, i) => (
        <li key={i} className="flex items-baseline gap-3 text-small">
          <span className="font-mono text-caption text-text-3">
            {new Date(entry.changedAt).toLocaleDateString()}
          </span>
          <span className="text-text-2">
            {entry.fromStatus
              ? `${statusLabel(entry.fromStatus)} → ${statusLabel(entry.toStatus)}`
              : `Created as ${statusLabel(entry.toStatus)}`}
            {entry.note ? ` · ${entry.note}` : ""}
          </span>
        </li>
      ))}
    </ol>
  );
}

function ProvenanceFooter({ platforms, url }: { platforms: string[]; url: string | null }) {
  return (
    <footer className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-2 px-4 py-3">
      <ProviderBadges platforms={platforms} variant="badges" />
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="text-control text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          Open job posting ↗
        </a>
      )}
    </footer>
  );
}
