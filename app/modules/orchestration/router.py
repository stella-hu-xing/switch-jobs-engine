"""HTTP routes for the orchestration module (sequential pipeline runs)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import llm_dep, storage_dep
from app.core.llm_client import LLMClient
from app.core.storage import StorageBackend
from app.modules.ingestion.connectors.greenhouse import GreenhouseConnector
from app.modules.ingestion.connectors.lever import LeverConnector
from app.modules.orchestration.pipeline import (
    draft_application_for_top_match,
    run_sourcing_and_matching,
)
from app.schemas.application import Application

router = APIRouter(prefix="/orchestration", tags=["orchestration"])

CONNECTORS = {"greenhouse": GreenhouseConnector, "lever": LeverConnector}


class SourceAndMatchRequest(BaseModel):
    profile_id: str
    source: str  # "greenhouse" | "lever"
    query: str  # company board token / site slug
    top_n: int | None = 20


class DraftRequest(BaseModel):
    profile_id: str
    job_id: str
    company_id: str | None = None


@router.post("/source-and-match")
def source_and_match(
    payload: SourceAndMatchRequest,
    storage: StorageBackend = Depends(storage_dep),
    llm: LLMClient = Depends(llm_dep),
) -> dict:
    connector_cls = CONNECTORS.get(payload.source)
    if connector_cls is None:
        raise HTTPException(
            status_code=400, detail=f"unknown source '{payload.source}', expected one of {list(CONNECTORS)}"
        )
    try:
        run = run_sourcing_and_matching(
            storage,
            llm,
            profile_id=payload.profile_id,
            connector=connector_cls(),
            connector_query=payload.query,
            top_n=payload.top_n,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return run.to_dict()


@router.post("/draft-application", response_model=Application)
def draft_application(
    payload: DraftRequest,
    storage: StorageBackend = Depends(storage_dep),
    llm: LLMClient = Depends(llm_dep),
) -> Application:
    """Drafts a tailored application package. Still requires the explicit
    approval-gate call (POST /applications/{id}/approve) before submission."""
    try:
        return draft_application_for_top_match(
            storage,
            llm,
            profile_id=payload.profile_id,
            job_id=payload.job_id,
            company_id=payload.company_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
