"""Unit tests for the GenerationRepositoryPort abstract contract."""

import inspect

import pytest

from src.core.ports.generation_repository_port import GenerationRepositoryPort


def test_cannot_instantiate_abstract_port():
    """The port is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        GenerationRepositoryPort()  # type: ignore[abstract]


def test_incomplete_subclass_fails_at_instantiation():
    """A subclass missing an abstract method raises at instantiation, not runtime."""

    class Partial(GenerationRepositoryPort):
        def save(self, generation):
            return generation
        # deliberately omits get and list_for_job

    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


def test_port_declares_the_expected_methods():
    """The contract exposes exactly the save/get/list operations."""
    methods = {
        name
        for name, _ in inspect.getmembers(
            GenerationRepositoryPort, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    }
    assert methods == {"save", "get", "list_for_job"}
