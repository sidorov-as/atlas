"""Static plugin descriptor for the Database Schema plugin.

Proves the Facet/view split (`plugin-architecture.md:165-184`, ADR 0018): the
`DatabaseSchema` Facet — its model, parser, and facet-owned CRUD endpoint —
and the ER Diagram view it backs live here, entirely new functionality with
no prior home in `server.apps.catalog`.

Optional in the official distribution, like `atlas.apis`/`atlas.c4`: a
distribution selecting `atlas.standard-catalog` but not `atlas.database-
schema` must still compose (it is an optional
plugin) — absent from `server.apps.plugins.composition.REQUIRED_PLUGINS`.
Declares a required manifest dependency on `atlas.standard-catalog`, since
the facet attaches to `Resource` entities and the `resource` kind is where
`schema.host.v1` is declared.

Registers a search source (`search_source.py`) as well as the facet writer below, but no capability, permission, or Entity Kind of its own at runtime
(`schema.host.v1` is declared by Standard Catalog's `resource` kind
handler, not by this plugin).

`register_runtime()` registers
this plugin's `DatabaseSchemaFacetWriter` against `atlas_plugin_ingestion`'s
`atlas.ingestion.facet_writers.v1` extension point, under key
`'database-schema'` — the same "only registered when actually selected"
mechanism `atlas.ingestion`'s own `connectors`/`parsers` registration already
depends on, so a distribution that selects `atlas.ingestion` and
`atlas.standard-catalog` but not `atlas.database-schema` never attempts a
Facet write, with no capability check needed.
"""

from atlas_plugin_api import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="atlas.database-schema",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_database_schema",),
    entry_point="atlas_plugin_database_schema.plugin:PLUGIN",
    requires_plugins={"atlas.standard-catalog": ">=0.1 <1"},
)


def register_runtime() -> None:
    """Register this plugin's facet-writer against `atlas_plugin_ingestion`'s
    `facet_writers` extension point.

    Called by the shared "load selected runtime entry points" phase
    (`server.apps.plugins.runtime.load_runtime_entry_points`), after
    `django.setup()` — never at import time, and only for plugins actually
    selected/composed for the distribution, exactly like `connectors`/
    `parsers` registration in `atlas_plugin_ingestion.plugin`.

    Imports `atlas_plugin_ingestion` here rather than at module level for the
    same reason `atlas_plugin_ingestion.plugin._git_connector_factory`
    imports `.connectors.git` lazily: this plugin only needs
    `atlas_plugin_ingestion` at all when it's actually registering into its
    extension point, not merely to be imported (every plugin's backend
    package is always importable regardless of selection).

    Ingestion is an optional companion, not a dependency: a distribution
    that doesn't ship `atlas_plugin_ingestion` at all has nothing to
    register into, so the facet-writer is simply skipped.
    """
    from atlas_plugin_api import register_search_source, register_upload_target

    from .search_source import database_schema_search_source
    from .upload import schema_upload_target

    # Harmless without the search plugin: nothing reads the registry then.
    register_search_source(database_schema_search_source, owner=PLUGIN.id)
    register_upload_target(schema_upload_target(), owner=PLUGIN.id)

    try:
        from atlas_plugin_ingestion.extension_points import facet_writers
    except ModuleNotFoundError as exc:
        if not (exc.name or "").startswith("atlas_plugin_ingestion"):
            raise
        return

    from .facet_writer import DatabaseSchemaFacetWriter

    # Key agreed with `atlas_plugin_ingestion.database_schema.FACET_WRITER_KEY`
    # (`atlas_plugin_ingestion.extension_points` is this plugin's only
    # declared contract surface another plugin may import — plain string,
    # not imported, to avoid reaching into its non-contract `database_schema`
    # module for a constant).
    facet_writers.register("database-schema", DatabaseSchemaFacetWriter())
