"""HTTP routes for the workspace module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import storage_dep
from app.core.storage import StorageBackend
from app.modules.workspace.service import InvalidTransition, WorkspaceService
from app.schemas.common import WorkspaceStatus
from app.schemas.job import JobPosting

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _service(storage: StorageBackend = Depends(storage_dep)) -> WorkspaceService:
    return WorkspaceService(storage=storage)


class TransitionRequest(BaseModel):
    status: WorkspaceStatus
    note: str | None = None


@router.get("/board", response_model=dict[str, list[JobPosting]])
def get_board(service: WorkspaceService = Depends(_service)) -> dict[str, list[JobPosting]]:
    return service.board()


@router.get("", response_model=list[JobPosting])
def list_jobs(
    status: WorkspaceStatus | None = None, service: WorkspaceService = Depends(_service)
) -> list[JobPosting]:
    return service.list_by_status(status)


@router.post("/{job_id}/transition", response_model=JobPosting)
def transition(
    job_id: str, payload: TransitionRequest, service: WorkspaceService = Depends(_service)
) -> JobPosting:
    try:
        return service.transition(job_id, payload.status, note=payload.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
