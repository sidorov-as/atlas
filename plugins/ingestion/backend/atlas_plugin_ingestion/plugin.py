"""Static plugin descriptor for the ingestion plugin.

`RegisteredRepository`, the conflict-record models, `GitConnector`, and
manifest parsing/upsert live here, split out of `server.apps.ingestion`

Optional in the official distribution, like `atlas.apis`: omitting it from
`SELECTED_PLUGINS` must not fail composition — it's absent from
`server.apps.plugins.composition.REQUIRED_PLUGINS`. It declares a manifest
dependency on `atlas.standard-catalog` (ingestion must be able to intend
entities of any registered kind), checked by
`server.apps.plugins.composition._check_plugin_dependencies`.

`django_apscheduler` is listed alongside this plugin's own app — it's the
program's chosen background-job runtime, needed only
when `atlas.ingestion` (the only plugin scheduling jobs so far) is selected,
so it rides along as this plugin's own dependency rather than a core
`additional_apps` entry.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from atlas_plugin_api import PluginDescriptor

from .config import IngestionPluginConfig, SourceConfig
from .job_ids import DISCOVERY_JOB_ID, SPEC_REFRESH_JOB_ID

if TYPE_CHECKING:
    from .connectors.git import GitConnector

PLUGIN = PluginDescriptor(
    id="atlas.ingestion",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("django_apscheduler", "atlas_plugin_ingestion"),
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
