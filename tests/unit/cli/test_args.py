"""Unit tests for src/cli/args.py — argument parsing."""

from unittest.mock import patch

from src.cli.args import parse_args


def test_parse_args_all_defaults_none():
    """All fields are None when no CLI arguments are provided."""
    with patch("sys.argv", ["main"]):
        args = parse_args()
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
