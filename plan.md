1. `profile` module — Self Preparation
   - Ingest resume/LinkedIn export/free-text experience → LLM extraction of achievements, STAR stories, skills taxonomy → generates `CandidateProfile` (structured JSON: experience, skills, preferences, story bank, Q\&A bank).

2. `ingestion` module — Job Hunting sourcing
   - Pluggable **connector/adapter** interface (`JobSourceConnector`) per source: company career pages (greenhouse/lever/workday APIs where available), LinkedIn (via user-provided exported links/saved search, respecting ToS — no aggressive scraping), user-pasted JD/URL.
   - Parses raw postings into a normalized `JobPosting` schema, dedupes (hash on company+title+location+description similarity).

3. `company_research` module — culture/vision/tech-match analysis
   - Given a company name, gathers (user-supplied or fetched) company materials — website, Glassdoor/Blind-style review text if user provides it, engineering blog — LLM summarizes culture/vision/tech stack and produces a `CompanyProfile` + match score against candidate preferences.

4. `matching` module — Match and rank jobs
   - Scores `JobPosting` × `CandidateProfile` (skills overlap, seniority, location/remote, comp if present) → ranked list with rationale, stored for the workspace UI/API.

5. `workspace` module — review/save/reject/pursue state machine (statuses: `new → reviewing → saved/rejected → pursuing → applied → interviewing → offer/closed`).

