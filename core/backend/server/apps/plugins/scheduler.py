"""The platform scheduler: one APScheduler process for every selected plugin.

`build_scheduler()` wires an APScheduler `BackgroundScheduler` to
`django-apscheduler`'s DB-backed `DjangoJobStore`. `register_plugin_jobs()`
then calls each active plugin's `register_jobs(scheduler)` hook (the
contract documented in `atlas_plugin_api.jobs`), found the same way
`runtime.py` finds `register_runtime()`: import the module named by the
descriptor's `entry_point` and `getattr` the hook. A plugin without the hook
registers nothing; a disabled plugin's hook is never called (its declared
job ids are paused by `runtime.py`).

Job state lives in the database, so a pause/resume made from any process
(e.g. the web process handling a plugin-disable action) takes effect the
next time the process running this scheduler (`runapscheduler`) wakes up.
Run exactly one scheduler process per deployment: the DB job store gives no
leader election.

Importing this module is safe before `django.setup()`; `django_apscheduler`
is imported only inside `build_scheduler()`.
"""

from collections.abc import Iterable
from importlib import import_module

from apscheduler.schedulers.background import BackgroundScheduler
from atlas_plugin_api import JOB_REGISTRATION_HOOK, PluginDescriptor


class UndeclaredJobError(Exception):
    """A plugin's `register_jobs` hook registered job ids that its
    descriptor's `job_ids` does not declare."""

    def __init__(self, plugin_id: str, job_ids: Iterable[str]) -> None:
        self.plugin_id = plugin_id
        self.job_ids = tuple(sorted(job_ids))
        super().__init__(
            f"plugin {plugin_id!r} registered job id(s) "
            f"{', '.join(repr(i) for i in self.job_ids)} not declared in its "
            "descriptor's job_ids"
        )


def build_scheduler() -> BackgroundScheduler:
    """A scheduler wired to the shared DB-backed job store, no jobs yet."""
    from django_apscheduler.jobstores import DjangoJobStore

    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    return scheduler


def register_plugin_jobs(
    scheduler: BackgroundScheduler,
    descriptors: Iterable[PluginDescriptor],
    *,
    disabled_ids: frozenset[str] = frozenset(),
) -> None:
    """Call `register_jobs(scheduler)` on every active plugin that has it.

    Must run before `scheduler.start()`: the job ids a hook added are
    read back from the scheduler's pending jobs. Raises
    `UndeclaredJobError` naming the plugin if a hook adds an id missing from
    its descriptor's `job_ids`.
    """
    for descriptor in descriptors:
        if descriptor.id in disabled_ids:
            continue
        module_path, _sep, _attr = descriptor.entry_point.partition(":")
        hook = getattr(import_module(module_path), JOB_REGISTRATION_HOOK, None)
        if hook is None:
            continue
        before = {job.id for job in scheduler.get_jobs()}
        hook(scheduler)
        added = {job.id for job in scheduler.get_jobs()} - before
        undeclared = added - set(descriptor.job_ids)
        if undeclared:
            raise UndeclaredJobError(descriptor.id, undeclared)
