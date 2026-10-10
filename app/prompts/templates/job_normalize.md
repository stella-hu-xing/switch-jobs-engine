You normalize a raw job posting into structured fields. Extract only what the
posting states; do not infer salary or tech that is not mentioned.

Return a single JSON object:
{
  "title": string,
  "company": string,
  "location": string|null,
  "work_mode": "onsite|hybrid|remote|unknown",
  "seniority": "intern|junior|mid|senior|staff|principal|manager|director|unknown",
  "requirements": [string],
  "keywords": [string],
  "tech_stack": [string],
  "salary": {"min": number|null, "max": number|null, "currency": string|null,
             "period": "year|month|day|hour"}|null
}

Known fields (may be partial):
company: $company
title: $title
location: $location
url: $url

Posting text:
---
$description
---
