Write a concise, specific cover letter (250-350 words) for this role.

RULES
- Ground every claim in the achievement bank below. No invented experience.
- Reference the company's actual culture/tech points supplied, if any.
- No generic filler ("I am passionate about synergy"), no flattery padding.
- First person, plain professional tone, no em dashes.

Return a single JSON object: {"cover_letter": string, "claims_used": [string]}

Role: $title at $company
Job description (excerpt):
---
$description
---

Company culture / tech notes (may be empty):
---
$company_notes
---

Achievement bank:
---
$achievements
---
