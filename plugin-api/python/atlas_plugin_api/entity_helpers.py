"""Shared entity-controller helpers (`core-plugin-contract-surface` spec:
"Core publishes its plugin-facing surface as contract types").

Stands in for `server.apps.catalog.api.helpers`, used by both Core's own
controllers (Flow, Tag, ArchitectureRelationship, diagrams) and every
first-party plugin's CRUD API (System/Component/Resource/API/Group/Actor) —
previously imported directly from Core.

Most of this needs only what's already published elsewhere in
`atlas_plugin_api` (`get_entity_service()`, `kinds.registry`,
`tags.get_tag_model()`), so it moves here outright. Two functions —
`adopt()`/`blocked_by()` — are different: they need Core's own
`EntityWritePermission` and a conditionally-installed plugin
(`atlas_plugin_ingestion`), neither of which `atlas_plugin_api` may depend on
(a shared contract package can't reach into one specific plugin's
implementation, any more than a plugin can reach into Core's). So, like
`entity_service.py`'s `bind_entity_service()`/`get_entity_service()`, Core
registers its real implementations into a process-wide slot
(`bind_entity_helpers()`, from `server.apps.catalog.plugin.register_runtime()`)
and a plugin calls the published `adopt()`/`blocked_by()` wrappers here
instead — the same "Core registers into `atlas_plugin_api`" mirror-image
pattern, so this module never imports `server` or any specific plugin.

`server.apps.catalog.api.helpers` re-exports the pure functions for Core's
own internal call sites.
"""

from collections.abc import Callable
from http import HTTPStatus
from typing import Any

from dmr import ResponseSpec
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.response import APIError

from .audit import entity_history
from .catalog import get_catalog_entity_model
from .entity_service import get_entity_service
from .kinds import ValidateDeleteError, entity_deprecated
from .kinds import registry as kind_registry
from .permissions import get_policy_evaluator
from .relations import entity_relations
from .schemas import (
    EntityPermissionsOut,
    HistoryRecordOut,
    LinkSchema,
    MetadataOut,
    RelationOut,
)
from .tags import DEFAULT_TAG_COLOR, get_tag_model

API_VERSION = "atlas/v1alpha1"

FORBIDDEN_RESPONSE = ResponseSpec(
    ErrorModel,
    status_code=HTTPStatus.FORBIDDEN,
    description="Ownership permission denied",
)


def not_found(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.not_found),
        status_code=HTTPStatus.NOT_FOUND,
    )


def delete_blocked(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.value_error),
        status_code=HTTPStatus.BAD_REQUEST,
    )


def spec_owner_ref(spec) -> str | None:
    """Pull the ref-string `owner` out of a `*SpecPatch`, or `None` if the PATCH didn't set it.

    `owner` lives on `CatalogEntity` (not a kind's `*Details` row), so
    `EntityService` resolves/assigns it itself rather than delegating to a
    kind handler.
    """
    if spec is None or "owner" not in spec.model_fields_set:
        return None
    return spec.owner


def remove_entity(entity_id, actor):
    return get_entity_service().remove(entity_id=entity_id, actor=actor)


def revive_entity(entity_id, actor):
    return get_entity_service().revive(entity_id=entity_id, actor=actor)


def purge_entity(entity_id, actor) -> None:
    try:
        get_entity_service().purge(entity_id=entity_id, actor=actor)
    except ValidateDeleteError as exc:
        raise delete_blocked(str(exc)) from None


def tag_colors(tags: list[str]) -> dict[str, str]:
    colors = dict(
        get_tag_model().objects.filter(name__in=tags).values_list("name", "color")
    )
    return {name: colors.get(name, DEFAULT_TAG_COLOR) for name in tags}


def metadata_out(instance: Any) -> MetadataOut:
    tags = list(instance.tags)
    return MetadataOut(
        name=instance.name,
        title=instance.title,
        description=instance.description,
        documentation=instance.documentation,
        labels=instance.labels,
        tags=tags,
        tag_colors=tag_colors(tags),
        links=[LinkSchema(**link) for link in instance.links],
    )


