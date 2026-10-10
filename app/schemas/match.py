"""Matching / ranking schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.core.ids import now_utc
from app.schemas.common import SJEModel


class ScoreComponent(SJEModel):
    name: str
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    detail: str | None = None


class MatchResult(SJEModel):
    id: str
    profile_id: str
    job_id: str
    company: str
    title: str
    score: float = Field(ge=0, le=100)
    components: list[ScoreComponent] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    rationale: str = ""
    company_match_score: float | None = None
    created_at: datetime = Field(default_factory=now_utc)
