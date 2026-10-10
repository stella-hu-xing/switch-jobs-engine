"""Application prep service: tailoring strictly grounded in the real profile,
plus a diff/preview and an explicit human approval gate before any submission.
"""

from __future__ import annotations

import difflib
import logging

from app.core.ids import new_id, now_utc
from app.core.llm_client import LLMClient, ModelTier
from app.core.storage import Collections, StorageBackend
from app.prompts import render
from app.schemas.application import (
    Application,
    ApplicationPackage,
    DiffLine,
    QuestionAnswer,
    TailoredBullet,
)
from app.schemas.common import ApplicationStage
from app.schemas.company import CompanyProfile
from app.schemas.job import JobPosting
from app.schemas.profile import CandidateProfile

logger = logging.getLogger(__name__)


def _achievements_text(profile: CandidateProfile) -> str:
    lines = []
    for a in profile.achievements:
        lines.append(f"- id={a.id} | {a.title}: {a.summary} (impact: {a.impact or 'n/a'})")
    return "\n".join(lines) if lines else "(no achievements on file)"


def _profile_extract(profile: CandidateProfile) -> str:
    stories = "\n".join(
        f"- id={s.id} | {s.title}: S={s.situation} T={s.task} A={s.action} R={s.result}"
        for s in profile.story_bank
    )
    qa = "\n".join(f"- id={q.id} | Q: {q.question} A: {q.answer}" for q in profile.qa_bank)
    return f"Stories:\n{stories or '(none)'}\n\nQ&A bank:\n{qa or '(none)'}"


def tailor_resume(llm: LLMClient, *, profile: CandidateProfile, job: JobPosting) -> dict:
    prompt = render(
        "resume_tailor",
        title=job.title,
        company=job.company,
        keywords=", ".join(job.keywords) or "(none extracted)",
        description=job.description[:8000],
        achievements=_achievements_text(profile),
        candidate_headline=profile.headline or "",
    )
    fallback = {
        "resume_summary": profile.summary,
        "bullets": [
            {"achievement_id": a.id, "tailored": a.summary, "keywords_used": []}
            for a in profile.achievements
        ],
        "keywords_targeted": [],
        "notes": ["offline/fallback: achievements copied verbatim, no tailoring applied"],
    }
    return llm.complete_json(
        system="You tailor resumes strictly from the achievement bank given. Never fabricate.",
        user=prompt,
        tier=ModelTier.SMART,
        fallback=fallback,
    )


def write_cover_letter(
    llm: LLMClient, *, profile: CandidateProfile, job: JobPosting, company: CompanyProfile | None
) -> dict:
    company_notes = ""
    if company:
        company_notes = f"Culture: {company.culture_summary}\nValues: {', '.join(company.values)}"
    prompt = render(
        "cover_letter",
        title=job.title,
        company=job.company,
        description=job.description[:6000],
        company_notes=company_notes or "(none)",
        achievements=_achievements_text(profile),
    )
    fallback = {
        "cover_letter": (
            f"I am applying for the {job.title} role at {job.company}. "
            "(offline stub: configure OPENROUTER_API_KEY to generate a real letter)"
        ),
        "claims_used": [],
    }
    return llm.complete_json(
        system="You write grounded, specific cover letters as JSON. No fabrication, no filler.",
        user=prompt,
        tier=ModelTier.SMART,
        fallback=fallback,
    )


def answer_questions(
    llm: LLMClient, *, profile: CandidateProfile, job: JobPosting, questions: list[str]
) -> dict:
    if not questions:
        return {"answers": []}
    prompt = render(
        "application_answers",
        title=job.title,
        company=job.company,
        questions="\n".join(f"- {q}" for q in questions),
        profile_extract=_profile_extract(profile),
    )
    fallback = {
        "answers": [
            {"question": q, "answer": "NEEDS_USER_INPUT: offline mode", "source_story_ids": []}
            for q in questions
        ]
    }
    return llm.complete_json(
        system="You answer application questions strictly from the candidate's real profile.",
        user=prompt,
        tier=ModelTier.SMART,
        fallback=fallback,
    )


def _check_grounding(bullet: TailoredBullet, achievement_ids: set[str]) -> TailoredBullet:
    if bullet.achievement_id not in achievement_ids:
        bullet.grounded = False
        bullet.grounding_note = "achievement_id not found in candidate profile - flagged, not used"
    return bullet


