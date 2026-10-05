"""Static plugin descriptor for the search plugin.

Optional in every distribution: when it is not selected there is no search
API, no signal receiver, no pending-change table writes and no scheduled job.
It depends on no concrete engine; exactly one registered engine adapter is
chosen at startup (`finalize_runtime`, see below).

Hooks, all called by core's runtime phases after `django.setup()`:

- `register_runtime()` binds the configuration, registers the status
  permission and connects the model-change receivers. Other plugins' sources
  and engines may not be registered yet at that point.
- `finalize_runtime()` runs after every plugin's `register_runtime()`, picks
  the engine and fails startup when none or an ambiguous choice is found.
- `register_jobs()` contributes the drain, rebuild and initial-rebuild jobs
  to the core scheduler.
"""

import logging
from typing import TYPE_CHECKING

from atlas_plugin_api import PluginDescriptor

from .config import SearchPluginConfig
from .job_ids import DRAIN_JOB_ID, INITIAL_REBUILD_JOB_ID, REBUILD_JOB_ID

if TYPE_CHECKING:
    from apscheduler.schedulers.base import BaseScheduler

logger = logging.getLogger(__name__)

PLUGIN = PluginDescriptor(
    id="atlas.search",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_search",),
    entry_point="atlas_plugin_search.plugin:PLUGIN",
    job_ids=(DRAIN_JOB_ID, REBUILD_JOB_ID, INITIAL_REBUILD_JOB_ID),
    config_schema=SearchPluginConfig,
)

STATUS_ADMIN_PERMISSION = "atlas.search.status.admin"
"""Held by administrators only (the built-in evaluator grants it to
superusers); it unlocks the full detail of the status endpoint. A read
permission by effect: viewing status changes nothing."""


def register_runtime() -> None:
    from atlas_plugin_api import (
        configure_search_body_limit,
        get_plugin_config,
        register_permission,
    )

    from . import runtime, signals

    try:
        config = get_plugin_config(PLUGIN.id, SearchPluginConfig)
    except LookupError:
        config = SearchPluginConfig()
    runtime.configure(config)
    configure_search_body_limit(config.max_body_chars)
    register_permission(STATUS_ADMIN_PERMISSION, owner=PLUGIN.id, effect="read")
    signals.connect()


def finalize_runtime() -> None:
    """Choose the engine; raises `SearchEngineSelectionError` to stop startup."""
    from atlas_plugin_api import get_search_engine_lookup, select_search_engine

    from . import runtime

    engine = select_search_engine(
        get_search_engine_lookup(), runtime.get_config().engine
    )
    runtime.bind_engine(engine)
    logger.info("Search is using engine %r", engine.id)


def register_jobs(scheduler: "BaseScheduler") -> None:
    """Register the drain and rebuild jobs and the one-off initial rebuild.

    The initial rebuild runs once when the scheduler starts and does nothing
    unless the engine is empty while the sources are not.
    """
    from apscheduler.triggers.date import DateTrigger
    from atlas_plugin_api import add_interval_job
    from django_apscheduler.util import close_old_connections

    from . import runtime
    from .jobs import drain_job, initial_rebuild_job, rebuild_job

    config = runtime.get_config()
    add_interval_job(
        scheduler,
        drain_job,
        job_id=DRAIN_JOB_ID,
        seconds=config.drain_interval_seconds,
    )
    add_interval_job(
        scheduler,
        rebuild_job,
        job_id=REBUILD_JOB_ID,
        seconds=config.rebuild_interval_seconds,
    )
    scheduler.add_job(
        close_old_connections(initial_rebuild_job),
        trigger=DateTrigger(),
        id=INITIAL_REBUILD_JOB_ID,
        replace_existing=True,
        max_instances=1,
    )
