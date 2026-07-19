"""Unit tests for the ResumeParserPort abstract contract."""

import inspect

import pytest

from src.core.ports.resume_parser_port import ResumeParserPort


def test_cannot_instantiate_abstract_port():
    """The port is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        ResumeParserPort()  # type: ignore[abstract]


def test_incomplete_subclass_fails_at_instantiation():
    """A subclass missing extract_text raises at instantiation, not runtime."""

    class Partial(ResumeParserPort):
        pass  # deliberately omits extract_text

    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


def test_port_declares_the_expected_methods():
    """The contract exposes exactly the text-extraction operation."""
    methods = {
        name
        for name, _ in inspect.getmembers(ResumeParserPort, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert methods == {"extract_text"}
