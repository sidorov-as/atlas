"""Entity Kind registration contract (`core-plugin-contract-surface` spec: "Core
publishes its plugin-facing surface as contract types").

Canonical home for the Entity Kind registry, the `EntityKindHandler` protocol,
and the capability-lookup mechanism — previously `server.apps.catalog.kinds.
{registry,handler,capability_result,capabilities}`. Unlike `CatalogEntity`
(catalog.py), none of this needs a Django model/metaclass, so it moves here
outright rather than staying in `server` behind a wrapper: `atlas_plugin_api`
owns the mechanism, and `server.apps.catalog.kinds` re-exports it for Core's
own internal call sites.

A plugin registers its Entity Kind handler through `register_kind()`, not by
reaching into a registry object directly, and resolves a kind's capabilities
through `resolve_capability()`, not by importing the registry singleton.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from .catalog import CatalogEntity

# Well-known Entity Kind capability identifiers. An
# opaque, versioned string a kind's `provides` list declares and a
# contribution targets via `entitySupports(capability)` on the frontend or
# `resolve_capability()` below on the backend, instead of naming specific
# kind ids (plugin-architecture.md:186-205).
ARCHITECTURE_SUBJECT_V1 = "architecture.subject.v1"
ARCHITECTURE_ACTOR_V1 = "architecture.actor.v1"
SCHEMA_HOST_V1 = "schema.host.v1"


@dataclass(frozen=True)
class Ok[T]:
    """The capability call succeeded, producing `value`."""

    value: T


@dataclass(frozen=True)
class Unavailable:
    """The capability's providing plugin isn't currently installed or active."""


@dataclass(frozen=True)
class Error:
    """The capability call failed; `reason` is a human-readable description."""

    reason: str


type CapabilityResult[T] = Ok[T] | Unavailable | Error


@runtime_checkable
class EntityKindHandler(Protocol):
    """Every Entity Kind provider implements this Protocol and registers an
    instance against its `kind_id` via `register_kind()`. Core's Entity
    Service is the only caller — it owns the transaction/audit shell and
    invokes these methods only for kind-specific work: persisting `spec`
    fields to the kind's `*Details` row, serializing them back out, and
    vetoing a delete that would leave the catalog inconsistent.
    """

    kind_id: str
    spec_schema: type[BaseModel]
    # The partial-update counterpart of `spec_schema` — every field optional,
    # `update_details` reads only what `spec.model_fields_set` actually
    # contains (the existing REST PATCH convention every handler's own
    # `update_details` already follows). Published here, alongside
    # `spec_schema`, so a kind-agnostic caller (`atlas.mcp`'s catalog write
    # tools) can validate a generic `spec` payload for *either* create or
    # update without importing a specific kind-owning plugin's schemas
    # directly (mcp-plugin spec: "Catalog operations route through
    # EntityService").
    patch_schema: type[BaseModel]
    # Semantic capability identifiers this kind provides, independent of any particular consuming plugin — e.g. `system`
    # and `component` declare `architecture.subject.v1` so `atlas.c4` can
    # target them via `entitySupports(...)` instead of naming their kind ids.
    # A handler with nothing to declare sets `provides = []`.
    provides: list[str]

    def create_details(self, entity: CatalogEntity, spec: BaseModel) -> None:
        """Persist `spec` as `entity`'s kind-specific details row. `entity` is already saved."""
        ...

    def update_details(self, entity: CatalogEntity, spec: BaseModel) -> None:
        """Apply a partial `spec` update to `entity`'s existing details row.

        `spec` is expected to be a "patch" model — implementations should only
        touch fields present in `spec.model_fields_set`, matching the wire API's
        partial-update semantics.
        """
        ...

    def serialize_details(self, entity: CatalogEntity) -> BaseModel:
        """Return `entity`'s kind-specific `spec` for read responses."""
        ...

    def validate_delete(self, entity: CatalogEntity) -> None:
        """Raise `ValidateDeleteError` if deleting `entity` would leave dangling references."""
        ...

    def is_deprecated(self, entity: CatalogEntity) -> bool:
        """Whether `entity` should be flagged `deprecated` to anything that references it
        (entity-relations/architecture-relationships specs) — a cosmetic, non-gating read
        of whatever lifecycle flag this kind's own details carry (e.g. Component's
        `lifecycle == 'deprecated'`), independent of `entity.status`. Most kinds have no
        such flag and simply return `False`.
        """
        ...


