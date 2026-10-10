Answer the employer's application questions on behalf of the candidate.

RULES
- Use only the candidate's real profile: achievements, STAR stories, Q&A bank.
- Keep each answer under 180 words unless the question asks for more.
- Cite which story ids informed each answer.
- If the profile genuinely lacks the information (e.g. visa status, salary
  expectation not provided), answer with "NEEDS_USER_INPUT: <what is missing>".

Return a single JSON object:
{"answers": [{"question": string, "answer": string, "source_story_ids": [string]}]}

Role: $title at $company

Questions:
---
$questions
---

Candidate profile extract:
---
$profile_extract
---
