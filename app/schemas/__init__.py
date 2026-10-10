"""Pydantic v2 schemas shared across modules."""

from app.schemas.application import (
    Application,
    ApplicationPackage,
    DiffLine,
    QuestionAnswer,
    TailoredBullet,
)
from app.schemas.common import (
    SENIORITY_RANK,
    ApplicationStage,
    JobSource,
    Seniority,
    SJEModel,
    WorkMode,
    WorkspaceStatus,
)
from app.schemas.company import CompanyMaterial, CompanyProfile, CultureSignal
from app.schemas.interview import (
    InterviewBrief,
    InterviewDebrief,
    LikelyQuestion,
    MockSession,
    MockTurn,
)
from app.schemas.job import IngestionReport, JobPosting, RawPosting, SalaryRange
from app.schemas.match import MatchResult, ScoreComponent
from app.schemas.profile import (
    Achievement,
    CandidateProfile,
    ExperienceItem,
    Preferences,
    QAItem,
    SkillItem,
    StarStory,
)

__all__ = [
    "SENIORITY_RANK",
    "Achievement",
    "Application",
    "ApplicationPackage",
    "ApplicationStage",
    "CandidateProfile",
    "CompanyMaterial",
    "CompanyProfile",
    "CultureSignal",
    "DiffLine",
    "ExperienceItem",
    "IngestionReport",
    "InterviewBrief",
    "InterviewDebrief",
    "JobPosting",
    "JobSource",
    "LikelyQuestion",
    "MatchResult",
    "MockSession",
    "MockTurn",
    "Preferences",
    "QAItem",
    "QuestionAnswer",
    "RawPosting",
    "SJEModel",
    "SalaryRange",
    "ScoreComponent",
    "Seniority",
    "SkillItem",
    "StarStory",
    "TailoredBullet",
    "WorkMode",
    "WorkspaceStatus",
]
