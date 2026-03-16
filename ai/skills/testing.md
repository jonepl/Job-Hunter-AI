# Skill: Testing

## Goal
Write and maintain tests for all project components.

## Steps
1. Identify the function or module to test
2. Create `tests/test_<module>.py` if it does not exist
3. Import the function under test
4. Write a test for the happy path — expected inputs produce expected output
5. Write a test for at least one failure case:
   - Empty input
   - Missing required field
   - API timeout or HTTP error
6. Use `pytest.fixture` for shared setup (e.g. sample resume text, mock JD)
7. Use `unittest.mock.patch` to mock external API calls — never call real APIs in tests
8. Run: `pytest tests/ -v`
9. All tests must pass before the skill is considered complete

## Naming Conventions
- Test files: `test_<module>.py`
- Test functions: `test_<function>_<scenario>()`
- Example: `test_parse_resume_empty_pdf()`