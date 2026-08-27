"""Plugin-owned extension points: connectors, parsers, and facet writers
(ADR 0014).

`atlas.ingestion.connectors.v1` and `atlas.ingestion.parsers.v1` are `keyed`
extension points (plugin-architecture.md's cardinality model) — keyed by
connector/parser id, so each configured source registers its own
`GitConnector` factory alongside the YAML parser without either needing to
know about the other. Registered in `plugin.register_runtime()`, during the
shared runtime entry-point-loading phase (`server.apps.plugins.runtime`).

`atlas.ingestion.facet_writers.v1` is the same shape, keyed by facet id (e.g. `'database-schema'`) — it
lets an optional facet plugin (`atlas_plugin_database_schema`) register how
to apply/clear its own Facet from a manifest-declared value, without this
plugin's core upsert path acquiring hard-coded knowledge of that facet
plugin, or of facets in general beyond this one small, generic contract.
Resolving a key with nothing registered is a reliable "that plugin isn't
selected for this distribution" signal — the same one
`connectors`/`parsers` already rely on — not an error.

Unlike the core-owned `EntityKindRegistry`/`CapabilityRegistry`
(`server.apps.plugins`), these registries live in the plugin that publishes
them (ADR 0014: "any plugin may publish namespaced, versioned extension
points for dependent plugins"). `atlas.ingestion` is currently the sole
consumer of its own `connectors`/`parsers` extension points — the pipeline resolves a `GitConnector`/the YAML parser from these
registries rather than importing and calling them by name.
"""

from typing import Protocol

from atlas_plugin_api import CatalogEntity


class DuplicateExtensionPointRegistrationError(ValueError):
    """Raised when a second implementation tries to claim a registered key."""

    def __init__(self, extension_point_id: str, key: str) -> None:
        super().__init__(
            f"{extension_point_id} already has a registration for key={key!r}",
        )
        self.extension_point_id = extension_point_id
        self.key = key


class KeyedExtensionPoint:
    """Maps a registration key to its implementation, for one keyed
    extension point id."""

    def __init__(self, extension_point_id: str) -> None:
        self.extension_point_id = extension_point_id
        self._implementations: dict[str, object] = {}

    def register(self, key: str, implementation: object) -> None:
        if key in self._implementations:
            raise DuplicateExtensionPointRegistrationError(
                self.extension_point_id,
                key,
            )
        self._implementations[key] = implementation

    def resolve(self, key: str) -> object | None:
        """Return the implementation registered for `key`, or `None`."""
        return self._implementations.get(key)

    def registered_keys(self) -> list[str]:
        """Return every registered key, sorted."""
        return sorted(self._implementations)


class FacetWriter(Protocol):
    """The `atlas.ingestion.facet_writers.v1` contract.

    `apply` is called when a Resource's manifest declares the facet's
    ingestion-only field; `clear` is called when a Resource that previously
    declared it is re-ingested without one (full-overwrite semantics, ADR
    0001). Both are called from ingestion's pipeline in a second pass after
    the Resource's own `EntityService`-mediated upsert, the same shape
    `upsert.reconcile_declared_relationships` already uses — neither
    operation goes through `EntityService`/the kind handler itself
    (a Facet write does not invoke the entity's kind
    handler).
    """

    def apply(self, entity: CatalogEntity, dialect: str, source_sql: str) -> None: ...

    def clear(self, entity: CatalogEntity) -> None: ...


connectors = KeyedExtensionPoint("atlas.ingestion.connectors.v1")
parsers = KeyedExtensionPoint("atlas.ingestion.parsers.v1")
facet_writers = KeyedExtensionPoint("atlas.ingestion.facet_writers.v1")
