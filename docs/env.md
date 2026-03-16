# Environment Variables

All variables are stored in `.env` and loaded via `python-dotenv`.
Copy `.env.example` to `.env` and replace placeholder values with real keys.

| Variable | Required | Description | Where to Get It |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | GPT-4o LLM access | platform.openai.com |
| `ANTHROPIC_API_KEY` | Yes | Claude Code authentication | console.anthropic.com |
| `JSEARCH_API_KEY` | Optional | Job listings fallback API | rapidapi.com/JSearch |
```

---

## The Complete Agent Control System
```
ai/
├── rules.md                    ← Read first. Always.
├── commands.md                 ← Task shortcuts for Claude Code
└── skills/
    ├── environment-setup.md    ← Project context & structure reference
    ├── feature-development.md  ← How to build new features
    ├── debugging.md            ← How to trace and fix bugs
    ├── testing.md              ← How to write and run tests
    ├── add-job-source.md       ← How to add a new job platform
    └── resume-evaluation.md    ← How to evaluate JD vs resume

docs/
└── env.md                      ← Environment variable reference