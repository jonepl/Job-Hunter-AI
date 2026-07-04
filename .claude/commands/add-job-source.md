Add a new job platform scraper.

Argument: `[platform]`

Follow `.claude/skills/add-job-source/SKILL.md`. In short: implement a new
adapter under `src/adapters/scrapers/` that subclasses `ScraperPort` and returns
`list[Job]`, register it in `scraper_factory.build_scrapers()` and the
`ScraperName` enum, and add a unit test under
`tests/unit/adapters/scrapers/`.

Note: Indeed, Glassdoor, and ZipRecruiter are already served by the single
`JSearchScraper` (JSearch API) — do not add direct scrapers for them.
