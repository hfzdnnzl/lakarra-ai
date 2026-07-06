"""API route aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from . import (
    agents,
    analytics,
    approvals,
    content,
    health,
    logs,
    reports,
    tasks,
    workflows,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agents.router)
api_router.include_router(tasks.router)
api_router.include_router(reports.router)
api_router.include_router(content.router)
api_router.include_router(approvals.router)
api_router.include_router(analytics.router)
api_router.include_router(logs.router)
api_router.include_router(workflows.router)

__all__ = ["api_router"]
