"""HTTP routes for the profile module (Self Preparation)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import llm_dep, storage_dep
from app.core.llm_client import LLMClient
from app.core.storage import StorageBackend
from app.modules.profile.service import ProfileService
from app.schemas.profile import CandidateProfile

router = APIRouter(prefix="/profiles", tags=["profile"])


def _service(
    storage: StorageBackend = Depends(storage_dep), llm: LLMClient = Depends(llm_dep)
) -> ProfileService:
    return ProfileService(storage=storage, llm=llm)


class CreateProfileRequest(BaseModel):
    raw_text: str = Field(..., description="Resume text / LinkedIn export / free-text experience")
    source_label: str = "manual_text"
    preference_hints: str = ""


class AugmentProfileRequest(CreateProfileRequest):
    pass


@router.post("", response_model=CandidateProfile)
def create_profile(
    payload: CreateProfileRequest, service: ProfileService = Depends(_service)
) -> CandidateProfile:
    return service.create_from_text(
        raw_text=payload.raw_text,
        source_label=payload.source_label,
        preference_hints=payload.preference_hints,
    )


@router.get("", response_model=list[CandidateProfile])
def list_profiles(service: ProfileService = Depends(_service)) -> list[CandidateProfile]:
    return service.list()


@router.get("/{profile_id}", response_model=CandidateProfile)
def get_profile(profile_id: str, service: ProfileService = Depends(_service)) -> CandidateProfile:
    profile = service.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile


@router.post("/{profile_id}/augment", response_model=CandidateProfile)
def augment_profile(
    profile_id: str,
    payload: AugmentProfileRequest,
    service: ProfileService = Depends(_service),
) -> CandidateProfile:
    try:
        return service.augment_from_text(
            profile_id,
            raw_text=payload.raw_text,
            source_label=payload.source_label,
            preference_hints=payload.preference_hints,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{profile_id}")
def delete_profile(profile_id: str, service: ProfileService = Depends(_service)) -> dict:
    deleted = service.delete(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="profile not found")
    return {"deleted": True}
