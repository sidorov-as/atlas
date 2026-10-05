"""Basic ingestion upsert: create or update by `(kind, name)`, routed through
the core Entity Service.

Unlike the CRUD API's PATCH, ingestion always overwrites the matched entity
in full — re-ingesting the same file updates every field to match (ADR
0001). A field the manifest omits is explicitly reset (e.g. to its Patch
schema's default) rather than left untouched, which is why an update
constructs a Patch object with every field marked as set (`model_dump()`
unpacked back into the Patch schema's constructor) instead of passing the
parsed manifest spec straight through — a real partial patch would rely on
`model_fields_set` reflecting only what the caller *touched*, which is the
CRUD API's semantics, not ingestion's.

Each call is its own transaction (per-manifest, not
per-run), so one entity's write failing doesn't affect entities already
upserted earlier in the same run. Conflict-record bookkeeping around a
successful claim is wrapped in the same transaction as the Entity Service
call so the two can't drift if the process dies between them; a *rejected*
claim's conflict record is written outside any entity-write transaction,
since the whole point is to persist it even though the entity write never
happens.

First-claim collisions are arbitrated rather than silently overwritten
(ADR 0001 amendment): a ref already claimed by
a manual entity, by a different repository, or by a `removed` entity (of
either origin) still holding the name, is rejected and recorded as a
`ConflictRecord` instead of being upserted, and the rejection is decided
*before* an `EntityIntent` would be constructed — a rejected claim never
reaches the Entity Service. Arbitration is
re-evaluated from current state on every call — nothing here short-circuits
on a previous run's result, so deleting the blocking entity unblocks the
rival claim on the very next run with no cache to invalidate.
"""

import logging

from atlas_plugin_api import (
    ARCHITECTURE_RELATIONSHIP_ORIGIN_YAML,
    DEFAULT_NAMESPACE,
    KIND_ACTOR,
    KIND_API,
    KIND_COMPONENT,
    KIND_RESOURCE,
    KIND_SYSTEM,
    SOURCE_MANUAL,
    SOURCE_YAML,
    STATUS_ACTIVE,
    STATUS_REMOVED,
    CatalogEntity,
    MetadataPatch,
    RefError,
    ensure_tags_exist,
    get_architecture_relationship_model,
    get_catalog_entity_model,
    get_entity_service,
    resolve_ref,
)
from atlas_plugin_apis.contracts import ApiSpecPatch
from atlas_plugin_standard_catalog.contracts import (
    ActorSpecPatch,
    ComponentSpecPatch,
    ResourceSpecPatch,
    SystemSpecPatch,
)
from django.db import transaction
from pydantic import BaseModel

from .claims import claim_entity, claiming_repository_id
from .intent import EntityIntent
from .models import ConflictRecord, RegisteredRepository
from .validation import ManifestDocument

logger = logging.getLogger("atlas_plugin_ingestion")

_KIND_IDS: dict[str, str] = {
    "System": KIND_SYSTEM,
    "Component": KIND_COMPONENT,
    "Resource": KIND_RESOURCE,
    "API": KIND_API,
    "User": KIND_ACTOR,
}

_PATCH_SCHEMAS: dict[str, type[BaseModel]] = {
    KIND_SYSTEM: SystemSpecPatch,
    KIND_COMPONENT: ComponentSpecPatch,
    KIND_RESOURCE: ResourceSpecPatch,
    KIND_API: ApiSpecPatch,
    KIND_ACTOR: ActorSpecPatch,
}


class ClaimRejected(Exception):
    """Raised when arbitration rejects an ingestion claim; the conflict is already recorded."""


def _record_conflict(
    repo: RegisteredRepository, kind: str, namespace: str, name: str, reason: str
) -> None:
    conflict = ConflictRecord.objects.filter(
        repository=repo,
        kind=kind,
        namespace=namespace,
        name=name,
        reason=reason,
    ).first()
    if conflict is None:
        ConflictRecord.objects.create(
            repository=repo,
            repo_full_name=str(repo),
            kind=kind,
            namespace=namespace,
            name=name,
            reason=reason,
        )
    else:
        conflict.repo_full_name = str(repo)
        conflict.is_active = True
        conflict.save(update_fields=["repo_full_name", "is_active", "last_seen"])


