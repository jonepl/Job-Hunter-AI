"""Response schemas for the web API.

These are the JSON contracts the React SPA consumes — deliberately lean read
models, not the full domain entities. Fields serialize as camelCase so the
generated TypeScript matches the component contracts (e.g. ``nearMissFloor`` per
ADR-033); Python code may still populate them by their snake_case names.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.core.domain.app_settings import AppSettings
from src.core.domain.date_posted import DatePosted
from src.core.domain.generation import (
    Generation,
    GenerationKind,
    GenerationOutcome,
    GenerationStatus,
)
from src.core.domain.match_result import ScoreBreakdown
from src.core.domain.resume import Resume
from src.core.domain.run_record import RunRecord, RunStatus, RunTrigger
from src.core.domain.scraper_name import ScraperName
from src.core.domain.search_profile import SearchProfile
from src.core.domain.status_history_entry import StatusHistoryEntry
from src.core.domain.stored_job import StoredJob
from src.core.domain.voice_descriptor import Person, Tone, VoiceDescriptor
from src.core.domain.work_type import WorkType
from src.infra.pricing import rates_for, show_cost_estimate

# The six human-set statuses — the only values the API accepts for a status write
# (machine states are never user-selectable, ui-spec §4). A bad value 422s.
HumanStatus = Literal[
    "applied", "started", "interviewing", "offer", "rejected", "not_interested"
]


class JobSummary(BaseModel):
    """A single job as shown in the job-list screen (one JobCard).

    Carries only what a card needs: identity, the deduplicated platforms it was
    seen on, and the score/threshold/near-miss-floor the ``<ThresholdRail>`` reads
    per job. The full nine-category breakdown lives on the (later) detail endpoint.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    title: str
    company: str
    location: str
    url: str | None
    platforms: list[str]
    score: int | None
    threshold: int | None
    near_miss_floor: int | None
    hire_recommendation: str | None
    seniority_level: str | None
    status: str
    saved: bool
    last_seen_at: datetime

    @classmethod
    def from_stored_job(cls, job: StoredJob) -> "JobSummary":
        """Build a JobSummary from a persisted StoredJob.

        Args:
            job: The stored job (with its optional evaluation and seen-on set).

        Returns:
            The lean card-shaped response model.
        """
        result = job.match_result
        return cls(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            platforms=job.seen_on,
            score=result.score if result is not None else None,
            threshold=job.threshold,
            near_miss_floor=job.near_miss_floor,
            hire_recommendation=result.hire_recommendation if result is not None else None,
            seniority_level=result.seniority_level if result is not None else None,
            status=job.status.value,
            saved=job.saved,
            last_seen_at=job.last_seen_at,
        )


class ScoreCategoryRow(BaseModel):
    """One row of the nine-category score breakdown, in rubric order.

    ``category`` is the domain field name (e.g. ``role_alignment``); the frontend
    formats it into a label. Emitting an ordered list keeps the rubric order
    backend-owned and the component generic.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    category: str
    earned: int
    max: int
    reasoning: str


class StatusHistoryEntryOut(BaseModel):
    """A status-history row for the detail screen's action timeline (ADR-025)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    from_status: str | None
    to_status: str
    note: str | None
    changed_at: datetime

    @classmethod
    def from_entry(cls, entry: StatusHistoryEntry) -> "StatusHistoryEntryOut":
        """Build the response row from a domain StatusHistoryEntry."""
        return cls(
            from_status=entry.from_status.value if entry.from_status else None,
            to_status=entry.to_status.value,
            note=entry.note,
            changed_at=entry.changed_at,
        )


