"""Entity read/write contract (`core-plugin-contract-surface` spec: "Core
publishes its plugin-facing surface as contract types").

Stands in for `server.apps.catalog.services.entity_service` — Core's single
authorize -> validate -> resolve -> transaction -> audit pipeline for every
Catalog Entity create/update/delete (entity-lifecycle-service spec). Unlike
`kinds.py`, the real `EntityService` can't move here outright: it does real
Django ORM work against the concrete `CatalogEntity` model, which
`atlas_plugin_api` structurally cannot import (`core/backend` is
`package-mode = false` — catalog.py's docstring). So this module publishes:

- `EntityService`, a `Protocol` describing the singleton's public interface,
  for static typing.
- `EntityRead`/`EntityNotFoundError`/`EntityUnavailableError`/
  `UnknownEntityKindError`, the plain value/exception types the interface
  uses — none need a Django model, so (like `kinds.py`'s `ValidateDeleteError`)
  they move here outright; `server.apps.catalog.services.entity_service`
  re-exports them under the same names for Core's own call sites.
- `bind_entity_service()`/`get_entity_service()`, a process-wide registration
  slot Core populates with the real singleton from its own `register_runtime()`
  hook (`server.apps.catalog.plugin`), the same "load selected runtime entry
  points" phase that populates the Entity Kind registry
  (`server.apps.plugins.runtime`) — the mirror image of `register_kind()`:
  here Core registers *into* `atlas_plugin_api`, instead of a plugin
  registering into a Core-owned registry. This is how a plugin gets hold of
  the singleton without `atlas_plugin_api` ever importing `server`.

A plugin reads or writes catalog entities from application code through
`get_entity_service()`, never by importing
`server.apps.catalog.services.entity_service` directly.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel

from .catalog import SOURCE_MANUAL, CatalogEntity


@dataclass(frozen=True)
class EntityRead:
    """One `CatalogEntity` read back out of `EntityService.get`/`.list`.

    `spec` is the kind handler's serialized kind-specific data, or `None`
    when `unavailable` is set — the entity's kind has no currently
    registered handler (unavailable-entity spec).
    """

    entity: CatalogEntity
    spec: BaseModel | None
    unavailable: bool


class EntityNotFoundError(LookupError):
    """No `CatalogEntity` exists for the given id."""


class DuplicateEntityError(ValueError):
    """An entity of this kind already has this name (names are unique per kind
    and namespace, ignoring case). Raised by `create`, and by `update` when a
    rename collides, so callers can answer with a client error instead of failing
    on the database constraint."""

    def __init__(self, kind_id: str, name: str) -> None:
        super().__init__(f"A {kind_id} named {name!r} already exists")
        self.kind_id = kind_id
        self.name = name


class UnknownEntityKindError(ValueError):
    """No `EntityKindHandler` is registered for the given `kind_id` (entity-kind-registry spec)."""

    def __init__(self, kind_id: str) -> None:
        super().__init__(f"No Entity Kind handler registered for kind_id={kind_id!r}")
        self.kind_id = kind_id


class EntityUnavailableError(UnknownEntityKindError):
    """Raised by `update`/`delete` when the target entity's kind currently has
    no registered handler: the entity is a read-only Unavailable Entity
    (unavailable-entity spec) — real and previously available, not a
    `kind_id` that was never valid. `create` raises the base
    `UnknownEntityKindError` instead, since no entity exists yet there.
    """

    def __init__(self, kind_id: str) -> None:
        ValueError.__init__(
            self,
            f"Entity kind {kind_id!r} is unavailable (no handler currently "
            f"registered); writes are rejected",
        )
        self.kind_id = kind_id


@runtime_checkable
class EntityService(Protocol):
    """Structural type for Core's `EntityService` singleton — the only code
    path allowed to create, update, or delete a `CatalogEntity`
    (entity-lifecycle-service spec). Obtained via `get_entity_service()`,
    never constructed by a plugin.
    """

    def get(self, entity_id: UUID) -> EntityRead: ...

    def list(self, *, kind_id: str | None = None) -> list[EntityRead]: ...

    def create(
        self,
        *,
        kind_id: str,
        owner_ref: str | None = None,
        metadata: BaseModel,
        spec: BaseModel,
        actor: Any,
        source: str = SOURCE_MANUAL,
    ) -> CatalogEntity: ...

    def update(
        self,
        *,
        entity_id: UUID,
        owner_ref: str | None = None,
        metadata: BaseModel | None = None,
        spec: BaseModel | None = None,
        actor: Any,
        source: str = SOURCE_MANUAL,
    ) -> CatalogEntity: ...

    def delete(self, *, entity_id: UUID, actor: Any) -> None: ...

    def remove(
        self,
        *,
        entity_id: UUID,
        actor: Any,
        source: str = SOURCE_MANUAL,
    ) -> CatalogEntity: ...

    def revive(
        self,
        *,
        entity_id: UUID,
        actor: Any,
        source: str = SOURCE_MANUAL,
    ) -> CatalogEntity: ...

    def purge(self, *, entity_id: UUID, actor: Any) -> None: ...


_entity_service: EntityService | None = None


def bind_entity_service(service: EntityService) -> None:
    """Core-only: register the real `EntityService` singleton, so
    `get_entity_service()` can hand it out without `atlas_plugin_api` ever
    importing `server`. Called once from `server.apps.catalog.plugin.
    register_runtime()`, during the shared runtime entry-point-loading
    phase (`server.apps.plugins.runtime`), before any request is served.
    """
    global _entity_service
    _entity_service = service


def get_entity_service() -> EntityService:
    """Return the process-wide `EntityService` singleton Core registered via
    `bind_entity_service()`. Only callable after that registration has run —
    from inside a function body or method, never cached at plugin module
    import time (matching `get_catalog_entity_model()`'s same caution).
    """
    if _entity_service is None:
        msg = (
            "get_entity_service() called before Core registered its EntityService "
            "singleton (server.apps.catalog.plugin.register_runtime() must run first)"
        )
        raise RuntimeError(msg)
    return _entity_service
