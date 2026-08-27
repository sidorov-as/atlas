"""Relation derivation and targeted recompute-on-write (`core-plugin-contract-surface`
spec: "Core publishes its plugin-facing surface as contract types").

Canonical home for `recompute_relations`/`entity_relations` — previously
`server.apps.catalog.relations`. Relations are derived from `spec` reference
fields, not authored directly. Each predicate pair (`ownedBy`/`ownerOf`,
`partOf`/`hasPart`, `dependsOn`/`dependencyOf`, `providesAPI`/`apiProvidedBy`,
`consumesAPI`/`apiConsumedBy`, `hasMember`/`memberOf`) has exactly one
"owning" entity kind whose own spec field drives it — `_PREDICATE_PAIRS`
records that ownership so recomputing one entity only ever deletes/reinserts
the rows *it* is responsible for, never rows another entity's write produced.

Like `refs.py`, this needs only a real `Relation` query, available through
`get_relation_model()` without importing the concrete model, so it moves
here outright rather than staying in `server` behind a wrapper.
`server.apps.catalog.relations` re-exports it for Core's own internal call
sites.

A plugin recomputes an entity's relations through `recompute_relations()`,
not by importing `server.apps.catalog.relations` directly.
"""

from typing import Any

from django.apps import apps as _django_apps
from django.db import transaction
from django.db.models import Q

from .catalog import (
    KIND_ACTOR,
    KIND_API,
    KIND_COMPONENT,
    KIND_GROUP,
    KIND_RESOURCE,
    KIND_SYSTEM,
)
from .membership import get_membership_service

RELATION_LABEL = "catalog.Relation"

_OWNED_PAIR = ("ownedBy", "ownerOf")
_SYSTEM_PAIR = ("partOf", "hasPart")

_PREDICATE_PAIRS: dict[str, list[tuple[str, str]]] = {
    KIND_SYSTEM: [_OWNED_PAIR],
    KIND_COMPONENT: [
        _OWNED_PAIR,
        _SYSTEM_PAIR,
        ("dependsOn", "dependencyOf"),
        ("providesAPI", "apiProvidedBy"),
        ("consumesAPI", "apiConsumedBy"),
    ],
    KIND_RESOURCE: [_OWNED_PAIR, _SYSTEM_PAIR],
    KIND_API: [_OWNED_PAIR, _SYSTEM_PAIR],
    KIND_GROUP: [("hasMember", "memberOf")],
    KIND_ACTOR: [],
}


def get_relation_model() -> type:
    """Resolve Core's concrete `Relation` model via Django's app registry,
    the same lazy-resolution mechanism `get_catalog_entity_model()` uses.
    Only callable after `django.setup()` — from inside a function body,
    never cached at plugin module import time.
    """
    return _django_apps.get_model(RELATION_LABEL)


def _edges_for(instance: Any) -> list[tuple[Any, str, Any]]:
    """`(subject, predicate, object)` edges derived from `instance`'s own fields."""
    edges: list[tuple[Any, str, Any]] = []

    if instance.owner is not None:
        edges.append((instance, "ownedBy", instance.owner))
        edges.append((instance.owner, "ownerOf", instance))

    if instance.kind in (KIND_COMPONENT, KIND_RESOURCE, KIND_API):
        system = instance.details.system
        if system is not None:
            edges.append((instance, "partOf", system))
            edges.append((system, "hasPart", instance))

    if instance.kind == KIND_COMPONENT:
        details = instance.details
        for resource in details.depends_on.all():
            edges.append((instance, "dependsOn", resource))
            edges.append((resource, "dependencyOf", instance))
        for api in details.provides_apis.all():
            edges.append((instance, "providesAPI", api))
            edges.append((api, "apiProvidedBy", instance))
        for api in details.consumes_apis.all():
            edges.append((instance, "consumesAPI", api))
            edges.append((api, "apiConsumedBy", instance))

    if instance.kind == KIND_GROUP:
        for actor in get_membership_service().effective_members(instance.details):
            edges.append((instance, "hasMember", actor))
            edges.append((actor, "memberOf", instance))

    return edges


@transaction.atomic
def recompute_relations(instance: Any) -> None:
    """Recompute every `Relation` row derived from `instance`'s own spec fields.

    Deletes only the rows `instance`'s kind owns (its forward predicates as
    subject, their reverse mirrors as object) and reinserts them from current
    state — every other entity's relation rows are untouched (targeted
    recompute-on-write).
    """
    relation_model = get_relation_model()
    pairs = _PREDICATE_PAIRS.get(instance.kind, [])
    if pairs:
        forward_predicates = [forward for forward, _reverse in pairs]
        reverse_predicates = [reverse for _forward, reverse in pairs]
        relation_model.objects.filter(
            Q(subject_entity=instance, predicate__in=forward_predicates)
            | Q(object_entity=instance, predicate__in=reverse_predicates),
        ).delete()

    edges = _edges_for(instance)
    relation_model.objects.bulk_create(
        relation_model(subject_entity=subject, predicate=predicate, object_entity=obj)
        for subject, predicate, obj in edges
    )


def entity_relations(instance: Any) -> list[tuple[str, str, str, object]]:
    """Every relation involving `instance`, as `(predicate, target_ref, target_kind, target_id)` tuples.

    Both directions of every relation are materialized as their own row with
    `instance` as subject, so a plain subject filter already returns each
    relation exactly once, correctly labeled from `instance`'s own point of
    view — no fan-out query needed.
    """
    rows = (
        get_relation_model()
        .objects.filter(subject_entity=instance)
        .select_related("object_entity")
    )
    return [
        (
            row.predicate,
            row.object_entity.ref,
            row.object_entity.kind,
            row.object_entity.id,
        )
        for row in rows
    ]
