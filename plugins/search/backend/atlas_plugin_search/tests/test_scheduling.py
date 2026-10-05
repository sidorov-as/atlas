from datetime import UTC, datetime
from unittest.mock import MagicMock

from atlas_plugin_search import indexer, plugin, runtime
from atlas_plugin_search.config import SearchPluginConfig
from atlas_plugin_search.job_ids import (
    DRAIN_JOB_ID,
    INITIAL_REBUILD_JOB_ID,
    REBUILD_JOB_ID,
)


class _RecordingScheduler:
    def __init__(self):
        self.jobs = {}

    def add_job(self, func, trigger=None, id=None, **kwargs):
        self.jobs[id] = (func, trigger, kwargs)


def _register(scheduler):
    plugin.register_jobs(scheduler)
    return scheduler.jobs


def test_default_intervals(active):
    jobs = _register(_RecordingScheduler())

    assert set(jobs) == {DRAIN_JOB_ID, REBUILD_JOB_ID, INITIAL_REBUILD_JOB_ID}
    assert jobs[DRAIN_JOB_ID][1].interval.total_seconds() == 10
    assert jobs[REBUILD_JOB_ID][1].interval.total_seconds() == 6 * 3600
    assert set(jobs) == set(plugin.PLUGIN.job_ids)


def test_configured_intervals(activate):
    activate(SearchPluginConfig(drainIntervalSeconds=3, rebuildIntervalSeconds=90))

    jobs = _register(_RecordingScheduler())

    assert jobs[DRAIN_JOB_ID][1].interval.total_seconds() == 3
    assert jobs[REBUILD_JOB_ID][1].interval.total_seconds() == 90


def test_jobs_never_overlap_and_replace_persisted_ones(active):
    jobs = _register(_RecordingScheduler())

    for job_id in (DRAIN_JOB_ID, REBUILD_JOB_ID, INITIAL_REBUILD_JOB_ID):
        kwargs = jobs[job_id][2]
        assert kwargs["max_instances"] == 1
        assert kwargs["replace_existing"] is True


def test_initial_rebuild_is_a_one_off_job_due_now(active):
    jobs = _register(_RecordingScheduler())

    run_date = jobs[INITIAL_REBUILD_JOB_ID][1].run_date
    assert abs((run_date - datetime.now(UTC)).total_seconds()) < 5


def test_registering_jobs_works_with_a_real_scheduler(active):
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()  # not started: jobs stay pending

    plugin.register_jobs(scheduler)

    assert {job.id for job in scheduler.get_jobs()} == set(plugin.PLUGIN.job_ids)


def test_job_bodies_swallow_failures(active, engine, make_note, monkeypatch):
    from atlas_plugin_search import jobs

    make_note("alpha")
    engine.fail = True

    jobs.drain_job()  # engine down: recorded, not raised
    jobs.rebuild_job()
    jobs.initial_rebuild_job()

    monkeypatch.setattr(indexer, "drain_pending", MagicMock(side_effect=RuntimeError))
    jobs.drain_job()


def test_initial_rebuild_job_builds_an_empty_index(active, engine, make_note):
    from atlas_plugin_search import jobs

    make_note("alpha")

    jobs.initial_rebuild_job()

    assert len(engine.documents) == 1
    assert runtime.is_active()
