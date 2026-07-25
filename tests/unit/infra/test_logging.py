"""Unit tests for src/infra/logging.py — logging configuration."""

import logging

import pytest

from src.infra.logging import configure_logging


@pytest.fixture(autouse=True)
def reset_root_logger():
    """Remove handlers added by configure_logging() after each test."""
    root = logging.getLogger()
    before = list(root.handlers)
    yield
    for h in list(root.handlers):
        if h not in before:
            h.close()
            root.removeHandler(h)


def test_configure_logging_creates_log_dir(tmp_path, monkeypatch):
    """configure_logging() creates the logs/ directory when it does not exist."""
    monkeypatch.chdir(tmp_path)
    configure_logging()
    assert (tmp_path / "logs").is_dir()


def test_configure_logging_adds_handlers(tmp_path, monkeypatch):
    """configure_logging() adds at least two handlers to the root logger."""
    monkeypatch.chdir(tmp_path)
    root = logging.getLogger()
    before_count = len(root.handlers)
    configure_logging()
    assert len(root.handlers) >= before_count + 2
