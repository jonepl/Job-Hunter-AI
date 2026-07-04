Trigger a manual agent run.

Arguments: `[query] [work-type] [location?]`

- Locally: `python -m src.main --query "<query>" --work-type <remote|hybrid|onsite> [--location "<location>"]`
- In Docker: `docker compose run agent`

Remember the location rules (see `.claude/rules/scraping.md`): `--location` is
optional only when `--work-type remote` is the sole work type (defaults to
"United States"); it is required for hybrid, onsite, and mixed work types.
Results are emailed and written to `output/results_<timestamp>.csv`.
