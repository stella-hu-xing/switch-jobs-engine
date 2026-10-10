Produce an interview briefing for this candidate and role, combining the job
description, the company profile (culture/values/process) and the candidate's
own story and Q&A banks.

RULES
- Draft answers must only use the candidate's real stories. No invented projects.
- Mark preparation gaps where the JD demands something the profile lacks.
- Prefer questions that this specific company/process is known to ask when the
  company profile mentions its interview process.

Return a single JSON object:
{
  "company_snapshot": string,
  "culture_notes": [string],
  "tech_focus": [string],
  "likely_questions": [{"question": string,
      "category": "behavioural|technical|system_design|culture|motivation",
      "why_likely": string, "suggested_story_ids": [string],
      "draft_answer": string}],
  "questions_to_ask": [string],
  "preparation_gaps": [string]
}

Role: $title at $company

Job description:
---
$description
---

Company profile:
---
$company_profile
---

Candidate stories and Q&A bank:
---
$profile_extract
---
