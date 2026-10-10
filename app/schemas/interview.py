"""Interview prep schemas: briefing, mock loop, debrief."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.core.ids import now_utc
from app.schemas.common import SJEModel


class LikelyQuestion(SJEModel):
    question: str
    category: str = "behavioural"  # behavioural | technical | system_design | culture | motivation
    why_likely: str | None = None
    suggested_story_ids: list[str] = Field(default_factory=list)
    draft_answer: str | None = None


class InterviewBrief(SJEModel):
    id: str
    profile_id: str
    job_id: str | None = None
    company: str
    title: str | None = None
    company_snapshot: str | None = None
    culture_notes: list[str] = Field(default_factory=list)
    tech_focus: list[str] = Field(default_factory=list)
    likely_questions: list[LikelyQuestion] = Field(default_factory=list)
    questions_to_ask: list[str] = Field(default_factory=list)
    preparation_gaps: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)


class MockTurn(SJEModel):
    index: int
    question: str
    answer: str | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    feedback: str | None = None
    asked_at: datetime = Field(default_factory=now_utc)


class MockSession(SJEModel):
    id: str
    brief_id: str
    profile_id: str
    company: str
    turns: list[MockTurn] = Field(default_factory=list)
    finished: bool = False
    overall_feedback: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class InterviewDebrief(SJEModel):
    """Post-interview capture; feeds new stories/Q&A back into the profile."""

    id: str
    profile_id: str
    company: str
    job_id: str | None = None
    round_name: str | None = None
    questions_asked: list[str] = Field(default_factory=list)
    what_went_well: str | None = None
    what_to_improve: str | None = None
    interviewer_signals: str | None = None
    outcome: str | None = None
    derived_qa_ids: list[str] = Field(default_factory=list)
    positioning_advice: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
