# Skill: Resume Evaluation

## Goal
Compare a candidate resume against a job description and return
a structured match score with reasoning.

## Steps
1. Load resume text from `docs/resume/resume.pdf` using `pypdf2`
2. Cache extracted text — do not re-parse on every evaluation
3. Accept a job description dict with at minimum: `title`, `description`
4. Send both resume text and job description to GPT-4o with this task:
   - Extract required skills from the job description
   - Extract skills from the resume
   - Score the match from 0 to 100
   - List matched skills
   - List missing skills
   - Provide a one sentence summary of fit

5. Return structured JSON in this exact format:
   {
     "score": 85,
     "matched_skills": ["Python", "REST APIs", "PostgreSQL"],
     "missing_skills": ["Kubernetes", "Go"],
     "summary": "Strong backend match with a gap in container orchestration.",
     "job_title": "Senior Backend Engineer",
     "company": "Acme Corp"
   }

6. Handle LLM API errors gracefully — return a default low-score result on failure
7. Write tests using mocked LLM responses — never call the real API in tests