"""Deterministic scoring helpers. Kept separate from the LLM-written rationale
so the ranking itself is reproducible/testable without any model calls.
"""

from __future__ import annotations

from app.core.ids import normalize_text
from app.schemas.common import SENIORITY_RANK, WorkMode
from app.schemas.job import JobPosting
from app.schemas.match import ScoreComponent
from app.schemas.profile import CandidateProfile

SKILLS_WEIGHT = 0.45
SENIORITY_WEIGHT = 0.2
LOCATION_WEIGHT = 0.2
COMP_WEIGHT = 0.15


def score_skills(profile: CandidateProfile, job: JobPosting) -> tuple[ScoreComponent, list[str], list[str]]:
    candidate_skills = profile.skill_names()
    job_skills = {s.strip().lower() for s in (job.tech_stack + job.keywords) if s.strip()}
    if not job_skills:
        return (
            ScoreComponent(name="skills", score=50.0, weight=SKILLS_WEIGHT, detail="Job lists no skills/keywords"),
            [],
            [],
        )
    matched = sorted(candidate_skills & job_skills)
    missing = sorted(job_skills - candidate_skills)
    overlap_ratio = len(matched) / len(job_skills)
    score = round(overlap_ratio * 100, 1)
    detail = f"{len(matched)}/{len(job_skills)} job skills matched"
    return ScoreComponent(name="skills", score=score, weight=SKILLS_WEIGHT, detail=detail), matched, missing


def score_seniority(profile: CandidateProfile, job: JobPosting) -> ScoreComponent:
    profile_rank = SENIORITY_RANK.get(str(profile.seniority), 2)
    job_rank = SENIORITY_RANK.get(str(job.seniority), 2)
    distance = abs(profile_rank - job_rank)
    score = max(0.0, 100.0 - distance * 25.0)
    detail = f"candidate={profile.seniority} job={job.seniority}"
    return ScoreComponent(name="seniority", score=score, weight=SENIORITY_WEIGHT, detail=detail)


def score_location(profile: CandidateProfile, job: JobPosting) -> ScoreComponent:
    prefs = profile.preferences
    work_modes = {str(m) for m in prefs.work_modes}
    if job.work_mode == WorkMode.REMOTE and (not work_modes or "remote" in work_modes):
        return ScoreComponent(name="location", score=100.0, weight=LOCATION_WEIGHT, detail="remote job matches remote preference")

    locations = {normalize_text(loc) for loc in prefs.locations}
    job_location = normalize_text(job.location)
    if not locations:
        score, detail = 60.0, "candidate stated no location preference"
    elif job_location and any(loc in job_location or job_location in loc for loc in locations):
        score, detail = 100.0, "job location matches a stated preference"
    elif job.work_mode in (WorkMode.HYBRID, WorkMode.ONSITE) and "remote" in work_modes and len(work_modes) == 1:
        score, detail = 20.0, "candidate wants remote only; job is not remote"
    else:
        score, detail = 40.0, "job location not in stated preferences"
    return ScoreComponent(name="location", score=score, weight=LOCATION_WEIGHT, detail=detail)


def score_compensation(profile: CandidateProfile, job: JobPosting) -> ScoreComponent:
    min_salary = profile.preferences.min_salary
    if not min_salary or not job.salary or job.salary.max is None:
        return ScoreComponent(name="compensation", score=60.0, weight=COMP_WEIGHT, detail="insufficient salary data")
    if job.salary.max >= min_salary:
        return ScoreComponent(name="compensation", score=100.0, weight=COMP_WEIGHT, detail="job range meets minimum")
    if job.salary.min and job.salary.min >= min_salary * 0.85:
        return ScoreComponent(name="compensation", score=55.0, weight=COMP_WEIGHT, detail="job range close to minimum")
    return ScoreComponent(name="compensation", score=20.0, weight=COMP_WEIGHT, detail="job range below minimum")


def compute_score(profile: CandidateProfile, job: JobPosting) -> tuple[float, list[ScoreComponent], list[str], list[str]]:
    skills_component, matched, missing = score_skills(profile, job)
    components = [
        skills_component,
        score_seniority(profile, job),
        score_location(profile, job),
        score_compensation(profile, job),
    ]
    total_weight = sum(c.weight for c in components) or 1.0
    overall = sum(c.score * c.weight for c in components) / total_weight
    return round(overall, 1), components, matched, missing
