"""Lever public postings JSON API connector.

Docs: https://github.com/lever/postings-api
``query`` is the company's Lever site slug, e.g. "netflix".
"""

from __future__ import annotations

import logging

import httpx

from app.schemas.common import JobSource
from app.schemas.job import RawPosting

logger = logging.getLogger(__name__)

BASE_URL = "https://api.lever.co/v0/postings"


class LeverConnector:
    name = "lever"

    def __init__(self, user_agent: str = "switch-jobs-engine/0.1", timeout: float = 30.0) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    def fetch(self, query: str) -> list[RawPosting]:
        """``query`` is the Lever site slug (company)."""
        site = query.strip()
        url = f"{BASE_URL}/{site}?mode=json"
        try:
            response = httpx.get(
                url, timeout=self.timeout, headers={"User-Agent": self.user_agent}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Lever fetch failed for site=%s: %s", site, exc)
            return []

        postings: list[RawPosting] = []
        for job in response.json():
            categories = job.get("categories") or {}
            description = "\n\n".join(
                part
                for part in (job.get("descriptionPlain"), job.get("additionalPlain"))
                if part
            )
            postings.append(
                RawPosting(
                    source=JobSource.LEVER,
                    source_id=job.get("id"),
                    url=job.get("hostedUrl"),
                    company=site,
                    title=job.get("text"),
                    location=categories.get("location"),
                    description=description,
                    department=categories.get("team"),
                    posted_at=str(job.get("createdAt")) if job.get("createdAt") else None,
                    extra={"site": site},
                )
            )
        return postings
