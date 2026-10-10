"""HTTP routes for the ingestion module (Job Hunting sourcing)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import llm_dep, storage_dep
from app.core.llm_client import LLMClient
from app.core.settings import get_settings
from app.core.storage import StorageBackend
from app.modules.ingestion.connectors.greenhouse import GreenhouseConnector
from app.modules.ingestion.connectors.lever import LeverConnector
from app.modules.ingestion.connectors.manual_url import ManualUrlConnector, from_pasted_text
from app.modules.ingestion.service import IngestionService
from app.schemas.job import IngestionReport, JobPosting

router = APIRouter(prefix="/jobs", tags=["ingestion"])


def _service(
    storage: StorageBackend = Depends(storage_dep), llm: LLMClient = Depends(llm_dep)
) -> IngestionService:
    return IngestionService(storage=storage, llm=llm)


class SourceQueryRequest(BaseModel):
    query: str  # greenhouse/lever: company board slug. manual_url: a URL.


class PasteTextRequest(BaseModel):
    text: str
    title: str | None = None
    company: str | None = None


@router.post("/ingest/greenhouse", response_model=IngestionReport)
def ingest_greenhouse(
    payload: SourceQueryRequest, service: IngestionService = Depends(_service)
) -> IngestionReport:
    settings = get_settings()
    connector = GreenhouseConnector(user_agent=settings.http_user_agent)
    return service.run_connector(connector, payload.query)


@router.post("/ingest/lever", response_model=IngestionReport)
def ingest_lever(
    payload: SourceQueryRequest, service: IngestionService = Depends(_service)
) -> IngestionReport:
    settings = get_settings()
    connector = LeverConnector(user_agent=settings.http_user_agent)
    return service.run_connector(connector, payload.query)


@router.post("/ingest/url", response_model=IngestionReport)
def ingest_url(
    payload: SourceQueryRequest, service: IngestionService = Depends(_service)
) -> IngestionReport:
    """Fetch+parse a user-provided URL (also covers manually pasted LinkedIn links)."""
    settings = get_settings()
    connector = ManualUrlConnector(user_agent=settings.http_user_agent)
    return service.run_connector(connector, payload.query)


@router.post("/ingest/paste", response_model=JobPosting)
def ingest_pasted_text(
    payload: PasteTextRequest, service: IngestionService = Depends(_service)
) -> JobPosting:
    """Ingest raw JD text pasted by the user (e.g. copied from LinkedIn)."""
    raw = from_pasted_text(payload.text, title=payload.title, company=payload.company)
    job, _created = service.ingest_raw(raw, source_name="manual_text")
    if job is None:
        raise HTTPException(status_code=500, detail="failed to ingest pasted text")
    return job


@router.get("", response_model=list[JobPosting])
def list_jobs(service: IngestionService = Depends(_service)) -> list[JobPosting]:
    return service.list_jobs()


@router.get("/{job_id}", response_model=JobPosting)
def get_job(job_id: str, service: IngestionService = Depends(_service)) -> JobPosting:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
