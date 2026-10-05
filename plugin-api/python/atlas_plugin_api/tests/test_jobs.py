"""Scheduled-job contribution helper tests."""

import pytest

pytest.importorskip("django_apscheduler")

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from atlas_plugin_api import JOB_REGISTRATION_HOOK, add_interval_job


def _job_body() -> None:
    """Module-level so APScheduler can reference it."""


def test_hook_name():
    assert JOB_REGISTRATION_HOOK == "register_jobs"


def test_add_interval_job_applies_platform_defaults():
    scheduler = BackgroundScheduler()
    scheduler.start(paused=True)  # no job runs; replace_existing needs a started store

    add_interval_job(scheduler, _job_body, job_id="fixture.job", seconds=30)
    # Registering the same id again replaces rather than raising.
    add_interval_job(scheduler, _job_body, job_id="fixture.job", seconds=60)

    try:
        (job,) = scheduler.get_jobs()
    finally:
        scheduler.shutdown(wait=False)
    assert job.id == "fixture.job"
    assert job.max_instances == 1
    assert isinstance(job.trigger, IntervalTrigger)
    assert job.trigger.interval.total_seconds() == 60