class JobDetail(BaseModel):
    """The full detail fan-out for one job (ui-spec §6.1).

    Everything ``JobSummary`` carries plus the nine-category breakdown, matched /
    missing skills, the description, the lifecycle (status, saved, history), and a
    ``generations`` stub (populated once F ships). Never carries generated-document
    content or raw resume text (ui-spec §7).
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    title: str
    company: str
    location: str
    url: str | None
    description: str | None
    platforms: list[str]
    score: int | None
    threshold: int | None
    near_miss_floor: int | None
    hire_recommendation: str | None
    seniority_level: str | None
    years_experience_detected: int | None
    summary: str | None
    matched_skills: list[str]
    missing_skills: list[str]
    score_breakdown: list[ScoreCategoryRow] | None
    status: str
    saved: bool
    status_history: list[StatusHistoryEntryOut]
    generations: list = []  # unused stub; the chip reads GET /jobs/{id}/generations (W6)
    last_seen_at: datetime

    @classmethod
    def from_stored_job(
        cls, job: StoredJob, history: list[StatusHistoryEntry]
    ) -> "JobDetail":
        """Build the detail model from a stored job and its status history.

        Args:
            job: The stored job with its optional evaluation and seen-on set.
            history: The job's status-history entries, oldest-first.

        Returns:
            The full detail response model.
        """
        result = job.match_result
        return cls(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            description=job.description,
            platforms=job.seen_on,
            score=result.score if result is not None else None,
            threshold=job.threshold,
            near_miss_floor=job.near_miss_floor,
            hire_recommendation=result.hire_recommendation if result is not None else None,
            seniority_level=result.seniority_level if result is not None else None,
            years_experience_detected=(
                result.years_experience_detected if result is not None else None
            ),
            summary=result.summary if result is not None else None,
            matched_skills=result.matched_skills if result is not None else [],
            missing_skills=result.missing_skills if result is not None else [],
            score_breakdown=(
                _breakdown_rows(result.score_breakdown) if result is not None else None
            ),
            status=job.status.value,
            saved=job.saved,
            status_history=[StatusHistoryEntryOut.from_entry(e) for e in history],
            last_seen_at=job.last_seen_at,
        )


def _breakdown_rows(breakdown: ScoreBreakdown) -> list[ScoreCategoryRow]:
    """Flatten a ScoreBreakdown into ordered category rows (rubric order)."""
    rows: list[ScoreCategoryRow] = []
    for name in ScoreBreakdown.model_fields:
        category = getattr(breakdown, name)
        rows.append(
            ScoreCategoryRow(
                category=name,
                earned=category.earned,
                max=category.max,
                reasoning=category.reasoning,
            )
        )
    return rows


class StatusUpdate(BaseModel):
    """Request body for ``PATCH /jobs/{id}/status`` — a human status write."""

    status: HumanStatus
    note: str | None = None


class SavedUpdate(BaseModel):
    """Request body for ``PATCH /jobs/{id}/saved`` — the bookmark toggle."""

    saved: bool


class ResumeOut(BaseModel):
    """One stored master-resume version, provenance only (ui-spec §14.2).

    Carries *about* the resume — version, source file, size, parsed counts, which
    version is active — never the resume text itself (``raw_text``) or its content
    hash. The privacy boundary (ADR-028): resume content never leaves the API.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    version: int
    filename: str
    size_bytes: int
    skill_count: int
    role_count: int
    is_active: bool
    uploaded_at: datetime | None

    @classmethod
    def from_resume(cls, resume: Resume) -> "ResumeOut":
        """Build the provenance-only response model from a stored Resume."""
        return cls(
            version=resume.version,
            filename=resume.filename,
            size_bytes=resume.size_bytes,
            skill_count=resume.skill_count,
            role_count=resume.role_count,
            is_active=resume.is_active,
            uploaded_at=resume.uploaded_at,
        )


class ResumeState(BaseModel):
    """The master-resume panel's full read model — active version plus history.

    ``versions`` is newest-first; ``active`` is the one with ``is_active`` (or None
    when nothing is stored yet — a normal empty state, not an error).
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    active: ResumeOut | None
    versions: list[ResumeOut]

    @classmethod
    def from_versions(cls, versions: list[Resume]) -> "ResumeState":
        """Build the panel state from a list of stored versions (newest-first)."""
        active = next((r for r in versions if r.is_active), None)
        return cls(
            active=ResumeOut.from_resume(active) if active is not None else None,
            versions=[ResumeOut.from_resume(r) for r in versions],
        )


class GenerationOut(BaseModel):
    """One generated-document record for the chip, provenance only (ui-spec §5.4/§7).

    Carries the async ``status``, the formatter ``outcome`` (only meaningful once
    ``status == "ready"`` — surfaced as null while pending/failed), the repair note,
    and the structural ``reviewLocations`` for a ``needs_review`` outcome. It
    **never** carries document content or the server-side ``file_path``: the client
    reaches the file through ``GET /generations/{id}/download`` (ADR-034 §3).
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    job_id: int
    kind: GenerationKind
    status: GenerationStatus
    outcome: GenerationOutcome | None
    review_locations: list[str]
    repair_note: str
    created_at: datetime

    @classmethod
    def from_generation(cls, generation: Generation) -> "GenerationOut":
        """Build the response model, hiding the placeholder outcome until ready."""
        return cls(
            id=generation.id,
            job_id=generation.job_id,
            kind=generation.kind,
            status=generation.status,
            outcome=generation.outcome if generation.status == "ready" else None,
            review_locations=generation.review_locations,
            repair_note=generation.repair_note,
            created_at=generation.created_at,
        )


