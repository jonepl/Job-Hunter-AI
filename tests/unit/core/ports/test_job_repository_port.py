"""Unit tests for the JobRepositoryPort abstract contract."""

import inspect

import pytest

from src.core.ports.job_repository_port import JobRepositoryPort


def test_cannot_instantiate_abstract_port():
    """The port is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        JobRepositoryPort()  # type: ignore[abstract]


def test_incomplete_subclass_fails_at_instantiation():
    """A subclass missing an abstract method raises at instantiation, not runtime."""

    class Partial(JobRepositoryPort):
        def find_by_fingerprint(self, key):
            return None
        # deliberately omits the other abstract methods

    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


def test_port_declares_the_expected_methods():
    """The contract exposes exactly the dedup, save, and sighting operations."""
    methods = {
        name
        for name, _ in inspect.getmembers(JobRepositoryPort, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert methods == {
        "list_jobs",
        "get_job",
        "set_status",
        "set_saved",
        "find_by_fingerprint",
        "find_near_misses",
        "save_job",
        "record_sighting",
        "get_seen_on",
    }
