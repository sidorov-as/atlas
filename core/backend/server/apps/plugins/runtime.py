"""Runtime entry-point loading phase (including disabled-plugin handling).

Runs after `django.setup()`: for each selected plugin not in
`disabled_ids`, imports the module named by its static descriptor's
`entry_point` and calls that module's `register_runtime()` hook, if
present, to populate the capability, permission, and Entity Kind
registries (plugin-architecture.md:395-396), or — for a plugin that owns
its own extension points, like `atlas_plugin_ingestion` registering
against `atlas.ingestion.connectors.v1`/`atlas.ingestion.parsers.v1`
(ADR 0014) — a registry it owns itself. A plugin with nothing to register
at runtime (`server.apps.catalog` today) simply omits the hook.

A plugin in `disabled_ids` skips `register_runtime()` entirely (its
Django app still installed `INSTALLED_APPS`-side, per
`resolver.resolve_installed_apps`, so its migrations still apply — only
this registration step is skipped) and has any `django-apscheduler` job
ids it declared (`PluginDescriptor.job_ids`) paused; an active plugin's
job ids are resumed the same way, syncing job-pause state to the manifest
on every process start (disabled means not
contributing, and a background job silently writing data nobody can see
or act on would be a surprising exception to that).

This module — unlike `descriptor.py`/`resolver.py` — is safe to import
Django models from, since it only ever runs from `PluginsConfig.ready()`,
after `django.setup()` has completed.
"""

from collections.abc import Iterable
from importlib import import_module

from atlas_plugin_api import PluginDescriptor


def load_runtime_entry_points(
    descriptors: Iterable[PluginDescriptor],
    *,
    disabled_ids: frozenset[str] = frozenset(),
) -> None:
    descriptors = tuple(descriptors)
    job_store = _job_store_if_needed(descriptors)

    for descriptor in descriptors:
        if descriptor.id in disabled_ids:
            _sync_jobs(job_store, descriptor.job_ids, pause=True)
            continue
        module_path, _sep, _attr = descriptor.entry_point.partition(":")
        module = import_module(module_path)
        register_runtime = getattr(module, "register_runtime", None)
        if register_runtime is not None:
            register_runtime()
        _sync_jobs(job_store, descriptor.job_ids, pause=False)


def _job_store_if_needed(descriptors: Iterable[PluginDescriptor]):
    """The shared `django-apscheduler` DB-backed job store — used below to
    pause/resume jobs by id directly (not via `BaseScheduler.pause_job`/
    `resume_job`: those only consult a job store once the scheduler
    instance itself has been started, which would mean starting a
    `BackgroundScheduler` — spawning a real thread — just to toggle two
    database rows; `DjangoJobStore.lookup_job`/`update_job` are plain DB
    reads/writes that don't need that).

    Built only if some descriptor actually declares `job_ids`:
    `django_apscheduler` is only guaranteed importable when a plugin that
    uses it (`atlas.ingestion`) is selected, since it reaches
    `INSTALLED_APPS` only via that plugin's own `django_apps` (plugin.py's
    docstring) — a distribution without it must not need this import to
    succeed.
    """
    if not any(descriptor.job_ids for descriptor in descriptors):
        return None
    from django_apscheduler.jobstores import DjangoJobStore

    return DjangoJobStore()


def _sync_jobs(
    job_store: object,
    job_ids: Iterable[str],
    *,
    pause: bool,
) -> None:
    """Best-effort: a job id not yet registered (a fresh deployment before
    the scheduler process has ever run `register_jobs`) or a
    `django_apscheduler` table that doesn't exist yet (this phase also runs
    during `manage.py migrate` itself, before its own migrations apply)
    both silently no-op rather than failing startup — see scheduler.py's
    docstring: a pause/resume made from any process "takes effect the next
    time the process actually running this scheduler ... wakes up".
    """
    if job_store is None:
        return
    from datetime import UTC, datetime

    from apscheduler.jobstores.base import JobLookupError
    from django.db import DatabaseError

    for job_id in job_ids:
        try:
            job = job_store.lookup_job(job_id)
            if job is None:
                continue
            if pause:
                job.next_run_time = None
            else:
                job.next_run_time = job.trigger.get_next_fire_time(
                    None,
                    datetime.now(UTC),
                )
                if job.next_run_time is None:
                    continue
            job_store.update_job(job)
        except (JobLookupError, DatabaseError):
            pass