def _resolve_conflicts(kind: str, namespace: str, name: str) -> None:
    ConflictRecord.objects.filter(
        kind=kind, namespace=namespace, name=name, is_active=True
    ).update(is_active=False)


def _full_update_metadata_and_spec(
    intent: EntityIntent,
) -> tuple[MetadataPatch, BaseModel]:
    """Build full-overwrite Patch objects for `EntityService.update` from an `EntityIntent`.

    Reconstructing via `**model_dump()` marks every field as explicitly set
    (`model_fields_set`), even ones equal to their default — the Patch
    schema's `if <field> in fields:` checks then touch every field, matching
    ingestion's full-overwrite semantics instead of the CRUD API's partial-patch
    ones. `relationships` isn't a Patch-schema field (it's reconciled
    separately by `reconcile_declared_relationships`), so it's excluded.
    """
    metadata_patch = MetadataPatch(**intent.metadata.model_dump())
    spec_patch_cls = _PATCH_SCHEMAS[intent.kind]
    spec_patch = spec_patch_cls(**intent.spec.model_dump(exclude={"relationships"}))
    return metadata_patch, spec_patch


def upsert_entity(doc: ManifestDocument, repo: RegisteredRepository) -> CatalogEntity:
    kind_id = _KIND_IDS[doc.kind]
    namespace = DEFAULT_NAMESPACE
    name = doc.metadata.name

    existing = (
        get_catalog_entity_model()
        .objects.filter(
            kind=kind_id,
            namespace=namespace,
            name__iexact=name,
        )
        .first()
    )
    if existing is not None:
        # Recorded outside the write transaction below: a claim rejection must
        # persist its conflict record even though the upsert itself never runs,
        # and a rejected claim never reaches
        # the point below where an `EntityIntent` is even constructed.
        claiming_repo_id = claiming_repository_id(existing)
        is_rival = existing.source_kind == SOURCE_MANUAL or claiming_repo_id != repo.id
        if is_rival and existing.status == STATUS_REMOVED:
            # A removed entity's ref stays claimed (a removed entity keeps its name
            # reserved) — this reason
            # supersedes manual_entity/other_repository below for a rival
            # claim, distinguishing "blocked forever" from "blocked until
            # revived or purged". Same-repo re-declaration of its own removed
            # entity is not a rival (`is_rival` is False for it) and instead
            # falls through to the revive path further down.
            _record_conflict(
                repo, kind_id, namespace, name, ConflictRecord.REASON_REMOVED_ENTITY
            )
            raise ClaimRejected(f"{doc.kind} {name!r} is claimed by a removed entity")
        if existing.source_kind == SOURCE_MANUAL:
            _record_conflict(
                repo, kind_id, namespace, name, ConflictRecord.REASON_MANUAL_ENTITY
            )
            raise ClaimRejected(
                f"{doc.kind} {name!r} is already claimed by a manual entity"
            )
        if claiming_repo_id != repo.id:
            _record_conflict(
                repo, kind_id, namespace, name, ConflictRecord.REASON_OTHER_REPOSITORY
            )
            claimant = RegisteredRepository.objects.filter(pk=claiming_repo_id).first()
            raise ClaimRejected(
                f"{doc.kind} {name!r} is already claimed by {claimant}",
            )

    # Arbitration has cleared the claim (or there was nothing to arbitrate) —
    # only now is the `EntityIntent` constructed and submitted to the Entity Service.
    intent = EntityIntent(
        kind=kind_id,
        namespace=namespace,
        name=name,
        metadata=doc.metadata,
        spec=doc.spec,
        ingested_from=repo,
    )
    owner_ref = getattr(intent.spec, "owner", None)

    with transaction.atomic():
        if existing is not None:
            if existing.status == STATUS_REMOVED:
                # Same repo re-declaring a ref it previously dropped: Revive
                # (id/relations preserved) before the normal same-repo
                # overwrite below applies the manifest's current fields
                # (an entity removed by ingestion revives automatically when re-declared).
                # Arbitration above already guarantees
                # this is the same claiming repository, never a rival.
                get_entity_service().revive(
                    entity_id=existing.id, actor=None, source=SOURCE_YAML
                )
            metadata_patch, spec_patch = _full_update_metadata_and_spec(intent)
            instance = get_entity_service().update(
                entity_id=existing.id,
                owner_ref=owner_ref,
                metadata=metadata_patch,
                spec=spec_patch,
                actor=None,
                source=intent.source_kind,
            )
        else:
            instance = get_entity_service().create(
                kind_id=intent.kind,
                owner_ref=owner_ref,
                metadata=intent.metadata,
                spec=intent.spec,
                actor=None,
                source=intent.source_kind,
            )
        claim_entity(instance, intent.ingested_from)
        _resolve_conflicts(kind_id, namespace, name)
    return instance