6. `application_prep` module — tailoring
   - Generates tailored resume (reuses profile's achievement bank, rewrites bullets to JD keywords), cover letter, and answers to application questions — strictly grounded in the candidate's real profile (no fabrication) — and a diff/preview for the **user approval gate** before any submission/handoff.

7. `interview_prep` module — company-review-based interview briefing: likely questions (from profile's Q\&A bank + JD + company profile), STAR answer drafts, mock-interview Q\&A loop, and post-interview debrief capture to feed back into profile/positioning.

8. `orchestration` — a lightweight LangGraph/stateful pipeline (or simpler FastAPI workflow calls + a Cloud Run job for async crawling) tying stages together, with clear human-approval gates matching the diagram (no fully unattended auto-apply, consistent with ai-native-jobhunt's ethics stance and the user's own diagram which has an explicit "User approval gate").

**Tech implementation plan:**

- **Backend**: FastAPI app (`app/`) with routers per module (`profile`, `jobs`, `companies`, `match`, `applications`, `interview`). Pydantic v2 models for all schemas (`CandidateProfile`, `JobPosting`, `CompanyProfile`, `Application`).
- **LLM access**: single `llm_client` wrapper around OpenRouter (OpenAI-compatible API) with model selection per task (cheap model for parsing/dedup, stronger model for tailoring/interview prep), prompt templates under `app/prompts/`.
- **Background worker**: crawling/enrichment jobs run as Cloud Run Jobs (or a `/internal/tasks` endpoint triggered by Cloud Scheduler/Pub-Sub) separate from the request-serving Cloud Run service, since crawling is long-running.
- **Storage**: start with GCS (JSON/JSONL documents, like FindJobs-Agent's `data/*.jsonl` pattern) for postings/profiles/applications since "not decided yet" — plan a thin repository/storage interface (`StorageBackend` protocol) so it can later move to Firestore/Postgres without touching business logic.
- **Connectors**: `app/connectors/base.py` defines `JobSourceConnector.fetch(query) -> list[RawPosting]`; concrete connectors for Greenhouse/Lever JSON APIs (legit public APIs many tech cos use), a generic "user-provided URL" fetch+parse connector, and a LinkedIn connector stub that only processes user-supplied saved-job exports/links (to stay within ToS — flagged explicitly as manual/authorized-only, matching ai-native-jobhunt's "no unauthorized scraping" boundary).
- **Observability**: OpenTelemetry SDK instrumentation (FastAPI + httpx + LLM calls) exporting via OTLP to a Grafana stack (Grafana Alloy/Tempo/Loki or Grafana Cloud); optional Langfuse callback handler wired in alongside OTel for trace/eval inspection of LLM calls specifically.
- **Repo scaffolding**: `pyproject.toml` (or `requirements.txt`), `Dockerfile` for Cloud Run, `app/` package, `tests/` with pytest, `.env.example`, `docs/architecture.md` capturing this design, `Makefile`/scripts for local run (`uvicorn app.main:app --reload`) and deploy (`gcloud run deploy`).

### Open questions before implementation (act mode)

I'd like to confirm a few decisions since they materially affect scaffolding:

1. Storage backend to start with (GCS JSON files vs. Firestore vs. Cloud SQL/Postgres) — I'd lean GCS + local JSON for v0 given "not decided yet," with an abstraction layer.
2. Orchestration style — simple sequential FastAPI service calls vs. LangGraph-based agent graph (closer to Upwork-AI-jobs-applier) for multi-step reasoning/retries.
3. Scope of first implementation slice — build the full skeleton (all 8 modules with stub/real logic) vs. vertically slice just "Self Preparation" (profile builder) end-to-end first, then layer in ingestion/matching/tailoring/interview prep.
4. LinkedIn/company-posting sourcing — confirm we restrict to public job-board APIs (Greenhouse/Lever) + user-provided URLs/exports only, not actual LinkedIn scraping (which violates ToS and is explicitly called out as a boundary in the reference repo).

Since this is currently plan mode, I haven't created any files yet. Once you confirm the open questions (or tell me to just use my recommended defaults), I'll switch to

Act Mode (⌘⇧A) and scaffold the full `switch-jobs-engine` repo: FastAPI app skeleton, Pydantic schemas, connector/LLM/storage interfaces, prompt templates, Dockerfile, OTel setup, and docs — then run it locally to verify the server boots and basic endpoints respond.

Cline has a question:

Which starting scope should I implement first when we move to

Act Mode (⌘⇧A)?

Full skeleton: scaffold all 8 modules (profile, ingestion, company research, matching, workspace, tailoring, interview prep, orchestration) with working stubs end-to-endVertical slice: build only 'Self Preparation' (profile/resume/story/Q\&A builder) fully working first, stub everything elseVertical slice: build 'Job Hunting' ingestion + matching first (connectors, dedup, ranking), stub profile/tailoring/interviewUse my recommended defaults (GCS+local JSON storage, simple sequential FastAPI orchestration, Greenhouse/Lever + user-provided URLs only, full skeleton scope) and proceed

You've chosen the full skeleton scope. Since I also need decisions on storage backend, orchestration style, and sourcing scope to build this correctly, let me ask those remaining points together as one consolidated confirmation before switching to

Act Mode (⌘⇧A).

Cline has a question:

For the remaining open decisions (storage backend, orchestration style, job sourcing scope), should I go with my recommended defaults?

Yes, use all recommended defaults: GCS + local-JSON storage abstraction, simple sequential FastAPI orchestration (no LangGraph yet), connectors limited to Greenhouse/Lever public APIs + user-provided URLs/exports (no direct LinkedIn scraping)Same as above but use LangGraph for orchestration instead of plain sequential FastAPI callsSame as recommended defaults but use Firestore instead of GCS/local-JSON for structured data (profiles, jobs, applications)Let me specify different choices instead

Plan

All decisions are confirmed. Here's the finalized plan I'll execute once you switch to

Act Mode (⌘⇧A).

## Finalized Plan

**Repo:** `/Users/stellahu/Documents/projects/switch-jobs-engine` (existing, git-initialized, currently just `init.md` + stub `README.md`)

**Scope:** Full skeleton — all 8 modules scaffolded with working stubs end-to-end, wired together via a simple sequential FastAPI orchestration (no LangGraph for v0).

**Decisions locked in:**

- Storage: `StorageBackend` protocol with a `LocalJSONStorage` implementation (JSON/JSONL files under `./data/`) for dev, and a `GCSStorage` implementation using `google-cloud-storage` for Cloud Run deploys — selected via env var, so both exist but local is the default for easy testing.
- Orchestration: plain FastAPI routers calling module services in sequence; no agent-graph framework yet.
- Job sourcing: Greenhouse (`boards-api.greenhouse.io`) and Lever (`api.lever.co`) public JSON APIs as real connectors, plus a generic "user-provided URL" connector (fetch + HTML strip + LLM-structure). LinkedIn is explicitly a **manual/user-provided-link only** connector (paste a job URL or exported posting text) — no automated LinkedIn scraping, documented as a boundary.

**Build steps:**

1. **Repo scaffolding**: `pyproject.toml`, `requirements.txt`, `Dockerfile`, `.env.example`, `.gitignore`, `Makefile`, `docs/architecture.md`.
2. **`app/core`**: settings (pydantic-settings reading env: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL_*`, `STORAGE_BACKEND`, GCS bucket, OTel endpoint), `llm_client.py` (OpenRouter wrapper via OpenAI SDK-compatible client), `storage.py` (protocol + Local/GCS impls), `telemetry.py` (OpenTelemetry FastAPI/httpx instrumentation + OTLP exporter, optional Langfuse hook).
3. **`app/schemas`**: Pydantic models — `CandidateProfile`, `JobPosting`, `CompanyProfile`, `MatchResult`, `Application`, `InterviewBrief`.
4. **`app/modules/profile`**: self-prep service — extract achievements/STAR stories/Q\&A bank from raw resume/experience text via LLM; CRUD + "generate" endpoints.
5. **`app/modules/ingestion`**: `connectors/base.py` (`JobSourceConnector` protocol), `connectors/greenhouse.py`, `connectors/lever.py`, `connectors/manual_url.py` (covers LinkedIn/manual paste), normalizer + dedup (hash-based) service.
6. **`app/modules/company_research`**: LLM-based culture/vision/tech-stack summarizer from user-supplied company text/links + structured `CompanyProfile` + match-to-preferences scoring.
7. **`app/modules/matching`**: skill/seniority/location/preference scoring + ranking of `JobPosting` against `CandidateProfile`, with rationale string.
8. **`app/modules/workspace`**: status state machine (`new/saved/rejected/pursuing/applied/interviewing/closed`) + list/filter endpoints.
9. **`app/modules/application_prep`**: tailored resume bullet rewriter (grounded strictly in profile's real achievement bank — no fabrication), cover letter generator, Q\&A answer drafts, diff preview; all gated behind an explicit "approve" endpoint before marking as submitted (human-in-the-loop, no auto-submit).
10. **`app/modules/interview_prep`**: likely-question generator (JD + company profile + profile Q\&A bank), STAR answer drafts, simple mock-interview loop (LLM asks → user answers → LLM scores/feedback), post-interview debrief capture that writes back into the profile's story bank.
11. **`app/main.py`**: FastAPI app wiring all routers, health check, OTel instrumentation hook.
12. **`tests/`**: pytest unit tests per module service (mocking the LLM client and storage), plus a smoke test that boots the app and hits `/health`.
13. **Validation**: `pip install -r requirements.txt`, run `uvicorn app.main:app --reload`, curl `/health` and a couple of representative endpoints with mocked/local data to confirm the skeleton actually runs; run `pytest`.

Please toggle to **Act mode** and I'll scaffold and implement this, then run the server and test suite to verify everything works end-to-end.