class VoiceIn(BaseModel):
    """Optional cover-letter voice on a generate request (ADR-030, structured only)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    tone: Tone = "direct"
    person: Person = "first_person"
    style_notes: str = ""

    def to_descriptor(self) -> VoiceDescriptor:
        """Map the request voice to the domain VoiceDescriptor."""
        return VoiceDescriptor(
            tone=self.tone, person=self.person, style_notes=self.style_notes
        )


class GenerateRequest(BaseModel):
    """Request body for ``POST /jobs/{id}/generate`` — start an async generation.

    ``voice`` applies only to a cover letter; when omitted the router seeds the
    env-configured default voice (the in-browser voice form arrives with W7).
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    kind: GenerationKind
    voice: VoiceIn | None = None


# --- W7: settings, secrets, and search profiles ---------------------------


class ProviderRates(BaseModel):
    """One provider's configured per-1M-token rates (read-only, ``.env``-owned)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    input_per_1m: float
    output_per_1m: float


class PricingOut(BaseModel):
    """The configured token pricing, surfaced read-only on the provider cards.

    Rates live in ``.env`` (``docs/env.md`` is the source of truth) and always display;
    ``show_cost_estimate`` reflects ``SHOW_COST_ESTIMATE`` so the UI can note that the
    rates only *apply* to tracking when it is enabled. Never writable (no differs-from-.env
    semantics) — absent from ``SettingsUpdate`` and ``SettingsDefaults``.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    show_cost_estimate: bool
    openai: ProviderRates
    anthropic: ProviderRates


class SettingsOut(BaseModel):
    """The global settings screen state — effective values + the ``.env`` defaults.

    ``envDefaults`` lets the UI show a "differs from .env" indicator per field
    (ADR-031). ``secrets`` carries **masked** status only — never a key value.
    ``pricing`` is read-only configured token rates (never in ``SettingsUpdate``).
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    evaluator_provider: str
    evaluator_model: str | None
    schedule_cron: str
    schedule_timezone: str
    enrichment_mode: str
    voice: VoiceIn
    env_defaults: "SettingsDefaults"
    secrets: list["SecretStatus"]
    pricing: "PricingOut"

    @classmethod
    def build(
        cls,
        settings: AppSettings,
        env_defaults: AppSettings,
        secrets: list[dict],
    ) -> "SettingsOut":
        """Assemble the response from the effective settings, the .env seed, secrets."""
        openai_in, openai_out = rates_for("openai")
        anthropic_in, anthropic_out = rates_for("anthropic")
        return cls(
            evaluator_provider=settings.evaluator_provider,
            evaluator_model=settings.evaluator_model,
            schedule_cron=settings.schedule_cron,
            schedule_timezone=settings.schedule_timezone,
            enrichment_mode=settings.enrichment_mode,
            voice=VoiceIn(
                tone=settings.voice.tone,
                person=settings.voice.person,
                style_notes=settings.voice.style_notes,
            ),
            env_defaults=SettingsDefaults.from_settings(env_defaults),
            secrets=[SecretStatus(**s) for s in secrets],
            pricing=PricingOut(
                show_cost_estimate=show_cost_estimate(),
                openai=ProviderRates(input_per_1m=openai_in, output_per_1m=openai_out),
                anthropic=ProviderRates(
                    input_per_1m=anthropic_in, output_per_1m=anthropic_out
                ),
            ),
        )


class SettingsDefaults(BaseModel):
    """The `.env`-derived global settings, for the UI's differs-from-.env diff."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    evaluator_provider: str
    evaluator_model: str | None
    schedule_cron: str
    schedule_timezone: str
    enrichment_mode: str
    voice: VoiceIn

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "SettingsDefaults":
        """Build from an AppSettings derived purely from ``.env``."""
        return cls(
            evaluator_provider=settings.evaluator_provider,
            evaluator_model=settings.evaluator_model,
            schedule_cron=settings.schedule_cron,
            schedule_timezone=settings.schedule_timezone,
            enrichment_mode=settings.enrichment_mode,
            voice=VoiceIn(
                tone=settings.voice.tone,
                person=settings.voice.person,
                style_notes=settings.voice.style_notes,
            ),
        )


