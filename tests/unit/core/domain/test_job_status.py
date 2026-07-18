"""Unit tests for the JobStatus lifecycle enum (ADR-025)."""

from src.core.domain.job_status import (
    HUMAN_STATUSES,
    MACHINE_STATUSES,
    JobStatus,
    is_human_set,
)


def test_nine_lifecycle_values():
    """The lifecycle has exactly the nine ADR-025 states."""
    assert {s.value for s in JobStatus} == {
        "new",
        "evaluated",
        "pre_filtered",
        "applied",
        "started",
        "interviewing",
        "offer",
        "rejected",
        "not_interested",
    }


def test_machine_and_human_partition_all_states():
    """Every status is either machine-set or human-set, never both."""
    assert MACHINE_STATUSES == {
        JobStatus.NEW,
        JobStatus.EVALUATED,
        JobStatus.PRE_FILTERED,
    }
    assert MACHINE_STATUSES | HUMAN_STATUSES == set(JobStatus)
    assert MACHINE_STATUSES.isdisjoint(HUMAN_STATUSES)


def test_is_human_set_for_human_states():
    """The six human-set states classify as human."""
    for status in (
        JobStatus.APPLIED,
        JobStatus.STARTED,
        JobStatus.INTERVIEWING,
        JobStatus.OFFER,
        JobStatus.REJECTED,
        JobStatus.NOT_INTERESTED,
    ):
        assert is_human_set(status) is True


def test_is_human_set_false_for_machine_states():
    """The three machine-set states are not human-set."""
    for status in (JobStatus.NEW, JobStatus.EVALUATED, JobStatus.PRE_FILTERED):
        assert is_human_set(status) is False


def test_job_status_is_str_enum():
    """JobStatus is a str enum, so its value serializes directly."""
    assert JobStatus.APPLIED == "applied"
