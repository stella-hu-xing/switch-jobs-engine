"""Profile module service: LLM extraction + CRUD backed by StorageBackend."""

from __future__ import annotations

import logging
from typing import Any

from app.core.ids import new_id, now_utc
from app.core.llm_client import LLMClient, ModelTier
from app.core.storage import Collections, StorageBackend
from app.prompts import render
from app.schemas.profile import (
    Achievement,
    CandidateProfile,
    ExperienceItem,
    Preferences,
    QAItem,
    SkillItem,
    StarStory,
)

logger = logging.getLogger(__name__)


def _empty_extraction() -> dict[str, Any]:
    """Fallback payload used when the LLM is offline or returns junk."""
    return {
        "name": None,
        "headline": None,
        "summary": None,
        "years_experience": None,
        "seniority": "unknown",
        "experience": [],
        "skills": [],
        "achievements": [],
        "story_bank": [],
        "qa_bank": [],
        "preferences": {},
    }


def extract_profile_fields(
    llm: LLMClient,
    *,
    raw_text: str,
    source_label: str,
    preference_hints: str = "",
) -> dict[str, Any]:
    """Call the LLM to extract structured fields from raw candidate materials."""
    prompt = render(
        "profile_extract",
        raw_text=raw_text,
        source_label=source_label,
        preference_hints=preference_hints or "(none provided)",
    )
    return llm.complete_json(
        system=(
            "You extract strictly-grounded career facts as JSON. "
            "Never fabricate employers, dates, or metrics."
        ),
        user=prompt,
        tier=ModelTier.FAST,
        fallback=_empty_extraction(),
    )


def _with_ids(items: list[dict], prefix: str) -> list[dict]:
    out = []
    for item in items:
        item = dict(item)
        item.setdefault("id", new_id(prefix))
        out.append(item)
    return out


def build_candidate_profile(
    fields: dict[str, Any],
    *,
    existing: CandidateProfile | None = None,
    source_label: str,
) -> CandidateProfile:
    """Merge extracted fields into a CandidateProfile (new or existing)."""
    profile_id = existing.id if existing else new_id("profile")

    achievements = [Achievement(**a) for a in _with_ids(fields.get("achievements") or [], "ach")]
    stories = [StarStory(**s) for s in _with_ids(fields.get("story_bank") or [], "story")]
    qa_items = [QAItem(**q) for q in _with_ids(fields.get("qa_bank") or [], "qa")]
    skills = [SkillItem(**s) for s in (fields.get("skills") or [])]
    experience = [ExperienceItem(**e) for e in (fields.get("experience") or [])]
    preferences = Preferences(**(fields.get("preferences") or {}))

    if existing:
        achievements = existing.achievements + achievements
        stories = existing.story_bank + stories
        qa_items = existing.qa_bank + qa_items
        skills = _merge_skills(existing.skills, skills)
        experience = existing.experience + experience
        sources = existing.raw_sources + [source_label]
    else:
        sources = [source_label]

    return CandidateProfile(
        id=profile_id,
        name=fields.get("name") or (existing.name if existing else None),
        headline=fields.get("headline") or (existing.headline if existing else None),
        summary=fields.get("summary") or (existing.summary if existing else None),
        years_experience=fields.get("years_experience")
        or (existing.years_experience if existing else None),
        seniority=fields.get("seniority") or (existing.seniority if existing else "unknown"),
        experience=experience,
        skills=skills,
        achievements=achievements,
        story_bank=stories,
        qa_bank=qa_items,
        preferences=preferences if fields.get("preferences") else (
            existing.preferences if existing else preferences
        ),
        raw_sources=sources,
        created_at=existing.created_at if existing else now_utc(),
        updated_at=now_utc(),
    )


def _merge_skills(existing: list[SkillItem], new: list[SkillItem]) -> list[SkillItem]:
    by_name = {s.name.lower(): s for s in existing}
    for skill in new:
        key = skill.name.lower()
        if key in by_name:
            current = by_name[key]
            by_name[key] = current.model_copy(
                update={"evidence_count": current.evidence_count + 1}
            )
        else:
            by_name[key] = skill
    return list(by_name.values())


class ProfileService:
    def __init__(self, storage: StorageBackend, llm: LLMClient) -> None:
        self.storage = storage
        self.llm = llm

    def create_from_text(
        self,
        *,
        raw_text: str,
        source_label: str = "manual_text",
        preference_hints: str = "",
    ) -> CandidateProfile:
        fields = extract_profile_fields(
            self.llm, raw_text=raw_text, source_label=source_label,
            preference_hints=preference_hints,
        )
        profile = build_candidate_profile(fields, source_label=source_label)
        self.save(profile)
        return profile

    def augment_from_text(
        self,
        profile_id: str,
        *,
        raw_text: str,
        source_label: str = "manual_text",
        preference_hints: str = "",
    ) -> CandidateProfile:
        existing = self.get(profile_id)
        if existing is None:
            raise KeyError(f"profile not found: {profile_id}")
        fields = extract_profile_fields(
            self.llm, raw_text=raw_text, source_label=source_label,
            preference_hints=preference_hints,
        )
        profile = build_candidate_profile(fields, existing=existing, source_label=source_label)
        self.save(profile)
        return profile

    def save(self, profile: CandidateProfile) -> None:
        self.storage.put(Collections.PROFILES, profile.id, profile.model_dump(mode="json"))

    def get(self, profile_id: str) -> CandidateProfile | None:
        doc = self.storage.get(Collections.PROFILES, profile_id)
        return CandidateProfile(**doc) if doc else None

    def list(self) -> list[CandidateProfile]:
        return [CandidateProfile(**d) for d in self.storage.list(Collections.PROFILES)]

    def delete(self, profile_id: str) -> bool:
        return self.storage.delete(Collections.PROFILES, profile_id)