def reconcile_declared_relationships(
    doc: ManifestDocument, instance: CatalogEntity
) -> None:
    """Sync `instance`'s outgoing YAML-origin Architecture Relationships to `doc.spec.relationships`.

    Runs after every entity in the manifest has been upserted, so a declared target defined later in the same
    multi-document manifest is already resolvable here. Each declaration is
    resolved independently — one unresolved target is reported and skipped
    without blocking the entity's other declarations or creating a partial
    row (per-manifest failure isolation). The
    declared set fully replaces the source's prior YAML-origin relationships;
    manual rows are never touched.
    """
    architecture_relationship_model = get_architecture_relationship_model()
    declared = getattr(doc.spec, "relationships", [])
    kept_ids = set()
    for decl in declared:
        try:
            target = resolve_ref(decl.target)
        except RefError as exc:
            logger.warning(
                "Skipping unresolved architecture relationship target for %s (%s): %s",
                instance.ref,
                decl.target,
                exc,
            )
            continue
        kept_ids.add(target.id)
        architecture_relationship_model.objects.update_or_create(
            source=instance,
            target=target,
            origin=ARCHITECTURE_RELATIONSHIP_ORIGIN_YAML,
            defaults={
                "label": decl.label,
                "technology": decl.technology,
                "interaction_kind": decl.interaction_kind,
                "tags": decl.tags,
            },
        )
        ensure_tags_exist(decl.tags)

    stale = architecture_relationship_model.objects.filter(
        source=instance,
        origin=ARCHITECTURE_RELATIONSHIP_ORIGIN_YAML,
    )
    if kept_ids:
        stale = stale.exclude(target_id__in=kept_ids)
    stale.delete()


def reconcile_claimed_entities(
    repo: RegisteredRepository, upserted: list[tuple[ManifestDocument, CatalogEntity]]
) -> None:
    """Remove whole entities `repo` previously claimed but no longer declares (the zombie-entity
    fix), symmetric to `reconcile_declared_relationships` above and to how
    `ApiEndpoint`/`ApiOperation` disappearance is already reconciled.

    Scoped strictly to `repo`'s own `source_kind=yaml` claims: auto-remove authority is sticky to
    origin — an entity claimed by a different repository, or a
    manually-created entity that happens to share a since-dropped ref, is never touched, since
    this query only ever looks at rows this same repository claims. Runs through the Entity
    Service's Remove transaction, never a direct status write.
    """
    seen_ids = {instance.id for _, instance in upserted}
    stale = (
        get_catalog_entity_model()
        .objects.filter(
            source_kind=SOURCE_YAML,
            ingestion_claim__repository=repo,
            status=STATUS_ACTIVE,
        )
        .exclude(id__in=seen_ids)
    )
    for entity in stale:
        get_entity_service().remove(entity_id=entity.id, actor=None, source=SOURCE_YAML)
