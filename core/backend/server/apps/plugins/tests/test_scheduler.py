"""Core scheduler tests: hook discovery, declared-id validation, job state
following plugin enablement, and per-job isolation."""

import threading
import time

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from atlas_plugin_api import add_interval_job

from server.apps.plugins.resolver import load_selected_descriptors
from server.apps.plugins.runtime import load_runtime_entry_points
from server.apps.plugins.scheduler import (
    UndeclaredJobError,
    build_scheduler,
    register_plugin_jobs,
)
from server.apps.plugins.tests.fixtures import plugin_with_jobs

FIXTURES = "server.apps.plugins.tests.fixtures"


def _descriptors(*names: str):
    return load_selected_descriptors(
        tuple(f"{FIXTURES}.{name}" for name in names)
    )


def _job_ids(scheduler) -> set[str]:
    return {job.id for job in scheduler.get_jobs()}


# 4.1 Hook discovery


def test_active_plugin_hook_is_called_once_and_registers_its_jobs():
    plugin_with_jobs.hook_calls.clear()
    scheduler = BackgroundScheduler()

    register_plugin_jobs(scheduler, _descriptors("plugin_with_jobs"))

    assert plugin_with_jobs.hook_calls == ["fixture.with-jobs"]
    assert _job_ids(scheduler) == {plugin_with_jobs.JOB_ID}


def test_plugin_without_the_hook_is_skipped():
    scheduler = BackgroundScheduler()

    register_plugin_jobs(
        scheduler, _descriptors("plugin_no_hook", "plugin_with_hook")
    )

    assert _job_ids(scheduler) == set()


def test_disabled_plugin_hook_is_not_called():
    plugin_with_jobs.hook_calls.clear()
    scheduler = BackgroundScheduler()

    register_plugin_jobs(
        scheduler,
        _descriptors("plugin_with_jobs"),
        disabled_ids=frozenset({"fixture.with-jobs"}),
    )

    assert plugin_with_jobs.hook_calls == []
    assert _job_ids(scheduler) == set()


def test_no_plugins_registers_nothing():
    scheduler = BackgroundScheduler()

    register_plugin_jobs(scheduler, ())

    assert _job_ids(scheduler) == set()


# 4.2 Undeclared job id


def test_undeclared_job_id_fails_naming_the_plugin_and_id():
    scheduler = BackgroundScheduler()

    with pytest.raises(UndeclaredJobError) as excinfo:
        register_plugin_jobs(scheduler, _descriptors("plugin_undeclared_job"))

    assert excinfo.value.plugin_id == "fixture.undeclared-job"
    assert excinfo.value.job_ids == ("fixture.undeclared-job.rogue",)
    assert "fixture.undeclared-job" in str(excinfo.value)
    assert "fixture.undeclared-job.rogue" in str(excinfo.value)


# 4.3 Pause on disable, resume on enable, with the core scheduler


@pytest.mark.django_db
class TestJobStateFollowsEnablement:
    @pytest.fixture
    def scheduler(self):
        scheduler = build_scheduler()
        register_plugin_jobs(scheduler, _descriptors("plugin_with_jobs"))
        # `start(paused=True)` flushes the pending job to the DB job store
        # without letting it run.
        scheduler.start(paused=True)
        yield scheduler
        scheduler.remove_job(plugin_with_jobs.JOB_ID)
        scheduler.shutdown(wait=False)

    @staticmethod
    def _is_paused() -> bool:
        from django_apscheduler.models import DjangoJob

        return (
            DjangoJob.objects.get(id=plugin_with_jobs.JOB_ID).next_run_time
            is None
        )

    def test_disabling_pauses_the_job(self, scheduler):
        load_runtime_entry_points(
            _descriptors("plugin_with_jobs"),
            disabled_ids=frozenset({"fixture.with-jobs"}),
        )

        assert self._is_paused()

    def test_enabling_resumes_the_job(self, scheduler):
        scheduler.pause_job(plugin_with_jobs.JOB_ID)
        assert self._is_paused()

        load_runtime_entry_points(_descriptors("plugin_with_jobs"))

        assert not self._is_paused()


# 4.4 Isolation between jobs

_state = {"started": 0, "good_runs": 0}
_release = threading.Event()


def _raising_job() -> None:
    raise RuntimeError("job failure that must stay contained")


def _good_job() -> None:
    _state["good_runs"] += 1


def _slow_job() -> None:
    _state["started"] += 1
    _release.wait(timeout=10)


def _wait_for(condition, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def running_scheduler():
    _state.update(started=0, good_runs=0)
    _release.clear()
    scheduler = BackgroundScheduler()
    yield scheduler
    _release.set()
    scheduler.shutdown(wait=False)


def test_a_raising_job_does_not_stop_other_jobs_or_itself(running_scheduler):
    add_interval_job(
        running_scheduler, _raising_job, job_id="raising", seconds=1
    )
    add_interval_job(running_scheduler, _good_job, job_id="good", seconds=1)
    running_scheduler.start()

    assert _wait_for(lambda: _state["good_runs"] >= 2, timeout=6)
    assert {"raising", "good"} <= _job_ids(running_scheduler)


def test_an_overlapping_run_is_skipped(running_scheduler):
    add_interval_job(running_scheduler, _slow_job, job_id="slow", seconds=1)
    running_scheduler.start()

    assert _wait_for(lambda: _state["started"] >= 1, timeout=4)
    time.sleep(
        2.5
    )  # at least two more triggers fire while the first run blocks

    assert _state["started"] == 1
