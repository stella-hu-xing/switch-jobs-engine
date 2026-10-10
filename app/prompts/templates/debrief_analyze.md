Analyse a post-interview debrief and turn it into reusable preparation material
that will be written back into the candidate's profile.

RULES
- Only use what the candidate reported. Do not speculate about the outcome.
- Produce Q&A entries for questions the candidate struggled with, using their
  existing stories where possible.

Return a single JSON object:
{
  "positioning_advice": string,
  "new_qa": [{"question": string, "answer": string,
              "category": "behavioural|technical|motivation|logistics|other"}],
  "follow_up_actions": [string]
}

Company: $company
Round: $round_name
Questions asked: $questions_asked
What went well: $what_went_well
What to improve: $what_to_improve
Interviewer signals: $interviewer_signals
Candidate profile extract:
---
$profile_extract
---
