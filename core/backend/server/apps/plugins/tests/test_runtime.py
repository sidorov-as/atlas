"""Runtime entry-point loading phase tests (including
disabled-plugin/job pause-resume tests)."""

import pytest
from atlas_plugin_api import PluginDescriptor

from server.apps.plugins.resolver import load_selected_descriptors
from server.apps.plugins.runtime import load_runtime_entry_points
from server.apps.plugins.tests.fixtures import (
    plugin_with_finalize,
    plugin_with_hook,
)


def _noop_job() -> None:
    """A module-level function so `django-apscheduler` can serialize a
    textual reference to it (a lambda's reference can't be resolved)."""


def test_load_runtime_entry_points_calls_register_runtime_when_present():
    plugin_with_hook.runtime_calls.clear()
    descriptors = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_with_hook",)
    )

    load_runtime_entry_points(descriptors)

    assert plugin_with_hook.runtime_calls == ["fixture.with-hook"]


def test_finalize_runtime_runs_after_every_register_runtime():
    plugin_with_finalize.calls.clear()
    plugin_with_hook.runtime_calls.clear()
    descriptors = load_selected_descriptors(
        (
            "server.apps.plugins.tests.fixtures.plugin_with_finalize",
            "server.apps.plugins.tests.fixtures.plugin_with_hook",
        )
    )

    load_runtime_entry_points(descriptors)

    assert plugin_with_finalize.calls == ["register", "finalize"]
    assert plugin_with_finalize.finalized_after_all_registered is True


def test_finalize_runtime_is_skipped_for_disabled_plugin():
    plugin_with_finalize.calls.clear()
    descriptors = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_with_finalize",)
    )

    load_runtime_entry_points(
        descriptors, disabled_ids=frozenset({"fixture.with-finalize"})
    )

    assert plugin_with_finalize.calls == []


def test_finalize_runtime_failure_stops_loading():
    plugin_with_finalize.calls.clear()
    descriptors = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_with_finalize",)
    )
    plugin_with_finalize.fail = True
    try:
        with pytest.raises(RuntimeError, match="finalize failed"):
            load_runtime_entry_points(descriptors)
    finally:
        plugin_with_finalize.fail = False


def test_load_runtime_entry_points_skips_a_plugin_without_the_hook():
    descriptors = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_no_hook",)
    )

    load_runtime_entry_points(descriptors)  # must not raise


def test_load_runtime_entry_points_skips_register_runtime_for_disabled():
    plugin_with_hook.runtime_calls.clear()
    descriptors = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_with_hook",)
    )

    load_runtime_entry_points(
        descriptors,
        disabled_ids=frozenset({"fixture.with-hook"}),
    )

    assert plugin_with_hook.runtime_calls == []


def test_load_runtime_entry_points_still_runs_a_non_disabled_plugin():
    plugin_with_hook.runtime_calls.clear()
    descriptors = load_selected_descriptors(
        (
            "server.apps.plugins.tests.fixtures.plugin_with_hook",
            "server.apps.plugins.tests.fixtures.plugin_no_hook",
        )
    )

    load_runtime_entry_points(
        descriptors,
        disabled_ids=frozenset({"fixture.no-hook"}),
    )

    assert plugin_with_hook.runtime_calls == ["fixture.with-hook"]


@pytest.mark.django_db
class TestJobPauseResume:
    """A disabled plugin's `django-apscheduler` job ids are paused; an
    active plugin's are resumed. Uses a real job
    registered against the shared DB job store (`django_apscheduler` is
    installed in this test session's real distribution, via
    `atlas.ingestion`), not a mock, since the pause/resume state this
    verifies lives in that table."""

    JOB_ID = "fixture.job-pause-resume"

    @pytest.fixture(autouse=True)
    def _job(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from django_apscheduler.jobstores import DjangoJobStore

        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")
        scheduler.add_job(
            _noop_job,
            trigger=IntervalTrigger(seconds=3600),
            id=self.JOB_ID,
            replace_existing=True,
        )
        # `add_job` before `start()` only queues the job in-memory (logged
        # "Adding job tentatively") — `start(paused=True)` is what actually
        # flushes it to the DB-backed job store this test asserts against,
        # without letting the (very-long-interval, so harmless either way)
        # job actually run.
        scheduler.start(paused=True)
        yield scheduler
        scheduler.remove_job(self.JOB_ID)
        scheduler.shutdown(wait=False)

    def _descriptor(self, *, entry_point: str) -> PluginDescriptor:
        return PluginDescriptor(
            id="fixture.with-job",
            version="0.0.0",
            compatibility={},
            django_apps=(),
            entry_point=entry_point,
            job_ids=(self.JOB_ID,),
        )

    def _is_paused(self, scheduler) -> bool:
        from django_apscheduler.models import DjangoJob

        # `scheduler.get_job(...)` reflects the in-process, never-started
        # `BackgroundScheduler`'s own tentative state, not the persisted
        # pause flag `pause_job`/`resume_job` actually write — read the
        # `DjangoJobStore`'s row directly, the same thing a second process
        # (the real `ingestor` service) would see.
        return DjangoJob.objects.get(id=self.JOB_ID).next_run_time is None

    def test_disabling_pauses_its_job(self, _job):
        descriptor = self._descriptor(
            entry_point="server.apps.plugins.tests.fixtures.plugin_no_hook:PLUGIN",
        )

        load_runtime_entry_points(
            (descriptor,),
            disabled_ids=frozenset({descriptor.id}),
        )

        assert self._is_paused(_job)

    def test_reenabling_resumes_its_job(self, _job):
        _job.pause_job(self.JOB_ID)
        descriptor = self._descriptor(
            entry_point="server.apps.plugins.tests.fixtures.plugin_no_hook:PLUGIN",
        )

        load_runtime_entry_points((descriptor,))  # nothing disabled

        assert not self._is_paused(_job)

    def test_pausing_an_unregistered_job_id_does_not_raise(self):
        descriptor = PluginDescriptor(
            id="fixture.with-unregistered-job",
            version="0.0.0",
            compatibility={},
            django_apps=(),
            entry_point="server.apps.plugins.tests.fixtures.plugin_no_hook:PLUGIN",
            job_ids=("fixture.never-registered",),
        )

        load_runtime_entry_points(
            (descriptor,),
            disabled_ids=frozenset({descriptor.id}),
        )  # must not raise
