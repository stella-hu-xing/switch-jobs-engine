"""Candidate profile schemas -- output of the Self Preparation stage."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.core.ids import now_utc
from app.schemas.common import SJEModel, Seniority, WorkMode


class Achievement(SJEModel):
    """A single real, evidence-backed accomplishment from the candidate's history."""

    id: str
    title: str
    company: str | None = None
    role: str | None = None
    summary: str
    impact: str | None = Field(default=None, description="Quantified outcome if stated")
    skills: list[str] = Field(default_factory=list)
    source_excerpt: str | None = Field(
        default=None, description="Verbatim snippet from user input that grounds this item"
    )


class StarStory(SJEModel):
    """Behavioural story in STAR form, derived only from the candidate's own input."""

    id: str
    title: str
    situation: str
    task: str
    action: str
    result: str
    themes: list[str] = Field(default_factory=list)
    related_achievement_ids: list[str] = Field(default_factory=list)


class QAItem(SJEModel):
    """Pre-prepared answer to a commonly asked question."""

    id: str
    question: str
    answer: str
    category: Literal["behavioural", "technical", "motivation", "logistics", "other"] = "other"
    related_story_ids: list[str] = Field(default_factory=list)


class SkillItem(SJEModel):
    name: str
    category: str = "other"  # language | framework | cloud | data | practice | domain | other
    years: float | None = None
    evidence_count: int = 0


class ExperienceItem(SJEModel):
    company: str
    title: str
    start: str | None = None
    end: str | None = None
    location: str | None = None
    highlights: list[str] = Field(default_factory=list)


class Preferences(SJEModel):
    target_titles: list[str] = Field(default_factory=list)
    target_seniority: Seniority = Seniority.UNKNOWN
    locations: list[str] = Field(default_factory=list)
    work_modes: list[WorkMode] = Field(default_factory=list)
    min_salary: int | None = None
    currency: str | None = None
    industries: list[str] = Field(default_factory=list)
    company_sizes: list[str] = Field(default_factory=list)
    culture_values: list[str] = Field(
        default_factory=list, description="e.g. 'strong engineering culture', 'work-life balance'"
    )
    dealbreakers: list[str] = Field(default_factory=list)
    tech_interests: list[str] = Field(default_factory=list)


class CandidateProfile(SJEModel):
    """Structured profile: experience, skills, preferences, story bank, Q&A bank."""

    id: str
    name: str | None = None
    headline: str | None = None
    summary: str | None = None
    years_experience: float | None = None
    seniority: Seniority = Seniority.UNKNOWN
    experience: list[ExperienceItem] = Field(default_factory=list)
    skills: list[SkillItem] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)
    story_bank: list[StarStory] = Field(default_factory=list)
    qa_bank: list[QAItem] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)
    raw_sources: list[str] = Field(
        default_factory=list, description="Labels of the inputs this profile was built from"
    )
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    def skill_names(self) -> set[str]:
        return {s.name.strip().lower() for s in self.skills if s.name.strip()}
