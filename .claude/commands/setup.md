Set up the project environment for the first time.

Environment setup is deterministic — do **not** perform the steps by hand.
Instruct the user to run:

```bash
chmod +x setup.sh && ./setup.sh
```

Then read `.claude/skills/environment-setup/SKILL.md` for project context, and
remind the user to activate the virtualenv (`source .venv/bin/activate`) and to
fill real credentials into `.env` (see `docs/env.md`).
