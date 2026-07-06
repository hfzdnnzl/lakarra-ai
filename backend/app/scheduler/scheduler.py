"""Scheduler skeleton.

Phase 1 provides the structure for scheduled workflow execution (e.g. the morning
priorities run) without a live background loop. Jobs are declared as data; a real
scheduler (APScheduler, Celery beat, cron) can drive :meth:`trigger` in Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..workflows import run_workflow


@dataclass
class ScheduledJob:
    """A workflow scheduled to run on a cron/interval expression."""

    name: str
    workflow: str
    schedule: str  # cron expression or interval descriptor
    enabled: bool = True


class Scheduler:
    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}

    def add_job(self, job: ScheduledJob) -> ScheduledJob:
        self._jobs[job.name] = job
        return job

    def jobs(self) -> list[ScheduledJob]:
        return list(self._jobs.values())

    def trigger(self, name: str) -> dict:
        """Manually trigger a scheduled job's workflow (used by tests/ops)."""

        job = self._jobs.get(name)
        if job is None:
            raise ValueError(f"Unknown scheduled job: {name}")
        return dict(run_workflow(job.workflow, {"trigger": "scheduler", "job": name}))


#: Process-wide scheduler seeded with the example morning run.
scheduler = Scheduler()
scheduler.add_job(
    ScheduledJob(name="morning_priorities", workflow="daily_priorities", schedule="0 8 * * *")
)
