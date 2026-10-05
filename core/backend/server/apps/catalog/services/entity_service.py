"""Core Entity Service.

The only code path allowed to create, update, or delete a `CatalogEntity`: it
authorizes, validates the common envelope, resolves the kind handler from the
registry, opens one transaction, changes `CatalogEntity`, invokes the handler
for kind-specific data, writes an audit record, and commits — all inside one
`transaction.atomic()` block, so a kind-handler failure rolls back everything

`owner` is a `CatalogEntity` field, not a `*Details` one, so — like
name/title/description/labels/tags/links — its resolution lives here rather
than in a kind handler, even though the wire schema nests it under `spec`
for Backstage-envelope-shaped UX reasons.

`EntityRead`/`EntityNotFoundError`/`EntityUnavailableError`/
`UnknownEntityKindError` are re-exported from `atlas_plugin_api.entity_service`
— canonical home moved there,
since none needs a Django model; a plugin reads/writes through
`atlas_plugin_api.get_entity_service()`, not this module directly. Kept as a
same-named re-export so Core's own internal call sites don't need to change.
`entity_service` (the singleton below) is registered with `atlas_plugin_api`
via `server.apps.catalog.plugin.register_runtime()`'s `bind_entity_service()`
call, not exported from here for plugin use.
"""

from typing import Any
from uuid import UUID

from atlas_plugin_api.entity_service import (
    DuplicateEntityError,
    EntityNotFoundError,
    EntityRead,
    EntityUnavailableError,
    UnknownEntityKindError,
)
from atlas_plugin_api.purge import PurgeReference, run_purge_scan
from django.db import IntegrityError, transaction
from pydantic import BaseModel

from server.apps.catalog import refs
from server.apps.catalog.api.permissions import EntityWritePermission
from server.apps.catalog.kinds.handler import (
    EntityKindHandler,
    ValidateDeleteError,
)
from server.apps.catalog.kinds.registry import EntityKindRegistry
from server.apps.catalog.kinds.registry import registry as default_registry
from server.apps.catalog.models import (
    KIND_GROUP,
    CatalogEntity,
    EntityAuditRecord,
    ensure_tags_exist,
)

__all__ = [
    "EntityNotFoundError",
    "EntityRead",
    "EntityService",
    "EntityUnavailableError",
    "UnknownEntityKindError",
    "entity_service",
]


_UNIQUE_NAME_CONSTRAINT = "catalog_entity_unique_kind_namespace_name"


def _is_duplicate_name(exc: IntegrityError) -> bool:
    """Whether `exc` is the per-kind unique-name constraint, not some other
    integrity failure that must keep surfacing as a server error."""
    diag = getattr(exc.__cause__, "diag", None)
    constraint = getattr(diag, "constraint_name", None)
    return constraint == _UNIQUE_NAME_CONSTRAINT or (
        constraint is None and _UNIQUE_NAME_CONSTRAINT in str(exc)
    )


def _audit_actor(actor: Any):
    return actor if actor is not None and actor.is_authenticated else None


def _dump(model: BaseModel | None, *, fields_only: bool = False) -> dict:
    if model is None:
        return {}
    include = model.model_fields_set if fields_only else None
    return model.model_dump(mode="json", include=include)


def _owner_references(entity: CatalogEntity) -> list[PurgeReference]:
    """`owner` is one of D8's named FK-backed reference types, but — unlike
    `dependsOn`/`providesApis`/`consumesApis` — it's a Core field, not a
    plugin's, so it's checked here directly rather than through a registered
    `atlas_plugin_api.purge` scanner. In practice this is always empty for
    every currently purgeable kind (System/Component/Resource/API): `owner`
    only ever resolves to a Group (`create`'s `expected_kind=KIND_GROUP`),
    and Group isn't itself purgeable (D10) — kept for spec completeness and
    to cover a future purgeable owner-capable kind without another change
    here. No `cascade` is needed even for a `removed` owner: `owner`'s
    `on_delete=SET_NULL` already clears it automatically when the owning
    row is deleted.

    Module-level, not a method: a bare `list[...]` annotation inside
    `EntityService`'s class body would resolve `list` to the class's own
    `list()` method instead of the builtin (class-body name resolution
    checks the class namespace first).
    """
    return [
        PurgeReference(
            label=f"{owned.kind}:{owned.name} (owner)",
            active=owned.status == CatalogEntity.STATUS_ACTIVE,
        )
        for owned in entity.owned_entities.all()
    ]