class ValidateDeleteError(Exception):
    """Raised by `validate_delete` when a delete would leave the catalog inconsistent.

    The Entity Service calls this inside the same transaction as the delete
    and surfaces it as a client-facing error,
    ahead of the DB's `on_delete=PROTECT` backstop.
    """


class DuplicateKindError(ValueError):
    """Raised when a second handler tries to register a claimed `kind_id`.

    `existing_owner`/`new_owner` carry the registering plugins' ids, when
    known, for composition-validation error reporting (plugin-registries
    spec: "identifies the conflicting id and both registering plugins").
    """

    def __init__(
        self,
        kind_id: str,
        *,
        existing_owner: str | None = None,
        new_owner: str | None = None,
    ) -> None:
        message = (
            f"An Entity Kind handler is already registered for kind_id={kind_id!r}"
        )
        if existing_owner or new_owner:
            message += (
                f" (already registered by {existing_owner!r}, "
                f"conflicting registration from {new_owner!r})"
            )
        super().__init__(message)
        self.kind_id = kind_id
        self.existing_owner = existing_owner
        self.new_owner = new_owner


class EntityKindRegistry:
    """Maps `kind_id` to its registered `EntityKindHandler`."""

    def __init__(self) -> None:
        self._handlers: dict[str, EntityKindHandler] = {}
        self._owners: dict[str, str | None] = {}

    def register(
        self,
        handler: EntityKindHandler,
        *,
        owner: str | None = None,
    ) -> None:
        if handler.kind_id in self._handlers:
            raise DuplicateKindError(
                handler.kind_id,
                existing_owner=self._owners[handler.kind_id],
                new_owner=owner,
            )
        self._handlers[handler.kind_id] = handler
        self._owners[handler.kind_id] = owner

    def resolve(self, kind_id: str) -> EntityKindHandler | None:
        """Return the registered handler for `kind_id`, or `None` if none is registered."""
        return self._handlers.get(kind_id)

    def registered_ids(self) -> list[str]:
        """Return every registered `kind_id`, sorted — for startup logging."""
        return sorted(self._handlers)

    def capabilities_for(self, kind_id: str) -> list[str]:
        """Return the capabilities `kind_id`'s handler declares, or `[]` if unregistered."""
        handler = self._handlers.get(kind_id)
        return list(handler.provides) if handler is not None else []

    def kind_ids_with_capability(self, capability: str) -> list[str]:
        """Return every registered `kind_id` whose handler declares `capability`, sorted."""
        return sorted(
            kind_id
            for kind_id, handler in self._handlers.items()
            if capability in handler.provides
        )

    def resolve_capability(
        self, kind_id: str, capability: str
    ) -> "CapabilityResult[bool]":
        """Whether `kind_id`'s handler declares `capability`, distinguishing "no handler
        registered for `kind_id`" (`Unavailable`) from "registered, capability absent"
        (`Ok(False)`) — `capabilities_for`/`kind_ids_with_capability` above collapse both
        into an empty result, which is exactly the ambiguity a capability-shaped call site
        must not present to its caller.
        """
        handler = self._handlers.get(kind_id)
        if handler is None:
            return Unavailable()
        return Ok(capability in handler.provides)


# Process-wide registry populated by the runtime entry-point-loading phase —
# one registry for the whole process, matching the single core Entity
# Service that resolves handlers from it.
registry = EntityKindRegistry()


def register_kind(handler: EntityKindHandler, *, owner: str | None = None) -> None:
    """Register `handler` against its `kind_id`.

    Called from a plugin's `register_runtime()` hook, during the shared
    runtime entry-point-loading phase, after `django.setup()`.
    """
    registry.register(handler, owner=owner)


def resolve_capability(kind_id: str, capability: str) -> "CapabilityResult[bool]":
    """Whether `kind_id`'s registered handler declares `capability` — see
    `EntityKindRegistry.resolve_capability` for the three-way result shape.
    """
    return registry.resolve_capability(kind_id, capability)


def entity_deprecated(entity: CatalogEntity) -> bool:
    """Whether `entity` is `deprecated`, per its kind handler's `is_deprecated()`
    (entity-relations/architecture-relationships specs) — `False` if `entity`'s
    kind has no registered handler, matching `capabilities_for`'s
    unregistered-kind fallback.
    """
    handler = registry.resolve(entity.kind)
    if handler is None:
        return False
    return handler.is_deprecated(entity)
