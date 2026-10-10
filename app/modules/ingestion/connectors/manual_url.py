"""User-provided URL / pasted-text connector.

Covers: a job posting URL pasted by the user, or raw JD text pasted directly
(e.g. copied from a LinkedIn posting or saved-job export). This is the ONLY
way LinkedIn content enters the system -- there is no automated LinkedIn
fetch/scrape here, by design (see connectors/base.py docstring).
"""

from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from app.schemas.common import JobSource
from app.schemas.job import RawPosting

logger = logging.getLogger(__name__)


class ManualUrlConnector:
    """``fetch(query)`` treats ``query`` as a URL and downloads+strips the HTML."""

    name = "manual_url"

    def __init__(self, user_agent: str = "switch-jobs-engine/0.1", timeout: float = 30.0) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    def fetch(self, query: str) -> list[RawPosting]:
        url = query.strip()
        try:
            response = httpx.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Manual URL fetch failed for %s: %s", url, exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        title = soup.title.string.strip() if soup.title and soup.title.string else None
        text = " ".join(soup.get_text(separator=" ").split())

        source = JobSource.LINKEDIN_MANUAL if "linkedin.com" in url else JobSource.MANUAL_URL
        return [
            RawPosting(
                source=source,
                source_id=None,
                url=url,
                company=None,
                title=title,
                location=None,
                description=text,
                extra={"fetched_html_bytes": len(response.text)},
            )
        ]


def from_pasted_text(text: str, *, title: str | None = None, company: str | None = None) -> RawPosting:
    """Build a RawPosting directly from pasted JD text (no fetch at all)."""
    return RawPosting(
        source=JobSource.MANUAL_TEXT,
        source_id=None,
        url=None,
        company=company,
        title=title,
        location=None,
        description=text,
    )
