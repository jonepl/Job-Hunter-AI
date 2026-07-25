"""Unit tests for src/cli/args.py — argument parsing."""

from unittest.mock import patch

import pytest

from src.cli.args import parse_args


def test_parse_args_all_defaults_none():
    """The default (no-subcommand) run is a search with all fields None."""
    with patch("sys.argv", ["main"]):
        args = parse_args()
    assert args.command is None
    assert args.query is None
    assert args.location is None
    assert args.work_type is None
    assert args.date_posted is None
    assert args.scrapers is None
    assert args.evaluator_model is None


def test_parse_args_query():
    """--query value is stored in args.query."""
    with patch("sys.argv", ["main", "--query", "Software Engineer"]):
        args = parse_args()
    assert args.query == "Software Engineer"


def test_parse_args_evaluator_model():
    """--evaluator-model value is stored in args.evaluator_model."""
    with patch("sys.argv", ["main", "--evaluator-model", "gpt-4o-mini"]):
        args = parse_args()
    assert args.evaluator_model == "gpt-4o-mini"


def test_parse_args_work_type_single():
    """--work-type with a single value is stored as a one-element list."""
    with patch("sys.argv", ["main", "--work-type", "remote"]):
        args = parse_args()
    assert args.work_type == ["remote"]


def test_parse_args_work_type_multiple():
    """--work-type with multiple values is stored as a list."""
    with patch("sys.argv", ["main", "--work-type", "remote", "hybrid"]):
        args = parse_args()
    assert args.work_type == ["remote", "hybrid"]


# ---------------------------------------------------------------------------
# mark subcommand (Story C, ADR-025)
# ---------------------------------------------------------------------------


def test_parse_args_mark_status_and_note():
    """The mark subcommand captures job id, status, and note."""
    with patch(
        "sys.argv",
        ["main", "mark", "--job-id", "7", "--status", "applied", "--note", "referred"],
    ):
        args = parse_args()
    assert args.command == "mark"
    assert args.job_id == 7
    assert args.status == "applied"
    assert args.note == "referred"
    assert args.save is False
    assert args.unsave is False


def test_parse_args_mark_save_flag():
    """--save sets the save flag on the mark subcommand."""
    with patch("sys.argv", ["main", "mark", "--job-id", "3", "--save"]):
        args = parse_args()
    assert args.command == "mark"
    assert args.save is True
    assert args.status is None


def test_parse_args_mark_requires_job_id():
    """The mark subcommand requires --job-id."""
    with patch("sys.argv", ["main", "mark", "--status", "applied"]):
        with pytest.raises(SystemExit):
            parse_args()


def test_parse_args_mark_rejects_machine_status():
    """Machine-set statuses are not valid --status choices."""
    with patch("sys.argv", ["main", "mark", "--job-id", "1", "--status", "evaluated"]):
        with pytest.raises(SystemExit):
            parse_args()


def test_parse_args_mark_save_and_unsave_mutually_exclusive():
    """--save and --unsave cannot be combined."""
    with patch("sys.argv", ["main", "mark", "--job-id", "1", "--save", "--unsave"]):
        with pytest.raises(SystemExit):
            parse_args()
