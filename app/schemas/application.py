"""Application preparation schemas (tailored resume / cover letter / Q&A)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.core.ids import now_utc
from app.schemas.common import ApplicationStage, SJEModel


class TailoredBullet(SJEModel):
    """A rewritten resume bullet that must stay grounded in a real achievement."""

    achievement_id: str
    original: str
    tailored: str
    keywords_used: list[str] = Field(default_factory=list)
    grounded: bool = True
    grounding_note: str | None = None


class QuestionAnswer(SJEModel):
    question: str
    answer: str
    source_story_ids: list[str] = Field(default_factory=list)


class DiffLine(SJEModel):
    kind: str  # context | added | removed
    text: str


class ApplicationPackage(SJEModel):
    resume_summary: str | None = None
    resume_bullets: list[TailoredBullet] = Field(default_factory=list)
    cover_letter: str | None = None
    answers: list[QuestionAnswer] = Field(default_factory=list)
    keywords_targeted: list[str] = Field(default_factory=list)
    diff: list[DiffLine] = Field(default_factory=list)
    fabrication_warnings: list[str] = Field(default_factory=list)


class Application(SJEModel):
    id: str
    profile_id: str
    job_id: str
    company: str
    title: str
    stage: ApplicationStage = ApplicationStage.DRAFT
    package: ApplicationPackage = Field(default_factory=ApplicationPackage)
    approval_note: str | None = None
    approved_by_user: bool = False
    approved_at: datetime | None = None
    submitted_at: datetime | None = None
    submission_mode: str | None = Field(
        default=None, description="handoff mode, e.g. 'manual' - the engine never auto-submits"
    )
    history: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
