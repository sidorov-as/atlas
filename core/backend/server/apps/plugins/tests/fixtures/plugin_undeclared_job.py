"""Fixture plugin whose hook registers a job id its descriptor omits."""

from atlas_plugin_api import PluginDescriptor, add_interval_job

PLUGIN = PluginDescriptor(
    id="fixture.undeclared-job",
    version="0.0.0",
    compatibility={},
    django_apps=(),
    entry_point="server.apps.plugins.tests.fixtures.plugin_undeclared_job:PLUGIN",
    job_ids=("fixture.undeclared-job.declared",),
)


def tick() -> None:
    """Module-level so APScheduler can reference it textually."""


def register_jobs(scheduler) -> None:
    add_interval_job(
        scheduler, tick, job_id="fixture.undeclared-job.declared", seconds=3600
    )
    add_interval_job(
        scheduler, tick, job_id="fixture.undeclared-job.rogue", seconds=3600
    )