def _build_diff(original: str, tailored: str) -> list[DiffLine]:
    matcher = difflib.ndiff(original.split(), tailored.split())
    diff: list[DiffLine] = []
    for token in matcher:
        if token.startswith("+ "):
            diff.append(DiffLine(kind="added", text=token[2:]))
        elif token.startswith("- "):
            diff.append(DiffLine(kind="removed", text=token[2:]))
        elif token.startswith("  "):
            diff.append(DiffLine(kind="context", text=token[2:]))
    return diff


class ApplicationPrepService:
    def __init__(self, storage: StorageBackend, llm: LLMClient) -> None:
        self.storage = storage
        self.llm = llm

    def draft(
        self,
        *,
        profile: CandidateProfile,
        job: JobPosting,
        company: CompanyProfile | None = None,
        questions: list[str] | None = None,
        existing_id: str | None = None,
    ) -> Application:
        achievement_by_id = {a.id: a for a in profile.achievements}
        achievement_ids = set(achievement_by_id)

        resume_fields = tailor_resume(self.llm, profile=profile, job=job)
        bullets: list[TailoredBullet] = []
        all_diff: list[DiffLine] = []
        for b in resume_fields.get("bullets", []):
            original_text = achievement_by_id[b["achievement_id"]].summary if b["achievement_id"] in achievement_by_id else ""
            bullet = TailoredBullet(
                achievement_id=b["achievement_id"],
                original=original_text,
                tailored=b["tailored"],
                keywords_used=b.get("keywords_used", []),
            )
            bullet = _check_grounding(bullet, achievement_ids)
            bullets.append(bullet)
            all_diff.extend(_build_diff(original_text, b["tailored"]))

        cover_fields = write_cover_letter(self.llm, profile=profile, job=job, company=company)
        qa_fields = answer_questions(self.llm, profile=profile, job=job, questions=questions or [])

        fabrication_warnings = [
            f"Bullet for achievement_id={b.achievement_id} could not be grounded: {b.grounding_note}"
            for b in bullets
            if not b.grounded
        ]

        package = ApplicationPackage(
            resume_summary=resume_fields.get("resume_summary"),
            resume_bullets=bullets,
            cover_letter=cover_fields.get("cover_letter"),
            answers=[QuestionAnswer(**a) for a in qa_fields.get("answers", [])],
            keywords_targeted=resume_fields.get("keywords_targeted", []),
            diff=all_diff,
            fabrication_warnings=fabrication_warnings,
        )

        application = Application(
            id=existing_id or new_id("app"),
            profile_id=profile.id,
            job_id=job.id,
            company=job.company,
            title=job.title,
            stage=ApplicationStage.AWAITING_APPROVAL,
            package=package,
            history=[{"stage": "draft", "at": now_utc().isoformat()}],
            updated_at=now_utc(),
        )
        self.save(application)
        return application

    def approve(self, application_id: str, *, note: str | None = None) -> Application:
        """User approval gate: nothing is ever auto-submitted before this call."""
        application = self._require(application_id)
        application.stage = ApplicationStage.APPROVED
        application.approved_by_user = True
        application.approved_at = now_utc()
        application.approval_note = note
        application.history.append(
            {"stage": "approved", "at": now_utc().isoformat(), "note": note}
        )
        application.updated_at = now_utc()
        self.save(application)
        return application

    def request_changes(self, application_id: str, *, note: str) -> Application:
        application = self._require(application_id)
        application.stage = ApplicationStage.CHANGES_REQUESTED
        application.approval_note = note
        application.history.append(
            {"stage": "changes_requested", "at": now_utc().isoformat(), "note": note}
        )
        application.updated_at = now_utc()
        self.save(application)
        return application

    def mark_submitted(self, application_id: str, *, submission_mode: str = "manual") -> Application:
        application = self._require(application_id)
        if not application.approved_by_user:
            raise PermissionError(
                "application has not passed the user approval gate; call approve() first"
            )
        application.stage = ApplicationStage.SUBMITTED
        application.submitted_at = now_utc()
        application.submission_mode = submission_mode
        application.history.append(
            {"stage": "submitted", "at": now_utc().isoformat(), "mode": submission_mode}
        )
        application.updated_at = now_utc()
        self.save(application)
        return application

    def _require(self, application_id: str) -> Application:
        app = self.get(application_id)
        if app is None:
            raise KeyError(f"application not found: {application_id}")
        return app

    def save(self, application: Application) -> None:
        self.storage.put(
            Collections.APPLICATIONS, application.id, application.model_dump(mode="json")
        )

    def get(self, application_id: str) -> Application | None:
        doc = self.storage.get(Collections.APPLICATIONS, application_id)
        return Application(**doc) if doc else None

    def list(self) -> list[Application]:
        return [Application(**d) for d in self.storage.list(Collections.APPLICATIONS)]
