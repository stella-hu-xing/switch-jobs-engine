"""HTTP routes for the application_prep module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import llm_dep, storage_dep
from app.core.llm_client import LLMClient
from app.core.storage import StorageBackend
from app.modules.application_prep.service import ApplicationPrepService
from app.modules.company_research.service import CompanyResearchService
from app.modules.ingestion.service import IngestionService
from app.modules.profile.service import ProfileService
from app.schemas.application import Application

router = APIRouter(prefix="/applications", tags=["application_prep"])


def _service(
    storage: StorageBackend = Depends(storage_dep), llm: LLMClient = Depends(llm_dep)
) -> ApplicationPrepService:
    return ApplicationPrepService(storage=storage, llm=llm)


class DraftRequest(BaseModel):
    profile_id: str
    job_id: str
    company_id: str | None = None
    questions: list[str] = Field(default_factory=list)


class ApproveRequest(BaseModel):
    note: str | None = None


class ChangesRequest(BaseModel):
    note: str


class SubmitRequest(BaseModel):
    submission_mode: str = "manual"


@router.post("/draft", response_model=Application)
def draft_application(
    payload: DraftRequest,
    storage: StorageBackend = Depends(storage_dep),
    llm: LLMClient = Depends(llm_dep),
) -> Application:
    profile = ProfileService(storage=storage, llm=llm).get(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    job = IngestionService(storage=storage, llm=llm).get_job(payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    company = None
    if payload.company_id:
        company = CompanyResearchService(storage=storage, llm=llm).get(payload.company_id)

    return ApplicationPrepService(storage=storage, llm=llm).draft(
        profile=profile, job=job, company=company, questions=payload.questions
    )


@router.get("", response_model=list[Application])
def list_applications(service: ApplicationPrepService = Depends(_service)) -> list[Application]:
    return service.list()


@router.get("/{application_id}", response_model=Application)
def get_application(
    application_id: str, service: ApplicationPrepService = Depends(_service)
) -> Application:
    app = service.get(application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="application not found")
    return app


@router.post("/{application_id}/approve", response_model=Application)
def approve_application(
    application_id: str, payload: ApproveRequest, service: ApplicationPrepService = Depends(_service)
) -> Application:
    try:
        return service.approve(application_id, note=payload.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{application_id}/request-changes", response_model=Application)
def request_changes(
    application_id: str, payload: ChangesRequest, service: ApplicationPrepService = Depends(_service)
) -> Application:
    try:
        return service.request_changes(application_id, note=payload.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{application_id}/submit", response_model=Application)
def submit_application(
    application_id: str, payload: SubmitRequest, service: ApplicationPrepService = Depends(_service)
) -> Application:
    """Marks the application as submitted/handed-off. Requires prior approval
    (the User Approval Gate) -- this endpoint never auto-applies anywhere."""
    try:
        return service.mark_submitted(application_id, submission_mode=payload.submission_mode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
