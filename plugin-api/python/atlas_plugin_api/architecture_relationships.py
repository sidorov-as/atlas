"""Architecture Relationship contract (`core-plugin-contract-surface` spec:
"Core publishes its plugin-facing surface as contract types").

Stands in for `server.apps.catalog.models.architecture_relationship` — a
declared, directed architecture interaction between catalog entities,
authored manually or by ingestion, never regenerated from entity
specifications (unlike `Relation`, see `relations.py`). Like `CatalogEntity`
(catalog.py's docstring), the concrete Django model can't move here, so this
publishes a `get_architecture_relationship_model()` runtime accessor plus the
`origin` values as plain constants, needing no import of the target class at
all.

Manual relationship list/create/update/delete is published as
`ArchitectureRelationshipService`, a `Protocol` Core implements and registers
through `bind_architecture_relationship_service()` from its own
`register_runtime()` hook (the same slot pattern as `entity_service.py`), so a
plugin reaches it through `get_architecture_relationship_service()` without
importing `server`. Core's REST controllers call the same singleton.
"""

from typing import Any, Protocol, runtime_checkable

from django.apps import apps as _django_apps

ARCHITECTURE_RELATIONSHIP_LABEL = "catalog.ArchitectureRelationship"

ARCHITECTURE_RELATIONSHIP_ORIGIN_MANUAL = "manual"
ARCHITECTURE_RELATIONSHIP_ORIGIN_YAML = "yaml"


class ArchitectureRelationshipNotFoundError(LookupError):
    """No `ArchitectureRelationship` exists for the given id."""


class ArchitectureRelationshipReadOnlyError(PermissionError):
    """The relationship is YAML-origin: ingestion owns it, so manual
    update/delete is rejected."""


class ArchitectureRelationshipSourceKindError(ValueError):
    """The source entity's kind cannot own manual relationships (only
    System, Component, Resource, and API can)."""


@runtime_checkable
class ArchitectureRelationshipService(Protocol):
    """Structural type for Core's manual Architecture Relationship service.

    Every method takes the acting user (`actor`) and enforces write
    permission on the relationship's source entity. `create` raises
    `ArchitectureRelationshipSourceKindError` for a non-writable source kind
    and `RefError` (`atlas_plugin_api.refs`) for an unresolvable source or
    target ref; `update`/`delete` raise
    `ArchitectureRelationshipNotFoundError` and, for a YAML-origin row,
    `ArchitectureRelationshipReadOnlyError`. Permission denial surfaces as
    the same 403 `APIError` `EntityService` raises.
    """

    def get(self, relationship_id: int) -> Any: ...

    def list_for_entity(self, *, entity_ref: str) -> list[Any]: ...

    def create(
        self,
        *,
        source_ref: str,
        target_ref: str,
        label: str,
        technology: str = "",
        interaction_kind: str = "manual",
        tags: list[str] | None = None,
        actor: Any,
    ) -> Any: ...

    def update(
        self,
        *,
        relationship_id: int,
        fields: dict[str, Any],
        actor: Any,
    ) -> Any: ...

    def delete(self, *, relationship_id: int, actor: Any) -> None: ...


_architecture_relationship_service: ArchitectureRelationshipService | None = None


def bind_architecture_relationship_service(
    service: ArchitectureRelationshipService,
) -> None:
    """Core-only: register the real service singleton. Called once from
    `server.apps.catalog.plugin.register_runtime()`."""
    global _architecture_relationship_service
    _architecture_relationship_service = service


def get_architecture_relationship_service() -> ArchitectureRelationshipService:
    """Return the singleton Core registered. Call from a function body, never
    at plugin import time."""
    if _architecture_relationship_service is None:
        msg = (
            "get_architecture_relationship_service() called before Core "
            "registered its service (server.apps.catalog.plugin."
            "register_runtime() must run first)"
        )
        raise RuntimeError(msg)
    return _architecture_relationship_service


def get_architecture_relationship_model() -> type:
    """Resolve Core's concrete `ArchitectureRelationship` model via Django's
    app registry, the same lazy-resolution mechanism
    `get_catalog_entity_model()` uses. Only callable after `django.setup()` —
    from inside a function body, never cached at plugin module import time.
    """
    return _django_apps.get_model(ARCHITECTURE_RELATIONSHIP_LABEL)
