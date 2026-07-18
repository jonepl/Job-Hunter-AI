"""FastAPI driving adapter for the Job Hunter AI Agent.

A second way into the same core services as the CLI (ADR-026): it serves the
React SPA and a JSON API over the shared ``JobRepositoryPort``, reimplementing no
business logic. Build the app with :func:`src.api.main.create_app`; the module
attribute ``src.api.main:app`` is the uvicorn entrypoint.
"""
