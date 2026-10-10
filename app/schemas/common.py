"""Shared enums and base model configuration."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class SJEModel(BaseModel):
    """Base model: tolerant of extra input, serializes enums by value."""

    model_config = ConfigDict(extra="ignore", use_enum_values=True, populate_by_name=True)


class Seniority(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    MANAGER = "manager"
    DIRECTOR = "director"
    UNKNOWN = "unknown"


SENIORITY_RANK: dict[str, int] = {
    Seniority.INTERN.value: 0,
    Seniority.JUNIOR.value: 1,
    Seniority.MID.value: 2,
    Seniority.SENIOR.value: 3,
    Seniority.STAFF.value: 4,
    Seniority.PRINCIPAL.value: 5,
    Seniority.MANAGER.value: 4,
    Seniority.DIRECTOR.value: 6,
    Seniority.UNKNOWN.value: 2,
}


class WorkMode(str, Enum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class JobSource(str, Enum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    MANUAL_URL = "manual_url"
    MANUAL_TEXT = "manual_text"
    LINKEDIN_MANUAL = "linkedin_manual"


class WorkspaceStatus(str, Enum):
    """Workspace state machine (see app/modules/workspace/service.py)."""

    NEW = "new"
    REVIEWING = "reviewing"
    SAVED = "saved"
    REJECTED = "rejected"
    PURSUING = "pursuing"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    CLOSED = "closed"


class ApplicationStage(str, Enum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    SUBMITTED = "submitted"
