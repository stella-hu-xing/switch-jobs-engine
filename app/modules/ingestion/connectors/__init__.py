"""Pluggable JobSourceConnector implementations."""

from app.modules.ingestion.connectors.base import JobSourceConnector
from app.modules.ingestion.connectors.greenhouse import GreenhouseConnector
from app.modules.ingestion.connectors.lever import LeverConnector
from app.modules.ingestion.connectors.manual_url import ManualUrlConnector

__all__ = [
    "GreenhouseConnector",
    "JobSourceConnector",
    "LeverConnector",
    "ManualUrlConnector",
]
