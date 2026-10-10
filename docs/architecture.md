# switch-jobs-engine — Architecture

## 1. Problem & scope

A personal AI assistant for a job search, covering everything *up to* but
deliberately not including unattended application submission. Source intent:
`init.md` at the repo root (the original task brief + workflow diagram).

```
Self Preparation
      |
Job Hunting (connectors -> ingest/parse/dedupe)
      |
      +-----------------+-----------------+
      |                                   |
 Job database                      Candidate profile
      |                                   |
      +-----------------+-----------------+
                         |
                 Match and rank jobs
                         |
                  Job-search workspace
            (review, save, reject, or pursue)
                         |
                Application preparation
        (tailored resume + cover letter + answers)
                         |
                   USER APPROVAL GATE
                         |
            Application submission or handoff
                         |
        Interview briefings, practice, follow-up
```

Reference projects consulted for scope/ethics framing (see `init.md`):
`ai-native-jobhunt`, `FindJobs-Agent`, `Upwork-AI-jobs-applier`.

## 2. Module map

| Module | Responsibility | Key schema(s) |
|---|---|---|
| `profile` | Self Preparation: extract achievements/STAR stories/skills/Q&A from resume/LinkedIn export/free text | `CandidateProfile` |
| `ingestion` | Pluggable connectors, normalization, dedup | `RawPosting` -> `JobPosting`, `IngestionReport` |
| `company_research` | Culture/vision/tech-stack summary + preference match score | `CompanyProfile` |
| `matching` | Deterministic scoring + LLM rationale, ranks jobs for a profile | `MatchResult` |
| `workspace` | Status state machine over `JobPosting.status` | uses `JobPosting` |
| `application_prep` | Tailored resume/cover letter/Q&A, diff preview, **approval gate** | `Application`, `ApplicationPackage` |
| `interview_prep` | Briefing, mock interview loop, post-interview debrief -> feeds back to profile | `InterviewBrief`, `MockSession`, `InterviewDebrief` |
| `orchestration` | Plain sequential pipeline calling the above; no agent framework in v0 | `PipelineRun` (ephemeral, persisted as a dict) |

Each module is a FastAPI sub-router mounted in `app/main.py`, backed by a
`*Service` class that takes a `StorageBackend` and `LLMClient` and contains
all the actual logic — the router layer is intentionally thin so the same
services are directly unit-testable and reusable from `orchestration`.

## 3. Cross-cutting infrastructure (`app/core`)

### Settings (`settings.py`)
`pydantic-settings` reading `.env` (see `.env.example`). Governs: LLM model
selection, storage backend choice, OTel/Langfuse toggles, HTTP user agent for
connectors. `Settings.llm_offline` is `True` whenever `OPENROUTER_API_KEY` is
blank — this is the switch that puts the whole app into deterministic
stub/offline mode.

### LLM access (`llm_client.py`)
Single wrapper around OpenRouter's OpenAI-compatible Chat Completions API.

- `ModelTier.FAST` (default `openai/gpt-4o-mini`) for parsing/normalization/
  dedup-adjacent extraction (profile extraction, job normalization, match
  rationale, debrief analysis).
- `ModelTier.SMART` (default `anthropic/claude-3.5-sonnet`) for generation
  tasks that need more care: company research, resume tailoring, cover
  letters, application answers, interview briefing/mock feedback.
- `complete_json(..., fallback=...)` is the primary entry point used by every
  service. When offline, it returns the caller-supplied `fallback` dict
  directly (schema-shaped), *without* ever calling the network — this is what
  makes `make dev` + manual curl testing possible with zero API spend. When
  online, it asks for `response_format=json_object` and best-effort extracts
  a JSON object from the reply (`extract_json_object`), falling back to the
  caller's fallback only if parsing truly fails.
- Every LLM-touching service function supplies a `fallback` shaped exactly
  like its expected JSON schema — this is a hard convention (see
  `AGENTS.md` rule 4).

### Storage (`storage.py`)
`StorageBackend` protocol: `put/get/list/delete/exists(collection, doc_id)`.
Three implementations:
- `LocalJSONStorage` — default, `./data/<collection>/<id>.json`.
- `GCSStorage` — same shape, `gs://<bucket>/<prefix>/<collection>/<id>.json`,
  lazy-imports `google-cloud-storage` so it's not required for local dev.
- `InMemoryStorage` — for tests.

Selected via `STORAGE_BACKEND=local|gcs` env var through `build_storage()`.
`Collections` centralizes collection name strings so modules never hardcode
them. This exists specifically so persistence can move to Firestore/Postgres
later without touching any module's business logic — only `storage.py`
changes.

