"""`register_jobs`: the ingestion plugin's contribution to the core scheduler."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.test import override_settings

from atlas_plugin_ingestion.job_ids import DISCOVERY_JOB_ID, SPEC_REFRESH_JOB_ID
from atlas_plugin_ingestion.plugin import PLUGIN, register_jobs


def test_registers_discovery_and_spec_refresh_under_the_declared_ids():
    scheduler = BackgroundScheduler()

    with override_settings(INGESTOR_POLL_INTERVAL=45):
        register_jobs(scheduler)

    jobs = {job.id: job for job in scheduler.get_jobs()}
    assert set(jobs) == {DISCOVERY_JOB_ID, SPEC_REFRESH_JOB_ID}
    assert set(jobs) == set(PLUGIN.job_ids)
    for job in jobs.values():
        assert isinstance(job.trigger, IntervalTrigger)
        assert job.trigger.interval.total_seconds() == 45
        assert job.max_instances == 1


def test_jobs_run_the_same_functions_as_the_one_off_command():
    from atlas_plugin_ingestion.pipeline import refresh_spec_urls, run_ingestion_pass

    scheduler = BackgroundScheduler()
    register_jobs(scheduler)

    names = {job.id: job.name for job in scheduler.get_jobs()}
    assert names[DISCOVERY_JOB_ID] == run_ingestion_pass.__name__
    assert names[SPEC_REFRESH_JOB_ID] == refresh_spec_urls.__name__
