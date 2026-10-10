# AGENTS.md — context for AI coding agents working on switch-jobs-engine

This file orients an AI agent (Cline, Copilot, etc.) picking up work in this
repo. Read `docs/architecture.md` for the full design; this file is the quick
reference + conventions.

## What this project is

A personal job-switch assistant that automates the *preparation* work around
a job search while keeping a human in control of every outbound action. It
follows the workflow in `init.md`:

```
Self Preparation -> Job Hunting (ingest/dedup) -> Match & rank
  -> Workspace (review/save/reject/pursue) -> Application prep
  -> USER APPROVAL GATE -> submission/handoff -> Interview prep -> debrief
```

There is **no auto-apply**. The approval gate in `application_prep` is a hard
rule, not a suggestion — see "Non-negotiable rules" below.

## Repo layout

```
app/
  main.py                FastAPI app, includes all module routers, /health
  core/                   cross-cutting infra, no business logic
    settings.py           pydantic-settings, reads .env (see .env.example)
    storage.py            StorageBackend protocol + LocalJSONStorage/GCSStorage/InMemoryStorage
    llm_client.py          OpenRouter (OpenAI-compatible) wrapper, offline-safe
    telemetry.py           OpenTelemetry (+ optional Langfuse), best-effort/no-op if disabled
    ids.py                 id/hash/text-similarity helpers (dedup, scoring)
  schemas/                Pydantic v2 models, one file per domain concept
  prompts/                prompt template registry; templates/*.md, render("name", **vars)
  api/deps.py             shared FastAPI Depends() providers (storage, llm)
  modules/<name>/         one package per workflow stage:
    profile/              Self Preparation -> CandidateProfile
    ingestion/            connectors/ (greenhouse, lever, manual_url) + normalize/dedup
    company_research/     culture/vision/tech-stack summarization + match score
    matching/              deterministic scoring (scoring.py) + LLM rationale (service.py)
    workspace/              job status state machine
    application_prep/      tailored resume/cover letter/answers + APPROVAL GATE
    interview_prep/        briefing, mock interview loop, debrief capture
    orchestration/          plain sequential pipeline wiring the above together
tests/                    pytest, mock storage (InMemoryStorage) + mock/offline LLM
docs/architecture.md      full design doc (read this for "why")
infra/terraform/          Terraform IaC for GCP deployment (Cloud Run, GCS, IAM, secrets)
  README.md               deployment workflow and runbook
  *.tf                    resource definitions
  terraform.tfvars        (gitignored) local variable values
data/                     LocalJSONStorage default root (gitignored — may contain real resume data)
```

Each module follows the same shape: `service.py` (pure business logic, takes
`storage`/`llm` as constructor args) + `router.py` (FastAPI routes, thin, no
business logic) + schemas live in `app/schemas/`, not inside the module.

## Non-negotiable rules

1. **No auto-apply / no auto-submit.** `ApplicationPrepService.mark_submitted`
   raises `PermissionError` unless `approve()` was already called. Never
   remove or bypass this check. Never add code that calls a real
   application-submission API automatically.
2. **No fabrication in candidate-facing content.** Resume bullets, cover
   letters and application answers must be grounded in the candidate's own
   `CandidateProfile.achievements` / `story_bank` / `qa_bank`. Prompts under
   `app/prompts/templates/` already encode this; preserve those rules when
   editing prompts. `TailoredBullet.grounded`/`grounding_note` exist to flag
   anything that can't be traced to a real achievement id — don't remove that
   check in `application_prep/service.py::_check_grounding`.
3. **No automated LinkedIn scraping.** The only LinkedIn path is
   `ingestion/connectors/manual_url.py`, which requires the user to paste a
   URL or raw text themselves. Do not add a connector that logs into or
   crawls LinkedIn.
4. **LLM calls always go through `app/core/llm_client.py`.** Don't call
   `openai`/`httpx` directly from a module service. Use
   `LLMClient.complete_json(..., fallback=<schema-shaped dict>)` so the
   offline/dev path (`OPENROUTER_API_KEY` unset) returns something the
   Pydantic schema can still parse. Every call site must supply a fallback
   shaped like the expected JSON — relying on the generic offline stub will
   break schema validation.
5. **Storage access always goes through `StorageBackend`** (`app/core/storage.py`),
   never direct file/GCS calls from a module. This keeps the Firestore/Postgres
   migration path open.

## Conventions

- Python 3.11+, Pydantic v2 (`model_dump(mode="json")` when persisting).
- All schemas inherit `SJEModel` (`app/schemas/common.py`) — tolerant of extra
  fields, enums serialize by value.
- IDs: `new_id("prefix")` from `app/core/ids.py` (e.g. `profile_xxxx`, `job_xxxx`).
- Timestamps: `now_utc()` from `app/core/ids.py`, always timezone-aware UTC.
- Prompt templates use `$variable` placeholders (`string.Template.safe_substitute`,
  not f-strings/Jinja) — see `app/prompts/__init__.py::render`.
- Model tiering: `ModelTier.FAST` for parsing/normalization/dedup-adjacent
  tasks, `ModelTier.SMART` for tailoring/company research/interview prep.
- New module checklist: add `schemas/<x>.py` if new data shapes are needed,
  `modules/<name>/service.py` + `router.py`, register the router in
  `app/main.py`, add a prompt template if it calls the LLM, add storage
  collection name to `Collections` in `app/core/storage.py`.

## Running & testing

```
make install   # creates .venv, installs requirements.txt
make dev       # uvicorn app.main:app --reload  (port 8000)
make test      # pytest
```

Runs fine with no `OPENROUTER_API_KEY` set (`.env.example` default) — every
LLM-backed service has a deterministic offline fallback, so the full HTTP
flow (profile -> ingest -> match -> draft -> approve -> submit) is exercisable
without spending any tokens. Set `OPENROUTER_API_KEY` to get real model output.

## Known gaps / next steps (intentionally left as TODOs)

- `tests/` currently has no pytest coverage yet; add tests per module (mock
  `LLMClient`/`StorageBackend` via `InMemoryStorage`) before relying on this
  in CI.
- No auth/multi-tenant support — this is a single-user personal tool today.
- GCS backend (`GCSStorage`) is implemented but untested against a real bucket.
  Terraform in `infra/terraform/` provisions the bucket and IAM bindings, so
  running `make deploy` exercises this path end-to-end.
- No Firestore/Postgres backend yet (deferred per the "not decided yet" note
  in `init.md`); the `StorageBackend` protocol exists specifically to make
  that swap non-invasive later.
- The background Cloud Run Job (`python -m app.worker`) is scaffolded in
  `infra/terraform/cloud_run_job.tf` but gated behind `var.enable_worker_job`
  (default `false`) because `app/worker.py` is not yet implemented.