### Telemetry (`telemetry.py`)
OpenTelemetry FastAPI + httpx auto-instrumentation, OTLP HTTP exporter
pointed at Grafana Alloy/Tempo (or Grafana Cloud) via
`OTEL_EXPORTER_OTLP_ENDPOINT`. Disabled by default (`OTEL_ENABLED=false`) and
fully best-effort: missing packages or an unreachable collector only log a
warning, never crash the app. Optional Langfuse client init
(`LANGFUSE_ENABLED=true`) sits alongside OTel for LLM-trace/eval inspection
specifically (not wired into every LLM call yet — see Known Gaps in
`AGENTS.md`).

### IDs/hashing (`ids.py`)
`new_id(prefix)`, `now_utc()`, and the text-similarity helpers used by dedup
and scoring: `normalize_text`, `token_set`, `jaccard`, `stable_hash`.

## 4. Module details

### 4.1 profile
`extract_profile_fields` renders `prompts/templates/profile_extract.md` (hard
anti-fabrication rules: only use text present in input, metrics null unless
stated, every achievement must carry a verbatim `source_excerpt`) and calls
the FAST tier. `build_candidate_profile` merges the extraction into a new or
`existing` `CandidateProfile`, assigning stable ids to achievements/stories/
Q&A items and merging skills by name (bumping `evidence_count` on repeats).
`ProfileService.augment_from_text` is how later inputs (a new resume version,
more notes, or interview-debrief-derived Q&A) are folded into the same
profile without clobbering history.

### 4.2 ingestion
`connectors/base.py` defines the `JobSourceConnector` Protocol:
`fetch(query) -> list[RawPosting]`. Three concrete connectors:

- `GreenhouseConnector` — `boards-api.greenhouse.io/v1/boards/<token>/jobs`,
  public, no auth. `query` = board token (company slug).
- `LeverConnector` — `api.lever.co/v0/postings/<site>`, public, no auth.
  `query` = Lever site slug.
- `ManualUrlConnector` — fetches a user-provided URL, strips HTML with
  BeautifulSoup. Tags LinkedIn URLs with `JobSource.LINKEDIN_MANUAL` so it's
  traceable, but there is **no login/search/crawl** of LinkedIn — the user
  always supplies the specific URL. `from_pasted_text()` covers the
  no-fetch-at-all case (paste raw JD text, e.g. copied out of a LinkedIn
  saved-job export).

`IngestionService.ingest_raw`: computes `dedup_key = stable_hash(company,
title, location)`, checks exact key match AND a Jaccard-similarity-based
near-duplicate check (`_is_near_duplicate`, threshold 0.85 on description
token overlap, same company+title) against every stored job before calling
the LLM to normalize (`job_normalize.md` prompt, FAST tier) and persisting.
`run_connector` wraps a full fetch+ingest batch into an `IngestionReport`
(fetched/created/duplicates/errors/job_ids).

### 4.3 company_research
`research_company` renders `company_research.md` (SMART tier) — explicitly
instructs the model to attribute opinions as sentiment, not fact, and leave
fields empty rather than guess when materials don't cover them. Produces
`CompanyProfile` including a `match_score`/`match_rationale` against the
candidate's `Preferences` if a `profile_id` is supplied. All materials
(`CompanyMaterial`) are user-supplied today (website text, review text,
eng-blog excerpts pasted in) — there is no automated web crawler yet.

### 4.4 matching
Split deliberately into:
- `scoring.py` — pure, deterministic, no LLM calls, fully unit-testable.
  Weighted components: skills overlap (0.45, skill-name set intersection over
  job's `tech_stack ∪ keywords`), seniority distance (0.2, via
  `SENIORITY_RANK`), location/work-mode fit (0.2), compensation range check
  (0.15, neutral 60 if insufficient data).
- `service.py` — calls `scoring.compute_score` then asks the LLM (FAST tier,
  `match_rationale.md`) for a 2-4 sentence human-readable explanation; the
  fallback rationale is deterministically generated from the computed score
  so matching never *requires* the LLM to produce a usable `MatchResult`.

`rank_jobs` sorts by score desc, optional `top_n` cutoff; takes an optional
`company_profiles: dict[name -> CompanyProfile]` to attach
`company_match_score`.

### 4.5 workspace
Explicit state machine, `ALLOWED_TRANSITIONS: dict[WorkspaceStatus,
set[WorkspaceStatus]]`:

```
new -> reviewing | rejected
reviewing -> saved | rejected | pursuing
saved -> pursuing | rejected
rejected -> reviewing              (reconsideration allowed)
pursuing -> applied | rejected
applied -> interviewing | closed
interviewing -> offer | closed
offer -> closed
closed -> (terminal)
```

`transition()` raises `InvalidTransition` (-> HTTP 409) on an illegal move;
every change appends to `JobPosting.status_history`. `board()` groups all
jobs by status for a kanban-style UI.

### 4.6 application_prep — the approval gate
This is the most safety-critical module.

