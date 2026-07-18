import { useJob, useMarkStatus, useSaved } from "../hooks/useJob";
import { statusLabel } from "../lib/status";
import { GenerationChip } from "./GenerationChip";
import { ProviderBadges } from "./ProviderBadges";
import { SaveStar } from "./SaveStar";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { ScoreChip } from "./ScoreChip";
import { StatusDropdown } from "./StatusDropdown";
import { ThresholdRail } from "./ThresholdRail";

// The right-hand detail pane (ui-spec §6.1), reduced to what the data model
// carries: identity, provider set, score + breakdown, the lifecycle controls
// (status dropdown + ★ save), skills, description, and the status timeline. The
// Generated-documents block is a stub until Story F. Salary / posted-age /
// job-type / profile provenance are not in the model and are omitted.

interface Props {
  jobId: number;
  onClose?: () => void;
}

export function JobDetail({ jobId, onClose }: Props) {
  const { data: job, isLoading, isError } = useJob(jobId);
  const markStatus = useMarkStatus(jobId);
  const setSaved = useSaved(jobId);

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

  return (
    <Shell onClose={onClose}>
      <header>
        <h2 className="font-display text-h2">{job.title}</h2>
        <p className="mt-1 text-small text-text-2">
          {job.company} · {job.location}
        </p>
        <div className="mt-3">
          <ProviderBadges platforms={job.platforms} variant="badges" />
        </div>
      </header>

      <section className="mt-5">
        <ScoreChip
          score={job.score}
          threshold={job.threshold}
          nearMissFloor={job.nearMissFloor}
        />
        <ThresholdRail
          score={job.score}
          threshold={job.threshold}
          nearMissFloor={job.nearMissFloor}
        />
      </section>

      <section className="mt-5 flex flex-wrap items-center gap-3">
        <StatusDropdown
          value={job.status}
          onChange={(status) => markStatus.mutate({ status })}
          disabled={markStatus.isPending}
        />
        <SaveStar
          saved={job.saved}
          onToggle={(saved) => setSaved.mutate(saved)}
          disabled={setSaved.isPending}
        />
      </section>

      <MetaGrid job={job} />

      {job.scoreBreakdown && (
        <Section title="Score breakdown">
          <ScoreBreakdown breakdown={job.scoreBreakdown} />
        </Section>
      )}

      {(job.matchedSkills.length > 0 || job.missingSkills.length > 0) && (
        <Section title="Why this matched">
          <SkillPills have={job.matchedSkills} miss={job.missingSkills} />
        </Section>
      )}

      {job.description && (
        <Section title="About the role">
          <p className="whitespace-pre-line text-small text-text-2">{job.description}</p>
        </Section>
      )}

      <Section title="Status history">
        <Timeline entries={job.statusHistory} />
      </Section>

      <Section title="Generated documents">
        <div className="flex flex-wrap gap-2">
          <GenerationChip kind="resume" />
          <GenerationChip kind="cover_letter" />
        </div>
        <p className="mt-2 text-caption text-text-3">Document generation arrives with a later story.</p>
      </Section>

      {job.url && (
        <a
          href={job.url}
          target="_blank"
          rel="noreferrer"
          className="mt-6 inline-block text-control text-accent transition-colors duration-fast hover:text-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
        >
          View original posting ↗
        </a>
      )}
    </Shell>
  );
}

function Shell({ children, onClose }: { children: React.ReactNode; onClose?: () => void }) {
  return (
    <article
      className="rounded-card border border-border bg-surface p-6"
      data-testid="job-detail"
    >
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
      <h3 className="font-display text-body font-semibold">{title}</h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function MetaGrid({
  job,
}: {
  job: { score: number | null; seniorityLevel: string | null; yearsExperienceDetected: number | null; hireRecommendation: string | null };
}) {
  const cells: [string, string][] = [
    ["Score", job.score !== null ? String(job.score) : "—"],
    ["Seniority", job.seniorityLevel ?? "—"],
    ["Experience", job.yearsExperienceDetected !== null ? `${job.yearsExperienceDetected} yrs` : "—"],
    ["Recommendation", job.hireRecommendation ?? "—"],
  ];
  return (
    <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4" data-testid="meta-grid">
      {cells.map(([label, value]) => (
        <div key={label}>
          <dt className="font-mono text-label uppercase tracking-[0.05em] text-text-3">{label}</dt>
          <dd className="mt-1 font-mono text-small text-text">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function SkillPills({ have, miss }: { have: string[]; miss: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {have.map((skill) => (
        <span
          key={`have-${skill}`}
          className="rounded-pill bg-accent-soft px-2 py-0.5 text-label text-accent"
          data-skill="have"
        >
          {skill}
        </span>
      ))}
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
