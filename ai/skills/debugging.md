# Skill: Debugging

## Goal
Identify and resolve a bug or failure in the project.

## Steps
1. Reproduce the failure — run the code and capture the exact error
2. Identify the file, function, and line number where the error originates
3. Read the full stack trace before forming any hypothesis
4. Trace the code path that leads to the failure
5. Form a hypothesis about the root cause
6. Implement the smallest possible fix — do not refactor while debugging
7. Run the relevant test: `pytest tests/test_<module>.py -v`
8. Run the full suite: `pytest tests/ -v`
9. Confirm no regressions were introduced
10. Commit with message: `fix: <short description>`