"""Unit tests for the EnrichmentSummary domain entity."""

from src.core.domain.enrichment_summary import GRADUATION_MIN_EVALS, EnrichmentSummary


def _summary(**overrides) -> EnrichmentSummary:
    """Build an EnrichmentSummary with sensible shadow-mode defaults."""
    base = dict(
        mode="shadow",
        total_jobs=10,
        flagged_count=4,
        evaluated_count=10,
        false_skips=0,
    )
    base.update(overrides)
    return EnrichmentSummary(**base)


def test_false_skip_rate_computes_fraction():
    """false_skip_rate is false_skips / flagged_count when measurable."""
    summary = _summary(flagged_count=4, false_skips=1)

    assert summary.false_skip_rate == 0.25


def test_false_skip_rate_none_when_nothing_flagged():
    """false_skip_rate is None when no jobs were flagged (0/0 is undefined)."""
    summary = _summary(flagged_count=0, false_skips=0)

    assert summary.false_skip_rate is None


def test_false_skip_rate_none_in_enforce_mode():
    """Enforce mode cannot measure false-skips, so the rate is None."""
    summary = _summary(mode="enforce", false_skips=None)

    assert summary.false_skip_rate is None


def test_graduation_ready_true_when_criterion_met():
    """Graduation is ready: shadow, 0 false-skips, >= GRADUATION_MIN_EVALS evals."""
    summary = _summary(evaluated_count=GRADUATION_MIN_EVALS, false_skips=0)

    assert summary.graduation_ready is True


def test_graduation_not_ready_below_min_evals():
    """Graduation is not ready below the evaluated-jobs floor."""
    summary = _summary(evaluated_count=GRADUATION_MIN_EVALS - 1, false_skips=0)

    assert summary.graduation_ready is False


def test_graduation_not_ready_with_false_skips():
    """Graduation is not ready while any false-skip has occurred."""
    summary = _summary(evaluated_count=GRADUATION_MIN_EVALS, false_skips=1)

    assert summary.graduation_ready is False


def test_graduation_not_ready_in_enforce_mode():
    """Enforce mode is already graduated — it never reports 'ready'."""
    summary = _summary(mode="enforce", evaluated_count=100, false_skips=None)

    assert summary.graduation_ready is False


def test_graduation_not_ready_when_pre_filter_errored():
    """A run with any pre-filter errors only partially measured precision."""
    summary = _summary(evaluated_count=GRADUATION_MIN_EVALS, false_skips=0, error_count=3)

    assert summary.graduation_ready is False


def test_error_count_defaults_to_zero():
    """error_count defaults to 0 when not provided."""
    summary = _summary()

    assert summary.error_count == 0
