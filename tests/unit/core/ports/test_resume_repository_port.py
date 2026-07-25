"""Unit tests for the ResumeRepositoryPort abstract contract."""

import inspect

import pytest

from src.core.ports.resume_repository_port import ResumeRepositoryPort


def test_cannot_instantiate_abstract_port():
    """The port is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        ResumeRepositoryPort()  # type: ignore[abstract]


def test_incomplete_subclass_fails_at_instantiation():
    """A subclass missing an abstract method raises at instantiation, not runtime."""

    class Partial(ResumeRepositoryPort):
        def get_active(self):
            return None

        # deliberately omits the other abstract methods

    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


def test_port_declares_the_expected_methods():
    """The contract exposes exactly the version-store and restore operations."""
    methods = {
        name
        for name, _ in inspect.getmembers(ResumeRepositoryPort, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert methods == {
        "get_active",
        "save_version",
        "list_versions",
        "activate",
        "find_by_hash",
    }
