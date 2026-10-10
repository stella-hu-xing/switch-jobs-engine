"""Normalization + dedup + persistence of RawPosting -> JobPosting."""

from __future__ import annotations

import logging
from typing import Any

from app.core.ids import jaccard, new_id, normalize_text, now_utc, stable_hash, token_set
from app.core.llm_client import LLMClient, ModelTier
from app.core.storage import Collections, StorageBackend
from app.modules.ingestion.connectors.base import JobSourceConnector
from app.prompts import render
from app.schemas.job import IngestionReport, JobPosting, RawPosting, SalaryRange

logger = logging.getLogger(__name__)

DESCRIPTION_SIMILARITY_THRESHOLD = 0.85


def dedup_key(company: str, title: str, location: str | None) -> str:
    return stable_hash(company, title, location or "")


def normalize_posting(llm: LLMClient, raw: RawPosting) -> dict[str, Any]:
    """LLM-assisted normalization of the free-text posting into structured fields."""
    prompt = render(
        "job_normalize",
        company=raw.company or "",
        title=raw.title or "",
        location=raw.location or "",
        url=raw.url or "",
        description=raw.description[:12000],
    )
    fallback = {
        "title": raw.title or "Unknown title",
        "company": raw.company or "Unknown company",
        "location": raw.location,
        "work_mode": "unknown",
        "seniority": "unknown",
        "requirements": [],
        "keywords": [],
        "tech_stack": [],
        "salary": None,
    }
    return llm.complete_json(
        system="You extract structured job-posting fields as JSON, grounded only in the text given.",
        user=prompt,
        tier=ModelTier.FAST,
        fallback=fallback,
    )


def _is_near_duplicate(a: JobPosting, b_description: str, b_company: str, b_title: str) -> bool:
    if normalize_text(a.company) != normalize_text(b_company):
        return False
    if normalize_text(a.title) != normalize_text(b_title):
        return False
    similarity = jaccard(token_set(a.description), token_set(b_description))
    return similarity >= DESCRIPTION_SIMILARITY_THRESHOLD


class IngestionService:
    def __init__(self, storage: StorageBackend, llm: LLMClient) -> None:
        self.storage = storage
        self.llm = llm

    def _existing_jobs(self) -> list[JobPosting]:
        return [JobPosting(**d) for d in self.storage.list(Collections.JOBS)]

    def ingest_raw(self, raw: RawPosting, *, source_name: str) -> tuple[JobPosting | None, bool]:
        """Normalize one RawPosting, dedup against stored jobs, persist if new.

        Returns (job, created). If a near-duplicate exists, returns the
        existing job and False.
        """
        company = raw.company or "Unknown company"
        title = raw.title or "Unknown title"
        key = dedup_key(company, title, raw.location)

        for existing in self._existing_jobs():
            if existing.dedup_key == key or _is_near_duplicate(
                existing, raw.description, company, title
            ):
                return existing, False

        fields = normalize_posting(self.llm, raw)
        salary = SalaryRange(**fields["salary"]) if fields.get("salary") else None
        job = JobPosting(
            id=new_id("job"),
            dedup_key=key,
            source=raw.source,
            source_id=raw.source_id,
            url=raw.url,
            company=fields.get("company") or company,
            title=fields.get("title") or title,
            location=fields.get("location") or raw.location,
            work_mode=fields.get("work_mode", "unknown"),
            seniority=fields.get("seniority", "unknown"),
            department=raw.department,
            description=raw.description,
            requirements=fields.get("requirements") or [],
            keywords=fields.get("keywords") or [],
            tech_stack=fields.get("tech_stack") or [],
            salary=salary,
            posted_at=raw.posted_at,
            ingested_at=now_utc(),
            status_history=[{"status": "new", "at": now_utc().isoformat(), "by": source_name}],
        )
        self.storage.put(Collections.JOBS, job.id, job.model_dump(mode="json"))
        return job, True

    def run_connector(self, connector: JobSourceConnector, query: str) -> IngestionReport:
        report = IngestionReport(source=connector.name)
        raw_postings = connector.fetch(query)
        report.fetched = len(raw_postings)
        for raw in raw_postings:
            try:
                job, created = self.ingest_raw(raw, source_name=connector.name)
            except Exception as exc:  # noqa: BLE001 - keep ingesting the rest of the batch
                logger.exception("Failed to ingest posting from %s", connector.name)
                report.errors.append(str(exc))
                continue
            if job is None:
                continue
            if created:
                report.created += 1
                report.job_ids.append(job.id)
            else:
                report.duplicates += 1
                report.duplicate_of[raw.source_id or raw.url or raw.title or "unknown"] = job.id
        return report

    def list_jobs(self) -> list[JobPosting]:
        return self._existing_jobs()

    def get_job(self, job_id: str) -> JobPosting | None:
        doc = self.storage.get(Collections.JOBS, job_id)
        return JobPosting(**doc) if doc else None
