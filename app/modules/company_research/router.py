"""HTTP routes for the company_research module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import llm_dep, storage_dep
from app.core.llm_client import LLMClient
from app.core.storage import StorageBackend
from app.modules.company_research.service import CompanyResearchService
from app.modules.profile.service import ProfileService
from app.schemas.company import CompanyMaterial, CompanyProfile

router = APIRouter(prefix="/companies", tags=["company_research"])


def _service(
    storage: StorageBackend = Depends(storage_dep), llm: LLMClient = Depends(llm_dep)
) -> CompanyResearchService:
    return CompanyResearchService(storage=storage, llm=llm)


def _profile_service(
    storage: StorageBackend = Depends(storage_dep), llm: LLMClient = Depends(llm_dep)
) -> ProfileService:
    return ProfileService(storage=storage, llm=llm)


class ResearchCompanyRequest(BaseModel):
    company_name: str
    materials: list[CompanyMaterial] = Field(default_factory=list)
    profile_id: str | None = Field(
        default=None, description="If given, score the match against this candidate's preferences"
    )


@router.post("", response_model=CompanyProfile)
def research_company(
    payload: ResearchCompanyRequest,
    service: CompanyResearchService = Depends(_service),
    profile_service: ProfileService = Depends(_profile_service),
) -> CompanyProfile:
    candidate_profile = None
    if payload.profile_id:
        candidate_profile = profile_service.get(payload.profile_id)
        if candidate_profile is None:
            raise HTTPException(status_code=404, detail="profile not found")
    return service.build_profile(
        company_name=payload.company_name,
        materials=payload.materials,
        candidate_profile=candidate_profile,
    )


@router.get("", response_model=list[CompanyProfile])
def list_companies(service: CompanyResearchService = Depends(_service)) -> list[CompanyProfile]:
    return service.list()


@router.get("/{company_id}", response_model=CompanyProfile)
def get_company(
    company_id: str, service: CompanyResearchService = Depends(_service)
) -> CompanyProfile:
    company = service.get(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    return company
