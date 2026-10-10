"""Company research service: summarize user-supplied materials with the LLM."""

from __future__ import annotations

from app.core.ids import new_id, now_utc
from app.core.llm_client import LLMClient, ModelTier
from app.core.storage import Collections, StorageBackend
from app.prompts import render
from app.schemas.company import CompanyMaterial, CompanyProfile, CultureSignal
from app.schemas.profile import CandidateProfile, Preferences


def _materials_text(materials: list[CompanyMaterial]) -> str:
    chunks = []
    for m in materials:
        label = m.label or m.kind
        chunks.append(f"[{m.kind} - {label}] {m.url or ''}\n{m.text}")
    return "\n\n---\n\n".join(chunks) if chunks else "(no materials supplied)"


def _preferences_text(preferences: Preferences | None) -> str:
    if preferences is None:
        return "(none provided)"
    return preferences.model_dump_json()


def research_company(
    llm: LLMClient,
    *,
    company_name: str,
    materials: list[CompanyMaterial],
    preferences: Preferences | None = None,
) -> dict:
    prompt = render(
        "company_research",
        company_name=company_name,
        preferences=_preferences_text(preferences),
        materials=_materials_text(materials),
    )
    fallback = {
        "industry": None,
        "size": None,
        "mission": None,
        "vision": None,
        "culture_summary": None,
        "culture_signals": [],
        "values": [],
        "tech_stack": [],
        "engineering_practices": [],
        "interview_process": [],
        "green_flags": [],
        "red_flags": [],
        "match_score": 50.0,
        "match_rationale": "No materials supplied or LLM offline; neutral default score.",
    }
    return llm.complete_json(
        system="You summarize company research strictly from supplied materials as JSON.",
        user=prompt,
        tier=ModelTier.SMART,
        fallback=fallback,
    )


class CompanyResearchService:
    def __init__(self, storage: StorageBackend, llm: LLMClient) -> None:
        self.storage = storage
        self.llm = llm

    def build_profile(
        self,
        *,
        company_name: str,
        materials: list[CompanyMaterial],
        candidate_profile: CandidateProfile | None = None,
        existing_id: str | None = None,
    ) -> CompanyProfile:
        preferences = candidate_profile.preferences if candidate_profile else None
        fields = research_company(
            self.llm, company_name=company_name, materials=materials, preferences=preferences
        )
        signals = [CultureSignal(**s) for s in (fields.get("culture_signals") or [])]
        profile = CompanyProfile(
            id=existing_id or new_id("company"),
            name=company_name,
            industry=fields.get("industry"),
            size=fields.get("size"),
            mission=fields.get("mission"),
            vision=fields.get("vision"),
            culture_summary=fields.get("culture_summary"),
            culture_signals=signals,
            values=fields.get("values") or [],
            tech_stack=fields.get("tech_stack") or [],
            engineering_practices=fields.get("engineering_practices") or [],
            interview_process=fields.get("interview_process") or [],
            green_flags=fields.get("green_flags") or [],
            red_flags=fields.get("red_flags") or [],
            sources=[m.url or m.label or m.kind for m in materials],
            match_score=fields.get("match_score"),
            match_rationale=fields.get("match_rationale"),
            updated_at=now_utc(),
        )
        self.save(profile)
        return profile

    def save(self, profile: CompanyProfile) -> None:
        self.storage.put(Collections.COMPANIES, profile.id, profile.model_dump(mode="json"))

    def get(self, company_id: str) -> CompanyProfile | None:
        doc = self.storage.get(Collections.COMPANIES, company_id)
        return CompanyProfile(**doc) if doc else None

    def list(self) -> list[CompanyProfile]:
        return [CompanyProfile(**d) for d in self.storage.list(Collections.COMPANIES)]
