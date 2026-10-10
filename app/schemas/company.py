"""Company research schemas -- culture / vision / tech match."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.core.ids import now_utc
from app.schemas.common import SJEModel


class CompanyMaterial(SJEModel):
    """A user-supplied or fetched piece of company evidence."""

    kind: str = Field(
        default="other",
        description="website | careers | eng_blog | review | news | funding | other",
    )
    label: str | None = None
    url: str | None = None
    text: str = ""


class CultureSignal(SJEModel):
    theme: str
    sentiment: str = "neutral"  # positive | mixed | negative | neutral
    evidence: str | None = None


class CompanyProfile(SJEModel):
    id: str
    name: str
    website: str | None = None
    industry: str | None = None
    size: str | None = None
    mission: str | None = None
    vision: str | None = None
    culture_summary: str | None = None
    culture_signals: list[CultureSignal] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    engineering_practices: list[str] = Field(default_factory=list)
    interview_process: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    green_flags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    match_score: float | None = Field(default=None, ge=0, le=100)
    match_rationale: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
