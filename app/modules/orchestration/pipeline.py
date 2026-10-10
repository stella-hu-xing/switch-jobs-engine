"""Sequential pipeline: ingest -> match -> (human review happens in workspace)
-> draft application (stops at the approval gate, never auto-submits).

This mirrors the diagram in init.md. Each step is also independently callable
through its own module's router, so a user/UI can intervene at any point
(the workspace review/save/reject/pursue stage, and the application approval
gate) instead of running the whole pipeline unattended.
"""

from __future__ import annotations

import logging

from app.core.ids import new_id, now_utc
from app.core.llm_client import LLMClient
from app.core.storage import Collections, StorageBackend
from app.modules.application_prep.service import ApplicationPrepService
from app.modules.company_research.service import CompanyResearchService
from app.modules.ingestion.connectors.base import JobSourceConnector
from app.modules.ingestion.service import IngestionService
from app.modules.matching.service import MatchingService
from app.modules.profile.service import ProfileService
from app.modules.workspace.service import WorkspaceService

logger = logging.getLogger(__name__)


class PipelineRun:
    """In-memory/record of one orchestration run, persisted as a plain dict."""

    def __init__(self, profile_id: str) -> None:
        self.id = new_id("run")
        self.profile_id = profile_id
        self.started_at = now_utc().isoformat()
        self.steps: list[dict] = []

    def log(self, step: str, **details: object) -> None:
        self.steps.append({"step": step, "at": now_utc().isoformat(), **details})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "started_at": self.started_at,
            "steps": self.steps,
        }


def run_sourcing_and_matching(
    storage: StorageBackend,
    llm: LLMClient,
    *,
    profile_id: str,
    connector: JobSourceConnector,
    connector_query: str,
    top_n: int | None = 20,
) -> PipelineRun:
    """Stage 2 + 4 of the diagram: ingest postings, then rank against the profile.

    Stage 5 (workspace review) and beyond are deliberately left to the user /
    separate API calls - there is no auto-apply path through this function.
    """
    run = PipelineRun(profile_id)

    profile_service = ProfileService(storage=storage, llm=llm)
    ingestion_service = IngestionService(storage=storage, llm=llm)
    matching_service = MatchingService(storage=storage, llm=llm)
    company_service = CompanyResearchService(storage=storage, llm=llm)

    profile = profile_service.get(profile_id)
    if profile is None:
        raise KeyError(f"profile not found: {profile_id}")

    report = ingestion_service.run_connector(connector, connector_query)
    run.log(
        "ingestion",
        source=report.source,
        fetched=report.fetched,
        created=report.created,
        duplicates=report.duplicates,
        errors=report.errors,
    )

    new_jobs = [j for j in ingestion_service.list_jobs() if j.id in set(report.job_ids)]
    company_profiles = {c.name: c for c in company_service.list()}
    matches = matching_service.rank_jobs(
        profile, new_jobs, company_profiles=company_profiles, top_n=top_n
    )
    run.log("matching", ranked=len(matches), top_score=matches[0].score if matches else None)

    storage.put(Collections.RUNS, run.id, run.to_dict())
    return run


def draft_application_for_top_match(
    storage: StorageBackend,
    llm: LLMClient,
    *,
    profile_id: str,
    job_id: str,
    company_id: str | None = None,
):
    """Stage 6 of the diagram: generate a tailored application package.

    Returns an Application in stage AWAITING_APPROVAL -- the caller (user)
    must explicitly call ApplicationPrepService.approve(...) before anything
    can move to 'submitted'. This function performs no submission.
    """
    profile_service = ProfileService(storage=storage, llm=llm)
    ingestion_service = IngestionService(storage=storage, llm=llm)
    company_service = CompanyResearchService(storage=storage, llm=llm)
    application_service = ApplicationPrepService(storage=storage, llm=llm)
    workspace_service = WorkspaceService(storage=storage)

    profile = profile_service.get(profile_id)
    if profile is None:
        raise KeyError(f"profile not found: {profile_id}")
    job = ingestion_service.get_job(job_id)
    if job is None:
        raise KeyError(f"job not found: {job_id}")
    company = company_service.get(company_id) if company_id else None

    application = application_service.draft(profile=profile, job=job, company=company)

    from app.schemas.common import WorkspaceStatus
    from app.modules.workspace.service import ALLOWED_TRANSITIONS, InvalidTransition

    try:
        if WorkspaceStatus.PURSUING in ALLOWED_TRANSITIONS.get(job.status, set()):
            workspace_service.transition(job.id, WorkspaceStatus.PURSUING, note="application drafted")
    except InvalidTransition as exc:  # pragma: no cover - best-effort bookkeeping only
        logger.info("Skipping workspace auto-transition: %s", exc)

    return application
