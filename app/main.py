"""FastAPI application entrypoint.

Run locally with:  uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.settings import get_settings
from app.core.telemetry import setup_telemetry
from app.modules.application_prep.router import router as application_prep_router
from app.modules.company_research.router import router as company_research_router
from app.modules.ingestion.router import router as ingestion_router
from app.modules.interview_prep.router import router as interview_prep_router
from app.modules.matching.router import router as matching_router
from app.modules.orchestration.router import router as orchestration_router
from app.modules.profile.router import router as profile_router
from app.modules.workspace.router import router as workspace_router

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="switch-jobs-engine",
    version="0.1.0",
    description=(
        "AI-assisted job switch workflow: self preparation, job sourcing, "
        "company research, matching, workspace review, application tailoring "
        "and interview prep - with an explicit human approval gate before any "
        "application is marked submitted."
    ),
)

app.include_router(profile_router)
app.include_router(ingestion_router)
app.include_router(company_research_router)
app.include_router(matching_router)
app.include_router(workspace_router)
app.include_router(application_prep_router)
app.include_router(interview_prep_router)
app.include_router(orchestration_router)

setup_telemetry(app, settings)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "storage_backend": settings.storage_backend,
        "llm_offline": settings.llm_offline,
    }


@app.get("/")
def root() -> dict:
    return {
        "name": "switch-jobs-engine",
        "docs": "/docs",
        "health": "/health",
        "modules": [
            "profile", "jobs", "companies", "match", "workspace",
            "applications", "interview", "orchestration",
        ],
    }
