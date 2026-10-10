"""Connector/adapter interface used by all job sources.

Boundary note: connectors in this codebase are limited to (a) legitimate
public job-board JSON APIs (Greenhouse, Lever) and (b) content the user
explicitly supplies (a pasted URL/JD, or an exported LinkedIn saved-job
link/text). There is intentionally no automated LinkedIn scraper -- that
would violate LinkedIn's ToS. See docs/architecture.md "Sourcing boundaries".
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.job import RawPosting


@runtime_checkable
class JobSourceConnector(Protocol):
    """Every connector fetches raw postings for a query and returns them unparsed."""

    name: str

    def fetch(self, query: str) -> list[RawPosting]: ...
