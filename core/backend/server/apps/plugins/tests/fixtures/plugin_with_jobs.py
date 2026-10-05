"""Fixture plugin contributing one scheduled job through `register_jobs`."""

from atlas_plugin_api import PluginDescriptor, add_interval_job

JOB_ID = "fixture.with-jobs.tick"

PLUGIN = PluginDescriptor(
    id="fixture.with-jobs",
    version="0.0.0",
    compatibility={},
    django_apps=(),
    entry_point="server.apps.plugins.tests.fixtures.plugin_with_jobs:PLUGIN",
    job_ids=(JOB_ID,),
)

hook_calls: list[str] = []


def tick() -> None:
    """Module-level so APScheduler can reference it textually."""


def register_jobs(scheduler) -> None:
    hook_calls.append(PLUGIN.id)
    add_interval_job(scheduler, tick, job_id=JOB_ID, seconds=3600)
