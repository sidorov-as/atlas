"""Scheduled-job contribution contract.

A plugin contributes periodic jobs by exposing a module-level
`register_jobs(scheduler)` hook on its entry-point module (the one named by
`PluginDescriptor.entry_point`, next to `register_runtime()`). Core's
`runapscheduler` command imports that module, calls the hook once per active
plugin with the shared APScheduler scheduler, and checks that every job id
the hook added is declared in `PluginDescriptor.job_ids`.

Importing the plugin module must not start or register anything; scheduling
happens only inside the hook. Keep imports of job bodies and of
`django_apscheduler` inside the hook, so a distribution that does not select
the plugin never imports them.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apscheduler.schedulers.base import BaseScheduler

JOB_REGISTRATION_HOOK = "register_jobs"
"""Name of the optional hook on a plugin's entry-point module."""


def add_interval_job(
    scheduler: "BaseScheduler",
    func: Callable[..., Any],
    *,
    job_id: str,
    seconds: int,
) -> None:
    """Register `func` to run every `seconds` seconds under `job_id`.

    Applies the platform defaults: the job body is wrapped in
    `django_apscheduler`'s `close_old_connections` (so a connection gone
    stale between runs in the scheduler's worker thread reconnects instead
    of raising), only one instance runs at a time (an overlapping trigger is
    skipped), and a persisted job with the same id is replaced. A plugin
    needing a different trigger or settings may call `scheduler.add_job`
    directly; the id must still be declared in `PluginDescriptor.job_ids`.
    """
    from apscheduler.triggers.interval import IntervalTrigger
    from django_apscheduler.util import close_old_connections

    scheduler.add_job(
        close_old_connections(func),
        trigger=IntervalTrigger(seconds=seconds),
        id=job_id,
        replace_existing=True,
        max_instances=1,
    )
