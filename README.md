# switch-jobs-engine

An AI-assisted job-switch workflow: self preparation, job sourcing, company
research, matching, a review workspace, application tailoring, and interview
prep — with an explicit **human approval gate** before anything is ever
submitted. No auto-apply, no LinkedIn scraping, no fabricated resume content.

```
Self Preparation -> Job Hunting (ingest/dedup) -> Match & rank
  -> Workspace (review/save/reject/pursue) -> Application prep
  -> USER APPROVAL GATE -> submission/handoff -> Interview prep -> debrief
```

See `docs/architecture.md` for the full design and `AGENTS.md` for repo
conventions / rules an AI coding agent should follow.

## Stack

FastAPI + Pydantic v2 · OpenRouter (OpenAI-compatible) LLM access ·
pluggable `StorageBackend` (local JSON by default, GCS for Cloud Run) ·
OpenTelemetry (+ optional Langfuse) · Greenhouse/Lever public APIs +
user-provided URLs/paste for sourcing.

## Quickstart

```bash
make install          # creates .venv, installs requirements.txt
cp .env.example .env  # optional: set OPENROUTER_API_KEY for real LLM output
make dev              # uvicorn app.main:app --reload on :8000
```

Open http://127.0.0.1:8000/docs for the interactive API, or
http://127.0.0.1:8000/health for a liveness check.

No `OPENROUTER_API_KEY`? The app still runs end-to-end — every LLM-backed
service returns a deterministic, schema-valid offline stub, so you can
exercise the full flow (create profile → ingest job → rank → draft
application → approve → submit) without spending any tokens.

## Example flow (curl)

```bash
# 1. Self preparation
curl -X POST localhost:8000/profiles -H 'Content-Type: application/json' \
  -d '{"raw_text": "<paste resume / LinkedIn export / free text>"}'

# 2. Ingest a job (pick one)
curl -X POST localhost:8000/jobs/ingest/greenhouse -d '{"query": "<board token>"}'
curl -X POST localhost:8000/jobs/ingest/lever -d '{"query": "<site slug>"}'
curl -X POST localhost:8000/jobs/ingest/paste -d '{"text": "<pasted JD>"}'

# 3. Rank jobs against the profile
curl -X POST localhost:8000/match/rank -d '{"profile_id": "<id>"}'

# 4. Move a job through the workspace
curl -X POST localhost:8000/workspace/<job_id>/transition -d '{"status": "pursuing"}'

# 5. Draft a tailored application, then approve before it can be marked submitted
curl -X POST localhost:8000/applications/draft -d '{"profile_id": "<id>", "job_id": "<id>"}'
curl -X POST localhost:8000/applications/<app_id>/approve -d '{}'
curl -X POST localhost:8000/applications/<app_id>/submit -d '{}'

# 6. Interview prep
curl -X POST localhost:8000/interview/brief -d '{"profile_id": "<id>", "company_id": "<id>"}'
```

## Testing

```bash
make test
```

## Config

All settings live in `.env` (see `.env.example`): LLM model selection,
`STORAGE_BACKEND` (`local` | `gcs`), telemetry toggles, HTTP user agent for
connectors.

## Boundaries by design

- **No auto-apply**: an application can only move to `submitted` after an
  explicit `/approve` call.
- **No fabrication**: tailored resume/cover-letter/answer content is grounded
  in the candidate's own achievement/story/Q&A bank; anything the LLM can't
  ground is flagged, not silently inserted.
- **No LinkedIn scraping**: LinkedIn content only enters the system via a
  user-pasted URL or text; sourcing otherwise uses public Greenhouse/Lever APIs.

## Future Steps

### 1. Productionize

- **Authentication & authorization**: Add proper auth (OAuth/OIDC) for user identity management.
- **Testing infrastructure**: Add unit tests per module, integration tests for the full pipeline, and test-coverage reporting in CI (currently a known gap).
- **Rate limiting & abuse protection**: Implement request throttling, API key management, and usage quotas.
- **Database migration**: Move from JSON/GCS storage to a proper database (PostgreSQL/Firestore) with migrations, connection pooling, and backups.
- **CI/CD hardening**: Add linting, security scanning, and staging environment deployment.
- **Error handling & retries**: Comprehensive error handling, circuit breakers, dead-letter queues for async tasks.
- **Secrets management**: Integrate with GCP Secret Manager or Vault for runtime secret rotation.
- **Health checks & readiness probes**: Extend `/health` with dependency checks (GCS, LLM API, database).
- **Graceful degradation**: Offline mode fallbacks, cached responses when dependencies are unavailable.

### 2. Set Evaluation Benchmark

- **Golden dataset**: Curate a labeled dataset of (profile, job) pairs with ground-truth match scores for regression testing.
- **Automated eval pipeline**: CI job that runs the matching/scoring pipeline against the golden dataset and tracks metrics over time.
- **Key metrics**:
  - Ranking quality: NDCG@k, MAP, Recall@k for job recommendations
  - Application prep quality: groundedness rate, hallucination rate, human eval score
  - Latency: p50/p95/p99 for each pipeline stage
  - Cost: tokens per workflow run, cost per successful application
- **A/B testing framework**: Infrastructure to compare prompt versions, model tiers, and scoring weights.
- **Regression alerts**: Alert when evaluation metrics drop below thresholds.

### 3. Add Observability

- **Structured logging**: JSON logs with trace IDs, correlation IDs, structured fields for querying.
- **Distributed tracing**: Full OpenTelemetry integration across FastAPI, LLM calls, storage ops, and background jobs.
- **Metrics dashboard**: Simple monitoring dashboard for:
  - Request volume, latency, error rates by endpoint
  - LLM token usage, cost, latency by model tier
  - Storage operations (reads/writes, latency, errors)
  - Pipeline stage throughput and bottlenecks
- **Alerting**: Basic alerts for error rate spikes and pipeline failures (optional).
- **Audit logging**: Immutable audit trail for approval gate and submissions.
- **Langfuse integration**: Enable by default for LLM trace inspection, prompt versioning, and evaluation.
