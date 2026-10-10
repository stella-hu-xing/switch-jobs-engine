"""Matching service: score+rank jobs for a candidate, with LLM rationale."""

from __future__ import annotations

from app.core.ids import new_id
from app.core.llm_client import LLMClient, ModelTier
from app.core.storage import Collections, StorageBackend
from app.modules.matching.scoring import compute_score
from app.prompts import render
from app.schemas.company import CompanyProfile
from app.schemas.job import JobPosting
from app.schemas.match import MatchResult
from app.schemas.profile import CandidateProfile


def build_rationale(
    llm: LLMClient,
    *,
    profile: CandidateProfile,
    job: JobPosting,
    score: float,
    components: list,
    matched: list[str],
    missing: list[str],
) -> dict:
    prompt = render(
        "match_rationale",
        title=job.title,
        company=job.company,
        location=job.location or "unspecified",
        score=score,
        components="; ".join(f"{c.name}={c.score}" for c in components),
        matched_skills=", ".join(matched) or "none",
        missing_skills=", ".join(missing) or "none",
        candidate_headline=profile.headline or "",
        preferences=profile.preferences.model_dump_json(),
    )
    fallback = {
        "rationale": (
            f"Overall score {score}/100 based on skills, seniority, location and "
            f"compensation fit. Matched skills: {', '.join(matched) or 'none'}."
        ),
        "top_gaps": missing[:3],
    }
    return llm.complete_json(
        system="You write concise, honest hiring-fit rationales as JSON.",
        user=prompt,
        tier=ModelTier.FAST,
        fallback=fallback,
    )


class MatchingService:
    def __init__(self, storage: StorageBackend, llm: LLMClient) -> None:
        self.storage = storage
        self.llm = llm

    def match(
        self,
        profile: CandidateProfile,
        job: JobPosting,
        *,
        company_profile: CompanyProfile | None = None,
    ) -> MatchResult:
        score, components, matched, missing = compute_score(profile, job)
        rationale_fields = build_rationale(
            self.llm,
            profile=profile,
            job=job,
            score=score,
            components=components,
            matched=matched,
            missing=missing,
        )
        result = MatchResult(
            id=new_id("match"),
            profile_id=profile.id,
            job_id=job.id,
            company=job.company,
            title=job.title,
            score=score,
            components=components,
            matched_skills=matched,
            missing_skills=missing,
            rationale=rationale_fields.get("rationale", ""),
            company_match_score=company_profile.match_score if company_profile else None,
        )
        self.storage.put(Collections.MATCHES, result.id, result.model_dump(mode="json"))
        return result

    def rank_jobs(
        self,
        profile: CandidateProfile,
        jobs: list[JobPosting],
        *,
        company_profiles: dict[str, CompanyProfile] | None = None,
        top_n: int | None = None,
    ) -> list[MatchResult]:
        company_profiles = company_profiles or {}
        results = [
            self.match(profile, job, company_profile=company_profiles.get(job.company))
            for job in jobs
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n] if top_n else results

    def list_matches(self, profile_id: str | None = None) -> list[MatchResult]:
        matches = [MatchResult(**d) for d in self.storage.list(Collections.MATCHES)]
        if profile_id:
            matches = [m for m in matches if m.profile_id == profile_id]
        return sorted(matches, key=lambda m: m.score, reverse=True)
