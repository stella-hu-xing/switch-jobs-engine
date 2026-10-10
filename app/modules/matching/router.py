"""HTTP routes for the matching module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import llm_dep, storage_dep
from app.core.llm_client import LLMClient
from app.core.storage import StorageBackend
from app.modules.company_research.service import CompanyResearchService
from app.modules.ingestion.service import IngestionService
from app.modules.matching.service import MatchingService
from app.modules.profile.service import ProfileService
from app.schemas.match import MatchResult

router = APIRouter(prefix="/match", tags=["matching"])


class RankRequest(BaseModel):
    profile_id: str
    job_ids: list[str] | None = None  # None => rank all stored jobs
    top_n: int | None = None


@router.post("/rank", response_model=list[MatchResult])
def rank_jobs(
    payload: RankRequest,
    storage: StorageBackend = Depends(storage_dep),
    llm: LLMClient = Depends(llm_dep),
) -> list[MatchResult]:
    profile_service = ProfileService(storage=storage, llm=llm)
    ingestion_service = IngestionService(storage=storage, llm=llm)
    company_service = CompanyResearchService(storage=storage, llm=llm)
    matching_service = MatchingService(storage=storage, llm=llm)

    profile = profile_service.get(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")

    all_jobs = ingestion_service.list_jobs()
    if payload.job_ids:
        jobs = [j for j in all_jobs if j.id in set(payload.job_ids)]
    else:
        jobs = all_jobs

    company_profiles = {c.name: c for c in company_service.list()}
    return matching_service.rank_jobs(
        profile, jobs, company_profiles=company_profiles, top_n=payload.top_n
    )


@router.get("", response_model=list[MatchResult])
def list_matches(
    profile_id: str | None = None,
    storage: StorageBackend = Depends(storage_dep),
    llm: LLMClient = Depends(llm_dep),
) -> list[MatchResult]:
    return MatchingService(storage=storage, llm=llm).list_matches(profile_id)
