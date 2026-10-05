"""Static plugin descriptor for the ingestion plugin.

`RegisteredRepository`, the conflict-record models, `GitConnector`, and
manifest parsing/upsert live here, split out of `server.apps.ingestion`

Optional in the official distribution, like `atlas.apis`: omitting it from
`SELECTED_PLUGINS` must not fail composition — it's absent from
`server.apps.plugins.composition.REQUIRED_PLUGINS`. It declares a manifest
dependency on `atlas.standard-catalog` (ingestion must be able to intend
entities of any registered kind), checked by
`server.apps.plugins.composition._check_plugin_dependencies`.

Its periodic jobs run on the core scheduler (`runapscheduler`) through
`register_jobs()` below; the scheduler's `django_apscheduler` app is core's.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from atlas_plugin_api import PluginDescriptor

from .config import IngestionPluginConfig, SourceConfig
from .job_ids import DISCOVERY_JOB_ID, SPEC_REFRESH_JOB_ID

if TYPE_CHECKING:
    from apscheduler.schedulers.base import BaseScheduler

    from .connectors.git import GitConnector

PLUGIN = PluginDescriptor(
    id="atlas.ingestion",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_ingestion",),
    entry_point="atlas_plugin_ingestion.plugin:PLUGIN",
    requires_plugins={"atlas.standard-catalog": ">=0.1 <1"},
    job_ids=(DISCOVERY_JOB_ID, SPEC_REFRESH_JOB_ID),
    config_schema=IngestionPluginConfig,
)


def register_runtime() -> None:
    """Register a `GitConnector` factory per configured source, and the YAML
    parser, against this plugin's own extension points.

    Called by the shared "load selected runtime entry points" phase
    (`server.apps.plugins.runtime.load_runtime_entry_points`), after
    `django.setup()` — never at import time. Unlike a core-owned registry
    (`EntityKindRegistry`, `CapabilityRegistry`),
    `atlas.ingestion.connectors.v1`/`atlas.ingestion.parsers.v1` are owned
    by this plugin itself (ADR 0014), so the registries live in
    `.extension_points` rather than `server.apps.plugins`.

    Registers a zero-argument *factory* under each source's `id`, not a
    live `GitConnector` instance: `connectors/git.py`'s "Clone lifecycle"
    is one clone per repository per pass, so `pipeline.py` constructs (and
    closes) a fresh connector per repository rather than reusing one
    long-lived instance across every scheduled pass — a long-lived instance
    would otherwise accumulate one cached checkout (and its temporary
    directory) per repository forever, since `RegisteredRepository.objects.
    all()` yields new Python objects on every pass.

    Config defaults to zero sources (`IngestionPluginConfig`'s own default)
    when `atlas.ingestion` has no resolved config bound at all — a
    deployment that hasn't declared any `sources` yet, or hasn't declared an
    `atlas.ingestion` config block in its manifest, still composes cleanly;
    any `RegisteredRepository` referencing an unresolved `source_id` is
    reported as a clear per-repository error at ingestion time instead
    (`pipeline.run_ingestion_pass`), not a startup failure.
    """
    from atlas_plugin_api import get_plugin_config

    from .extension_points import connectors, parsers
    from .parsing import PARSER_ID, CatalogInfoYamlParser

    try:
        config = get_plugin_config(PLUGIN.id, IngestionPluginConfig)
    except LookupError:
        config = IngestionPluginConfig()

    for source in config.sources:
        connectors.register(source.id, _git_connector_factory(source))
    parsers.register(PARSER_ID, CatalogInfoYamlParser())


def register_jobs(scheduler: "BaseScheduler") -> None:
    """Register the discovery-run and spec-refresh jobs on
    `INGESTOR_POLL_INTERVAL`-second triggers (the `atlas_plugin_api.jobs`
    hook, called by core's `runapscheduler` for an active plugin).

    The spec refresh is conceptually `atlas.apis`'s own concern, but is
    scheduled here since this is where the periodic jobs were introduced.
    """
    from atlas_plugin_api import add_interval_job
    from django.conf import settings

    from .pipeline import refresh_spec_urls, run_ingestion_pass

    interval = settings.INGESTOR_POLL_INTERVAL
    add_interval_job(
        scheduler, run_ingestion_pass, job_id=DISCOVERY_JOB_ID, seconds=interval
    )
    add_interval_job(
        scheduler, refresh_spec_urls, job_id=SPEC_REFRESH_JOB_ID, seconds=interval
    )


def _git_connector_factory(source: SourceConfig) -> Callable[[], "GitConnector"]:
    from .connectors.git import GitConnector, SourceConnection

    connection = SourceConnection(
        base_url=source.base_url,
        auth_kind=source.auth_kind,
        credential=source.credential,
        known_hosts=source.known_hosts,
        accept_unknown_host_keys=source.accept_unknown_host_keys,
    )
    return lambda: GitConnector(connection)