- `tailor_resume` (SMART tier, `resume_tailor.md`): the prompt's rules forbid
  adding any company/tool/metric not already in the achievement bank, forbid
  changing numbers, and require each returned bullet to echo its source
  `achievement_id`.
- `_check_grounding`: after the LLM responds, every returned
  `achievement_id` is checked against the real `profile.achievements` ids.
  Anything that doesn't match is flagged `grounded=False` with a
  `grounding_note`, and surfaces in `ApplicationPackage.fabrication_warnings`
  — this check happens in code, not just via the prompt, specifically so a
  hallucinated id can't silently slip through.
- `_build_diff` produces a word-level `difflib.ndiff` diff
  (`original` achievement text vs `tailored` bullet) so the user can review
  exactly what changed before approving.
- `write_cover_letter` / `answer_questions` similarly only consume the
  achievement bank / story+QA bank as their factual source;
  `application_answers.md` explicitly instructs the model to answer
  `"NEEDS_USER_INPUT: <what's missing>"` rather than invent facts like salary
  expectations or visa status.
- **State machine**: `ApplicationStage.DRAFT -> AWAITING_APPROVAL -> APPROVED
  -> SUBMITTED` (or `CHANGES_REQUESTED` to loop back). `draft()` always lands
  on `AWAITING_APPROVAL`. `mark_submitted()` hard-raises `PermissionError` if
  `approved_by_user` is not `True` — verified end-to-end in manual testing
  (see `AGENTS.md` for the exact curl sequence used). There is no code path
  anywhere in this repo that calls a real job-board submission API; "submit"
  only flips `stage`/`submission_mode` bookkeeping for a manual/human
  handoff.

### 4.7 interview_prep
- `build_brief` (SMART tier, `interview_brief.md`): combines job description +
  `CompanyProfile` (culture/values/interview_process/tech_stack) + the
  candidate's story/Q&A bank into `likely_questions` with `draft_answer`s
  grounded in `suggested_story_ids`, plus `preparation_gaps` where the JD
  demands something the profile doesn't cover.
- Mock interview loop: `start_mock_session` seeds the first
  `likely_questions[0]`; `submit_answer` scores the previous answer (SMART
  tier, `mock_feedback.md`: structure/specificity/relevance/ownership) and
  either advances to the next planned question or lets the model propose a
  `next_question`; finishes and computes an average score once questions run
  out.
- `capture_debrief` (FAST tier, `debrief_analyze.md`) turns a free-text
  post-interview debrief into new `QAItem`s, written back into
  `CandidateProfile.qa_bank` — this is the explicit feedback loop in the
  original diagram ("Interview briefings, practice, follow-up" feeding back
  into positioning).

### 4.8 orchestration
`run_sourcing_and_matching`: ingest via one connector + rank against a
profile in one call, logging each step into a `PipelineRun` persisted under
`Collections.RUNS`. `draft_application_for_top_match`: drafts an
`Application` for a specific job and best-effort transitions the job to
`pursuing` in the workspace (skipped silently if the transition isn't legal
from the job's current status). Neither function approves or submits
anything — those remain explicit, separate calls into `application_prep`.
No LangGraph/agent-graph dependency in v0, per the locked-in tech decision in
`plan.md`; revisit if multi-step retry/branching logic outgrows plain
function composition.

## 5. Data flow / persistence

Everything is a JSON document under a named collection (see `Collections` in
`storage.py`): `profiles`, `jobs`, `companies`, `matches`, `applications`,
`interviews` (also used for mock sessions, prefixed `mock_<id>`),
`debriefs`, `runs`. Local dev: `./data/<collection>/<id>.json` (gitignored —
may contain real resume/profile content). Cloud Run: same shape in GCS.

## 6. Deployment shape

- Request-serving: Cloud Run service running `uvicorn app.main:app` via the
  provided `Dockerfile` (honors `$PORT`).
- Long-running ingestion/enrichment: intended as a separate Cloud Run Job
  (`python -m app.worker`, not yet implemented — see Known Gaps in
  `AGENTS.md`) rather than blocking request-serving uvicorn workers.
- `Makefile` wraps local dev (`make install`, `make dev`, `make test`) and
  deploy (`make deploy` -> `gcloud run deploy --source .`).

## 7. Ethics / sourcing boundaries

Documented once, enforced in code + prompts, repeated in `AGENTS.md`:
1. Only legitimate public job-board JSON APIs (Greenhouse, Lever) are
   fetched automatically.
2. LinkedIn content only enters the system via a URL or text the user
   explicitly pastes — never scraped, logged into, or crawled.
3. No candidate-facing content (resume/cover letter/answers) may state
   anything not traceable to the candidate's own profile data.
4. No application is ever submitted without an explicit, separate
   `approve()` call from the user.