class EntityService:
    """Owns the authorize → validate → resolve → transaction → audit
    pipeline for every Catalog Entity create/update/delete
    """

    def __init__(self, registry: EntityKindRegistry | None = None) -> None:
        self.registry = registry or default_registry

    def _resolve_handler(self, kind_id: str) -> EntityKindHandler:
        handler = self.registry.resolve(kind_id)
        if handler is None:
            raise UnknownEntityKindError(kind_id)
        return handler

    def _resolve_handler_for_write(
        self, entity: CatalogEntity
    ) -> EntityKindHandler:
        """Like `_resolve_handler`, but for a write against an already-existing
        `entity` — raises `EntityUnavailableError` instead, since the entity
        is real and the condition is "became unavailable", not "was never a
        valid kind".
        """
        handler = self.registry.resolve(entity.kind)
        if handler is None:
            raise EntityUnavailableError(entity.kind)
        return handler

    def _get_entity(self, entity_id: UUID) -> CatalogEntity:
        try:
            return CatalogEntity.objects.select_related("owner").get(
                pk=entity_id
            )
        except CatalogEntity.DoesNotExist:
            raise EntityNotFoundError(str(entity_id)) from None

    @staticmethod
    def _apply_metadata(entity: CatalogEntity, metadata: BaseModel) -> None:
        """Validate/apply the common envelope
        (name/title/description/labels/tags/links).

        Runs before any kind handler is invoked — an invalid common field
        never reaches `create_details`/`update_details`
        """
        entity.name = metadata.name
        entity.title = metadata.title
        entity.description = metadata.description
        entity.documentation = metadata.documentation
        entity.labels = metadata.labels
        entity.tags = metadata.tags
        entity.links = [link.model_dump() for link in metadata.links]
        ensure_tags_exist(metadata.tags)

    @staticmethod
    def _apply_metadata_patch(
        entity: CatalogEntity, metadata: BaseModel | None
    ) -> None:
        if metadata is None:
            return
        for field in metadata.model_fields_set:
            value = getattr(metadata, field)
            if field == "links":
                value = [link.model_dump() for link in value]
            setattr(entity, field, value)
        if metadata.tags is not None:
            ensure_tags_exist(metadata.tags)

    def get(self, entity_id: UUID) -> EntityRead:
        return self._read(self._get_entity(entity_id))

    def list(self, *, kind_id: str | None = None) -> list[EntityRead]:
        queryset = CatalogEntity.objects.select_related("owner")
        if kind_id is not None:
            queryset = queryset.filter(kind=kind_id)
        return [self._read(entity) for entity in queryset]

    def _read(self, entity: CatalogEntity) -> EntityRead:
        """The "not found" early-return branch: an
        entity whose kind has no registered handler comes back with
        `spec=None`/`unavailable=True` instead of erroring or attempting to
        call a nonexistent handler's `serialize_details` — kept as a clearly
        separate branch from the normal case rather than threaded through it
        """
        handler = self.registry.resolve(entity.kind)
        if handler is None:
            return EntityRead(entity=entity, spec=None, unavailable=True)
        return EntityRead(
            entity=entity,
            spec=handler.serialize_details(entity),
            unavailable=False,
        )

    def create(
        self,
        *,
        kind_id: str,
        owner_ref: str | None = None,
        metadata: BaseModel,
        spec: BaseModel,
        actor: Any,
        source: str = CatalogEntity.SOURCE_MANUAL,
    ) -> CatalogEntity:
        """`owner_ref` is `None` for kinds with no owner concept (Group,
        Actor themselves);
        `EntityWritePermission.check_create` then requires a superuser
        rather than skipping authorization entirely.

        `source`: an ingestion writer passes `source=CatalogEntity.SOURCE_YAML`
        rather than patching `source_kind` onto the entity after this call
        returns, which would be a second, unaudited write. Which repository
        claims the entity is ingestion's own record (`EntityClaim`), written
        by ingestion; core's entity row carries no reference to it. A
        `source='yaml'` call is treated as pre-authorized by ingestion's own
        arbitration step, which already gated whether this call happens at all
        (a rejected claim never reaches the
        Entity Service), so it skips `EntityWritePermission` rather than
        requiring a superuser actor ingestion has no natural way to supply.
        """
        handler = self._resolve_handler(kind_id)
        owner = (
            refs.resolve_ref(owner_ref, expected_kind=KIND_GROUP)
            if owner_ref is not None
            else None
        )
        if source != CatalogEntity.SOURCE_YAML:
            EntityWritePermission.check_create(actor, owner)

        try:
            with transaction.atomic():
                entity = CatalogEntity(
                    kind=kind_id,
                    owner=owner,
                    source_kind=source,
                )
                self._apply_metadata(entity, metadata)
                entity.save()
                handler.create_details(entity, spec)
                EntityAuditRecord.objects.create(
                    entity_id=entity.id,
                    kind=entity.kind,
                    action=EntityAuditRecord.ACTION_CREATE,
                    actor=_audit_actor(actor),
                    diff={"metadata": _dump(metadata), "spec": _dump(spec)},
                )
        except IntegrityError as exc:
            if _is_duplicate_name(exc):
                raise DuplicateEntityError(kind_id, metadata.name) from exc
            raise
        return entity

    def update(
        self,
        *,
        entity_id: UUID,
        owner_ref: str | None = None,
        metadata: BaseModel | None = None,
        spec: BaseModel | None = None,
        actor: Any,
        source: str = CatalogEntity.SOURCE_MANUAL,
    ) -> CatalogEntity:
        """`source`: see `create`'s docstring. A `source='yaml'`
        call skips `EntityWritePermission.check_write` — including its
        unconditional "YAML-managed entities reject every write" rule (ADR
        0001), which exists to block *manual* edits to an ingested entity, not
        ingestion's own re-claim of it."""
        entity = self._get_entity(entity_id)
        if source != CatalogEntity.SOURCE_YAML:
            EntityWritePermission.check_write(actor, entity)
        handler = self._resolve_handler_for_write(entity)

        try:
            with transaction.atomic():
                self._apply_metadata_patch(entity, metadata)
                if owner_ref is not None:
                    entity.owner = refs.resolve_ref(
                        owner_ref, expected_kind=KIND_GROUP
                    )
                entity.source_kind = source
                entity.save()
                if spec is not None:
                    handler.update_details(entity, spec)
                EntityAuditRecord.objects.create(
                    entity_id=entity.id,
                    kind=entity.kind,
                    action=EntityAuditRecord.ACTION_UPDATE,
                    actor=_audit_actor(actor),
                    diff={
                        "metadata": _dump(metadata, fields_only=True),
                        "spec": _dump(spec, fields_only=True),
                    },
                )
        except IntegrityError as exc:
            if _is_duplicate_name(exc):
                raise DuplicateEntityError(entity.kind, entity.name) from exc
            raise
        return entity

    def remove(
        self,
        *,
        entity_id: UUID,
        actor: Any,
        source: str = CatalogEntity.SOURCE_MANUAL,
    ) -> CatalogEntity:
        """Removed/Revive/Purge lifecycle:
        flips `status` to `removed` in the same authorize → mutate → audit →
        commit shape as `create`/`update`.

        `source='yaml'` skips `EntityWritePermission` the same way
        `create`/`update` do — this is ingestion's own reconciliation
        re-claiming an entity it already owns (the
        auto-remove-authority-sticky-to-origin guard is enforced by the
        caller, not here). A manual (`source='manual'`) call goes through
        `check_write`, which already rejects every write against a
        `source_kind=yaml` entity unconditionally (ADR 0001) — so manual
        Remove is blocked for YAML-managed entities the same way manual
        edit/delete already are (D13), with no extra gating needed here.
        """
        entity = self._get_entity(entity_id)
        if source != CatalogEntity.SOURCE_YAML:
            EntityWritePermission.check_write(actor, entity)

        with transaction.atomic():
            entity.status = CatalogEntity.STATUS_REMOVED
            entity.save(update_fields=["status", "updated_at"])
            EntityAuditRecord.objects.create(
                entity_id=entity.id,
                kind=entity.kind,
                action=EntityAuditRecord.ACTION_REMOVE,
                actor=_audit_actor(actor),
                diff={"status": CatalogEntity.STATUS_REMOVED},
            )
        return entity

    def revive(
        self,
        *,
        entity_id: UUID,
        actor: Any,
        source: str = CatalogEntity.SOURCE_MANUAL,
    ) -> CatalogEntity:
        """Removed → active, preserving id/relations/audit history

        See `remove`'s docstring for the `source='yaml'` bypass and the
        `check_write`-based YAML-managed-entity block, which applies
        identically to manual Revive (D13).
        """
        entity = self._get_entity(entity_id)
        if source != CatalogEntity.SOURCE_YAML:
            EntityWritePermission.check_write(actor, entity)

        with transaction.atomic():
            entity.status = CatalogEntity.STATUS_ACTIVE
            entity.save(update_fields=["status", "updated_at"])
            EntityAuditRecord.objects.create(
                entity_id=entity.id,
                kind=entity.kind,
                action=EntityAuditRecord.ACTION_REVIVE,
                actor=_audit_actor(actor),
                diff={"status": CatalogEntity.STATUS_ACTIVE},
            )
        return entity

    def delete(self, *, entity_id: UUID, actor: Any) -> None:
        entity = self._get_entity(entity_id)
        EntityWritePermission.check_write(actor, entity)
        handler = self._resolve_handler_for_write(entity)

        with transaction.atomic():
            handler.validate_delete(entity)
            EntityAuditRecord.objects.create(
                entity_id=entity.id,
                kind=entity.kind,
                action=EntityAuditRecord.ACTION_DELETE,
                actor=_audit_actor(actor),
                diff={"name": entity.name, "namespace": entity.namespace},
            )
            entity.delete()

    def purge(self, *, entity_id: UUID, actor: Any) -> None:
        """Purge: the only action that frees a
        `removed` entity's `(kind, namespace, name)` slot, by permanently
        deleting its `CatalogEntity` row and kind-details row (D6/D7).

        Requires a Purge Grant (`check_purge`), not ownership — the one
        deliberate, narrow carve-out from YAML-managed entities otherwise
        rejecting every write (D9), so this doesn't call `check_write`.
        Reference-scanning validation runs inside the same transaction as
        the row deletion (deletion validity is checked inside the
        delete transaction, applying identically to
        purge), collecting both the Core-owned `owner` check above and every
        plugin-registered scanner (`run_purge_scan` — `dependsOn`/
        `providesApis`/`consumesApis` from `atlas_plugin_standard_catalog`,
        Flow `entity_ref` from the optional `atlas_plugin_flows`): any
        `active` reference blocks the purge with a named list (D8); every
        remaining (already-`removed`-status) reference is cascaded away via
        its own `cascade()` before the row is deleted. `handler.
        validate_delete` still runs afterwards, unchanged, as a structural
        backstop for what the new scan doesn't cover (e.g. a System's
        PROTECT-guarded Component/Resource/API/Flow containment) — by that
        point the scan has already cascaded away everything it's
        responsible for, so it never conflicts with the new cascade-on-
        removed behavior.
        """
        entity = self._get_entity(entity_id)
        if entity.status != CatalogEntity.STATUS_REMOVED:
            raise ValidateDeleteError(
                f"Cannot purge {entity.kind} {entity.name!r}: only a "
                "removed entity may be purged",
            )
        EntityWritePermission.check_purge(actor, entity)
        handler = self._resolve_handler_for_write(entity)

        with transaction.atomic():
            references = [*_owner_references(entity), *run_purge_scan(entity)]
            blocking = [
                reference.label for reference in references if reference.active
            ]
            if blocking:
                raise ValidateDeleteError(
                    f"Cannot purge {entity.kind} {entity.name!r}: still "
                    f"referenced by {', '.join(blocking)}",
                )
            for reference in references:
                if reference.cascade is not None:
                    reference.cascade()
            handler.validate_delete(entity)
            EntityAuditRecord.objects.create(
                entity_id=entity.id,
                kind=entity.kind,
                action=EntityAuditRecord.ACTION_PURGE,
                actor=_audit_actor(actor),
                diff={"name": entity.name, "namespace": entity.namespace},
            )
            entity.delete()


# Process-wide instance, matching the single shared `registry` it resolves
# handlers from.
entity_service = EntityService()
