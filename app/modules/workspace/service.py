"""Workspace state machine: new -> reviewing -> saved/rejected -> pursuing ->
applied -> interviewing -> offer/closed.
"""

from __future__ import annotations

from app.core.ids import now_utc
from app.core.storage import Collections, StorageBackend
from app.schemas.common import WorkspaceStatus
from app.schemas.job import JobPosting

ALLOWED_TRANSITIONS: dict[WorkspaceStatus, set[WorkspaceStatus]] = {
    WorkspaceStatus.NEW: {WorkspaceStatus.REVIEWING, WorkspaceStatus.REJECTED},
    WorkspaceStatus.REVIEWING: {
        WorkspaceStatus.SAVED,
        WorkspaceStatus.REJECTED,
        WorkspaceStatus.PURSUING,
    },
    WorkspaceStatus.SAVED: {WorkspaceStatus.PURSUING, WorkspaceStatus.REJECTED},
    WorkspaceStatus.REJECTED: {WorkspaceStatus.REVIEWING},  # allow reconsideration
    WorkspaceStatus.PURSUING: {WorkspaceStatus.APPLIED, WorkspaceStatus.REJECTED},
    WorkspaceStatus.APPLIED: {WorkspaceStatus.INTERVIEWING, WorkspaceStatus.CLOSED},
    WorkspaceStatus.INTERVIEWING: {WorkspaceStatus.OFFER, WorkspaceStatus.CLOSED},
    WorkspaceStatus.OFFER: {WorkspaceStatus.CLOSED},
    WorkspaceStatus.CLOSED: set(),
}


class InvalidTransition(ValueError):
    pass


class WorkspaceService:
    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage

    def _get_job(self, job_id: str) -> JobPosting:
        doc = self.storage.get(Collections.JOBS, job_id)
        if doc is None:
            raise KeyError(f"job not found: {job_id}")
        return JobPosting(**doc)

    def transition(self, job_id: str, new_status: WorkspaceStatus, *, note: str | None = None) -> JobPosting:
        job = self._get_job(job_id)
        current = WorkspaceStatus(job.status)
        new_status = WorkspaceStatus(new_status)
        if new_status == current:
            return job
        allowed = ALLOWED_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise InvalidTransition(
                f"cannot move job {job_id} from '{current.value}' to '{new_status.value}' "
                f"(allowed: {sorted(s.value for s in allowed)})"
            )
        job.status = new_status
        job.status_history.append(
            {"status": new_status.value, "at": now_utc().isoformat(), "note": note}
        )
        self.storage.put(Collections.JOBS, job.id, job.model_dump(mode="json"))
        return job

    def list_by_status(self, status: WorkspaceStatus | None = None) -> list[JobPosting]:
        jobs = [JobPosting(**d) for d in self.storage.list(Collections.JOBS)]
        if status:
            jobs = [j for j in jobs if str(j.status) == str(status)]
        return jobs

    def board(self) -> dict[str, list[JobPosting]]:
        """Group all jobs by status, handy for a kanban-style UI."""
        board: dict[str, list[JobPosting]] = {s.value: [] for s in WorkspaceStatus}
        for job in self.list_by_status():
            board.setdefault(str(job.status), []).append(job)
        return board
