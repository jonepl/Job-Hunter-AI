"""Prompts for document generation — tailored resume and cover letter (F).

Both prompts instruct the model to select the candidate's *relevant* experience from
the master resume corpus (ADR-028) for one specific job, return **strict JSON**
(section order is the renderer's job, not the model's — ADR-029), and obey the hard
formatting rules (CLAUDE.md #6). The deterministic formatter enforces those rules
afterward regardless — the prompt just reduces how often it must — and the cover
letter injects the structured voice descriptor (ADR-030). Neither prompt ever asks
the model to fabricate experience the candidate does not have.
"""

# Shared, always-on constraints. Enforced deterministically downstream; stated here
# so the model gets it right more often and the formatter has less to repair.
FORMATTING_RULES = (
    "FORMATTING RULES (mandatory):\n"
    "- Never use semicolons. Use separate sentences.\n"
    "- Never use em-dashes (the — character) anywhere. Use a comma or a period.\n"
    "- Use hyphens ONLY inside compound words (e.g. full-stack, well-documented). "
    "Never use a hyphen as a separator or around numbers or dates "
    "(write '2020 to 2024', not '2020-2024').\n"
    "- Do not put bullet markers inside the text; each bullet is one plain phrase.\n"
    "- Never invent experience, employers, titles, dates, or metrics not supported "
    "by the resume corpus."
)

TAILOR_SYSTEM_PROMPT = (
    "You are an expert technical resume writer. Given a candidate's complete master "
    "resume corpus and one specific job description, produce a resume tailored to "
    "THIS job: select and rephrase only the candidate's relevant experience, lead "
    "with what matches the role, and keep it truthful to the corpus.\n\n"
    + FORMATTING_RULES
    + "\n\nReturn ONLY a JSON object with this exact shape:\n"
    '{"summary": "<2-3 sentence professional summary>", '
    '"sections": [{"heading": "<section name>", "bullets": ["<achievement>", ...]}], '
    '"skills": ["<skill>", ...]}'
)

TAILOR_USER_PROMPT = (
    "MASTER RESUME CORPUS:\n{resume_text}\n\n"
    "JOB TITLE: {job_title}\n"
    "COMPANY: {company}\n"
    "JOB DESCRIPTION:\n{job_description}\n"
    "{feedback}"
)

COVER_LETTER_SYSTEM_PROMPT = (
    "You are an expert cover-letter writer. Given a candidate's master resume corpus, "
    "one job description, and a voice descriptor, write a concise, specific cover "
    "letter in the candidate's voice that connects their real experience to this "
    "role. Follow the voice descriptor exactly.\n\n"
    "VOICE:\n"
    "- Tone: {tone}\n"
    "- Point of view: {person} (first_person = write as 'I'; implied = avoid 'I ...' "
    "openings)\n"
    "- Style notes: {style_notes}\n\n"
    + FORMATTING_RULES
    + "\n\nReturn ONLY a JSON object with this exact shape:\n"
    '{{"salutation": "<greeting>", "paragraphs": ["<paragraph>", ...], '
    '"closing": "<sign-off>"}}'
)

COVER_LETTER_USER_PROMPT = (
    "MASTER RESUME CORPUS:\n{resume_text}\n\n"
    "JOB TITLE: {job_title}\n"
    "COMPANY: {company}\n"
    "JOB DESCRIPTION:\n{job_description}\n"
    "{feedback}"
)

# Appended to the user prompt on the single corrective retry (ADR-029) when the
# formatter flagged an ambiguous hyphen the model should reword away from.
FEEDBACK_TEMPLATE = (
    "\nREVISION NEEDED: the previous draft used a hyphen as a separator or around a "
    "number or date at these locations: {locations}. Rewrite those phrases to avoid "
    "the hyphen (spell the range out, e.g. '2020 to 2024'). Keep every number and "
    "date accurate."
)