class SettingsUpdate(BaseModel):
    """Request body for ``PUT /api/settings`` — the editable global settings."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    evaluator_provider: Literal["openai", "anthropic"]
    evaluator_model: str | None = None
    schedule_cron: str = ""
    schedule_timezone: str = "UTC"
    enrichment_mode: Literal["shadow", "enforce"] = "shadow"
    voice: VoiceIn = VoiceIn()

    def to_settings(self) -> AppSettings:
        """Map the request to the domain AppSettings entity."""
        return AppSettings(
            evaluator_provider=self.evaluator_provider,
            evaluator_model=self.evaluator_model or None,
            schedule_cron=self.schedule_cron,
            schedule_timezone=self.schedule_timezone,
            enrichment_mode=self.enrichment_mode,
            voice=self.voice.to_descriptor(),
        )


class SecretStatus(BaseModel):
    """A secret's masked status — never its value (ADR-031)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    configured: bool
    masked: str
    overridden: bool


class SecretUpdate(BaseModel):
    """Request body for ``PUT /api/settings/secrets/{name}`` — a write-only replace."""

    value: str


class SchedulePreview(BaseModel):
    """The next few cron fire times for the schedule preview."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    next_runs: list[datetime]


class ProfileOut(BaseModel):
    """One stored search profile as the Settings UI sees it."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    name: str
    query: str
    location: str
    work_types: list[str] | None
    date_posted: str | None
    active_scrapers: list[str]
    score_threshold: int
    top_results: int | None
    enabled: bool
    last_run_at: str | None
    last_run_status: str | None

    @classmethod
    def from_profile(cls, profile: SearchProfile) -> "ProfileOut":
        """Build the response model from a stored SearchProfile."""
        return cls(
            id=profile.profile_id,
            name=profile.name,
            query=profile.query,
            location=profile.location,
            work_types=(
                [w.value for w in profile.work_types] if profile.work_types else None
            ),
            date_posted=profile.date_posted.value if profile.date_posted else None,
            active_scrapers=[s.value for s in profile.active_scrapers],
            score_threshold=profile.score_threshold,
            top_results=profile.top_results,
            enabled=profile.enabled,
            last_run_at=profile.last_run_at,
            last_run_status=profile.last_run_status,
        )


class ProfileIn(BaseModel):
    """Request body for creating/updating a search profile."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = ""
    query: str
    location: str | None = None
    work_types: list[str] | None = None
    date_posted: str | None = "3days"
    active_scrapers: list[str] = ["linkedin", "indeed", "glassdoor", "ziprecruiter"]
    score_threshold: int = 75
    top_results: int | None = None
    enabled: bool = True

    def to_profile(self, profile_id: int = 0) -> SearchProfile:
        """Map the request to a SearchProfile, applying the location-resolution rule.

        Raises:
            ValueError: On an unknown enum value, or a missing location when the work
                type is not remote-only (mirrors ``SearchProfile.from_env``).
        """
        work_types = (
            [WorkType(w) for w in self.work_types] if self.work_types else None
        )
        location = self.location
        if not location:
            if work_types == [WorkType.REMOTE]:
                location = "United States"
            else:
                raise ValueError(
                    "location is required unless the work type is remote only"
                )
        return SearchProfile(
            profile_id=profile_id,
            name=self.name,
            query=self.query,
            location=location,
            work_types=work_types,
            date_posted=DatePosted(self.date_posted) if self.date_posted else None,
            active_scrapers=[ScraperName(s) for s in self.active_scrapers],
            score_threshold=self.score_threshold,
            top_results=self.top_results,
            enabled=self.enabled,
        )


# --- W8: web-triggered runs ------------------------------------------------


class RunOut(BaseModel):
    """One run's lifecycle + summary for the "Run search now" control (W8).

    Carries the async ``status`` and the summary counts (only meaningful once
    ``status == "succeeded"``), the trigger, and timing. ``error`` is a bare
    exception *type name* on a failed run — never a raw message (CLAUDE.md #2).
    It carries no job content: the evaluated jobs land in the job list, which the
    client refetches when a run succeeds.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    status: RunStatus
    trigger: RunTrigger
    profiles_run: int
    jobs_found: int
    new_jobs: int
    qualifying: int
    error: str
    started_at: datetime
    finished_at: datetime | None

    @classmethod
    def from_run(cls, run: RunRecord) -> "RunOut":
        """Build the response model from a RunRecord."""
        return cls(
            id=run.id,
            status=run.status,
            trigger=run.trigger,
            profiles_run=run.profiles_run,
            jobs_found=run.jobs_found,
            new_jobs=run.new_jobs,
            qualifying=run.qualifying,
            error=run.error,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
