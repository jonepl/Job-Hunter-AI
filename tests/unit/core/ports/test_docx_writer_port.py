"""Unit tests for the DocxWriterPort abstract contract."""

import inspect

import pytest

from src.core.ports.docx_writer_port import DocxWriterPort


def test_cannot_instantiate_abstract_port():
    """The port is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        DocxWriterPort()  # type: ignore[abstract]


def test_incomplete_subclass_fails_at_instantiation():
    """A subclass missing a write method raises at instantiation, not runtime."""

    class Partial(DocxWriterPort):
        def write_resume(self, doc, path):
            return None
        # deliberately omits write_cover_letter

    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


def test_port_declares_the_expected_methods():
    """The contract exposes exactly the two render operations."""
    methods = {
        name
        for name, _ in inspect.getmembers(DocxWriterPort, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert methods == {"write_resume", "write_cover_letter"}
