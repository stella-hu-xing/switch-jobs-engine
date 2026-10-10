"""HTTP routes for the interview_prep module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import llm_dep, storage_dep
from app.core.llm_client import LLMClient
from app.core.storage import StorageBackend
from app.modules.company_research.service import CompanyResearchService
from app.modules.ingestion.service import IngestionService
from app.modules.interview_prep.service import InterviewPrepService
from app.modules.profile.service import ProfileService
from app.schemas.interview import InterviewBrief, InterviewDebrief, MockSession

router = APIRouter(prefix="/interview", tags=["interview_prep"])


def _service(
    storage: StorageBackend = Depends(storage_dep), llm: LLMClient = Depends(llm_dep)
) -> InterviewPrepService:
    return InterviewPrepService(storage=storage, llm=llm)


class BriefRequest(BaseModel):
    profile_id: str
    company_id: str
    job_id: str | None = None


class StartMockRequest(BaseModel):
    brief_id: str
    profile_id: str


class AnswerRequest(BaseModel):
    answer: str


class DebriefRequest(BaseModel):
    profile_id: str
    company: str
    job_id: str | None = None
    round_name: str | None = None
    questions_asked: list[str] = Field(default_factory=list)
    what_went_well: str | None = None
    what_to_improve: str | None = None
    interviewer_signals: str | None = None
    outcome: str | None = None


@router.post("/brief", response_model=InterviewBrief)
def build_brief(
    payload: BriefRequest,
    storage: StorageBackend = Depends(storage_dep),
    llm: LLMClient = Depends(llm_dep),
) -> InterviewBrief:
    profile = ProfileService(storage=storage, llm=llm).get(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    company = CompanyResearchService(storage=storage, llm=llm).get(payload.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    job = None
    if payload.job_id:
        job = IngestionService(storage=storage, llm=llm).get_job(payload.job_id)
    return InterviewPrepService(storage=storage, llm=llm).build_brief(
        profile=profile, job=job, company=company
    )


@router.get("/brief/{brief_id}", response_model=InterviewBrief)
def get_brief(brief_id: str, service: InterviewPrepService = Depends(_service)) -> InterviewBrief:
    brief = service.get_brief(brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="brief not found")
    return brief


@router.post("/mock/start", response_model=MockSession)
def start_mock(
    payload: StartMockRequest,
    storage: StorageBackend = Depends(storage_dep),
    llm: LLMClient = Depends(llm_dep),
) -> MockSession:
    service = InterviewPrepService(storage=storage, llm=llm)
    brief = service.get_brief(payload.brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="brief not found")
    profile = ProfileService(storage=storage, llm=llm).get(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return service.start_mock_session(brief, profile)


@router.post("/mock/{session_id}/answer", response_model=MockSession)
def answer_mock(
    session_id: str,
    payload: AnswerRequest,
    storage: StorageBackend = Depends(storage_dep),
    llm: LLMClient = Depends(llm_dep),
) -> MockSession:
    service = InterviewPrepService(storage=storage, llm=llm)
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="mock session not found")
    brief = service.get_brief(session.brief_id)
    profile = ProfileService(storage=storage, llm=llm).get(session.profile_id)
    if brief is None or profile is None:
        raise HTTPException(status_code=404, detail="brief or profile missing for session")
    return service.submit_answer(session, brief, profile, answer=payload.answer)


@router.post("/debrief", response_model=InterviewDebrief)
def capture_debrief(
    payload: DebriefRequest,
    storage: StorageBackend = Depends(storage_dep),
    llm: LLMClient = Depends(llm_dep),
) -> InterviewDebrief:
    profile = ProfileService(storage=storage, llm=llm).get(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    debrief, _updated_profile = InterviewPrepService(storage=storage, llm=llm).capture_debrief(
        profile=profile,
        company=payload.company,
        job_id=payload.job_id,
        round_name=payload.round_name,
        questions_asked=payload.questions_asked,
        what_went_well=payload.what_went_well,
        what_to_improve=payload.what_to_improve,
        interviewer_signals=payload.interviewer_signals,
        outcome=payload.outcome,
    )
    return debrief
