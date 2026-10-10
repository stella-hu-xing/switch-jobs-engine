"""Raw + normalized job posting schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.core.ids import now_utc
from app.schemas.common import JobSource, SJEModel, Seniority, WorkMode, WorkspaceStatus


class RawPosting(SJEModel):
    """What a connector returns before normalization."""

    source: JobSource
    source_id: str | None = None
    url: str | None = None
    company: str | None = None
    title: str | None = None
    location: str | None = None
    description: str = ""
    department: str | None = None
    posted_at: str | None = None
    extra: dict = Field(default_factory=dict)


class SalaryRange(SJEModel):
    min: int | None = None
    max: int | None = None
    currency: str | None = None
    period: str | None = "year"


class JobPosting(SJEModel):
    """Normalized posting stored in the job database."""

    id: str
    dedup_key: str = Field(description="stable hash of company+title+location")
    source: JobSource
    source_id: str | None = None
    url: str | None = None
    company: str
    title: str
    location: str | None = None
    work_mode: WorkMode = WorkMode.UNKNOWN
    seniority: Seniority = Seniority.UNKNOWN
    department: str | None = None
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    salary: SalaryRange | None = None
    posted_at: str | None = None
    ingested_at: datetime = Field(default_factory=now_utc)
    status: WorkspaceStatus = WorkspaceStatus.NEW
    status_history: list[dict] = Field(default_factory=list)
    notes: str | None = None


class IngestionReport(SJEModel):
    """Result of one ingestion run (per connector or batch)."""

    source: str
    fetched: int = 0
    created: int = 0
    duplicates: int = 0
    errors: list[str] = Field(default_factory=list)
    job_ids: list[str] = Field(default_factory=list)
    duplicate_of: dict[str, str] = Field(
        default_factory=dict, description="skipped source_id -> existing job id"
    )