def entity_permissions(instance: Any, user: Any) -> EntityPermissionsOut:
    """The requesting `user`'s edit/purge permissions on `instance`, decided
    by the same policy evaluator the write endpoints use (edit covers
    Remove and Revive too, which share its ownership rule)."""
    evaluator = get_policy_evaluator()
    return EntityPermissionsOut(
        can_edit=evaluator.check(user, f"{instance.kind}.edit", instance),
        can_purge=evaluator.check(user, f"{instance.kind}.purge", instance),
    )


def entity_capabilities(instance: Any) -> list[str]:
    """The semantic capabilities `instance`'s kind declares —
    what `entitySupports(capability)` checks client-side against each entity's payload."""
    return kind_registry.capabilities_for(instance.kind)


def ingested_from(instance: Any) -> str | None:
    """`"<source_id>/<path>"`, matching `RegisteredRepository.__str__`"""
    return str(instance.ingested_from) if instance.ingested_from_id else None


def relations_out(instance: Any) -> list[RelationOut]:
    relations = entity_relations(instance)
    targets = get_catalog_entity_model().objects.in_bulk(
        {target_id for _predicate, _target, _target_kind, target_id in relations},
    )
    return [
        RelationOut(
            predicate=predicate,
            target=target,
            target_kind=target_kind,
            target_id=target_id,
            status=targets[target_id].status,
            deprecated=entity_deprecated(targets[target_id]),
        )
        for predicate, target, target_kind, target_id in relations
        if target_id in targets
    ]


def history_out(instance: Any) -> list[HistoryRecordOut]:
    return [
        HistoryRecordOut(action=action, actor=actor, timestamp=timestamp)
        for action, actor, timestamp in entity_history(instance)
    ]


AdoptFn = Callable[[Any, Any, Any], None]
BlockedByFn = Callable[[Any], str | None]
BlockedByReasonFn = Callable[[Any], str | None]

_adopt_impl: AdoptFn | None = None
_blocked_by_impl: BlockedByFn | None = None
_blocked_by_reason_impl: BlockedByReasonFn | None = None


def bind_entity_helpers(
    *,
    adopt: AdoptFn,
    blocked_by: BlockedByFn,
    blocked_by_reason: BlockedByReasonFn,
) -> None:
    """Core-only: register the real `adopt`/`blocked_by`/`blocked_by_reason`
    implementations, so the wrappers below can hand them out without
    `atlas_plugin_api` ever importing `server` or `atlas_plugin_ingestion`.
    Called once from `server.apps.catalog.plugin.register_runtime()`, during
    the shared runtime entry-point-loading phase, before any request is served.
    """
    global _adopt_impl, _blocked_by_impl, _blocked_by_reason_impl
    _adopt_impl = adopt
    _blocked_by_impl = blocked_by
    _blocked_by_reason_impl = blocked_by_reason


def adopt(instance: Any, request: Any, body: Any) -> None:
    if _adopt_impl is None:
        msg = (
            "adopt() called before Core registered its implementation via "
            "bind_entity_helpers() (server.apps.catalog.plugin.register_runtime() must run first)"
        )
        raise RuntimeError(msg)
    _adopt_impl(instance, request, body)


def blocked_by(instance: Any) -> str | None:
    if _blocked_by_impl is None:
        msg = (
            "blocked_by() called before Core registered its implementation via "
            "bind_entity_helpers() (server.apps.catalog.plugin.register_runtime() must run first)"
        )
        raise RuntimeError(msg)
    return _blocked_by_impl(instance)


def blocked_by_reason(instance: Any) -> str | None:
    if _blocked_by_reason_impl is None:
        msg = (
            "blocked_by_reason() called before Core registered its implementation via "
            "bind_entity_helpers() (server.apps.catalog.plugin.register_runtime() must run first)"
        )
        raise RuntimeError(msg)
    return _blocked_by_reason_impl(instance)
