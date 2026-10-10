"""Greenhouse Job Board public JSON API connector.

Docs: https://developers.greenhouse.io/job-board.html
``query`` is the company's Greenhouse board token, e.g. "stripe", "airbnb".
No authentication needed; this is a published public endpoint.
"""

from __future__ import annotations

import logging

import httpx

from app.schemas.common import JobSource
from app.schemas.job import RawPosting

logger = logging.getLogger(__name__)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseConnector:
    name = "greenhouse"

    def __init__(self, user_agent: str = "switch-jobs-engine/0.1", timeout: float = 30.0) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    def fetch(self, query: str) -> list[RawPosting]:
        """``query`` is the Greenhouse board token (company slug)."""
        board_token = query.strip()
        url = f"{BASE_URL}/{board_token}/jobs?content=true"
        try:
            response = httpx.get(
                url, timeout=self.timeout, headers={"User-Agent": self.user_agent}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Greenhouse fetch failed for board=%s: %s", board_token, exc)
            return []

        payload = response.json()
        postings: list[RawPosting] = []
        for job in payload.get("jobs", []):
            location = (job.get("location") or {}).get("name")
            postings.append(
                RawPosting(
                    source=JobSource.GREENHOUSE,
                    source_id=str(job.get("id")),
                    url=job.get("absolute_url"),
                    company=board_token,
                    title=job.get("title"),
                    location=location,
                    description=job.get("content") or "",
                    department=_first_department(job),
                    posted_at=job.get("updated_at"),
                    extra={"board_token": board_token},
                )
            )
        return postings


def _first_department(job: dict) -> str | None:
    departments = job.get("departments") or []
    return departments[0].get("name") if departments else None
