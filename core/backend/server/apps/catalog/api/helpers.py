"""Shared entity-controller helpers, used by both
`server.apps.catalog`'s own controllers (API, Tag, ArchitectureRelationship,
diagrams) and the Standard Catalog plugin's
(System/Component/Resource/Group/Actor).

Most of this re-exports `atlas_plugin_api.entity_helpers` — canonical home
moved there, since it needs
no `server`/plugin-specific import. Kept as same-named re-exports so Core's
own internal call sites (`api/views.py`) don't need to change.

`adopt`/`blocked_by`/`resolve_adopt_repository` stay here rather than moving:
they need Core's own `EntityWritePermission` and a conditionally-installed
plugin (`atlas_plugin_ingestion`), neither of which the shared
`atlas_plugin_api` contract package may depend on. Instead, `plugin.py`'s
`register_runtime()` hands these real implementations to
`atlas_plugin_api.bind_entity_helpers()`, so a plugin calling
`atlas_plugin_api.adopt()`/`blocked_by()` reaches them without
`atlas_plugin_api` ever importing `server` or `atlas_plugin_ingestion`
(mirroring `entity_service.py`'s `bind_entity_service()` pattern).
"""

from http import HTTPStatus
from typing import TYPE_CHECKING

from atlas_plugin_api.controllers import AtlasController
from atlas_plugin_api.entity_helpers import (
    API_VERSION,
    FORBIDDEN_RESPONSE,
    delete_blocked,
    entity_capabilities,
    ingested_from,
    metadata_out,
    not_found,
    relations_out,
    spec_owner_ref,
    tag_colors,
)
from django.apps import apps as django_apps
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from .permissions import EntityWritePermission

if TYPE_CHECKING:
    from atlas_plugin_ingestion.models import RegisteredRepository

__all__ = [
    "API_VERSION",
    "FORBIDDEN_RESPONSE",
    "AtlasController",
    "adopt",
    "blocked_by",
    "blocked_by_reason",
    "delete_blocked",
    "entity_capabilities",
    "ingested_from",
    "metadata_out",
    "not_found",
    "relations_out",
    "resolve_adopt_repository",
    "spec_owner_ref",
    "tag_colors",
]

# `atlas.ingestion` is a real, deselectable plugin —
# its Django app, and therefore `atlas_plugin_ingestion.models`, may not be
# installed. Every function below that touches its models imports them
# lazily, guarded by this check, rather than at module level: this module is
# imported by every other plugin's read/write views, so an
# eager import here would crash them all whenever ingestion is deselected.
#
# A manifest that omits `atlas.ingestion` entirely still force-installs its
# Django app (Core's own `ingested_from` FK needs it — `generate.py`'s
# `CORE_REQUIRED_PLUGIN_ID`) and falls back to `disabled`, so
# `apps.is_installed` alone would read True even when the plugin isn't
# really active. Checking `DISABLED_PLUGINS` too treats "disabled" the same
# as "unavailable" here — conflict-checking and repository adoption are
# ingestion-provided capabilities, and disabling suppresses a plugin's
# contributions, so these should go inert right
# alongside them.
INGESTION_APP_NAME = "atlas_plugin_ingestion"
INGESTION_PLUGIN_ID = "atlas.ingestion"


def _ingestion_available() -> bool:
    from server.settings.selected_plugins import DISABLED_PLUGINS

    return (
        django_apps.is_installed(INGESTION_APP_NAME)
        and INGESTION_PLUGIN_ID not in DISABLED_PLUGINS
    )


def _active_conflict(instance):
    if not _ingestion_available():
        return None
    from atlas_plugin_ingestion.models import ConflictRecord

    return (
        ConflictRecord.objects.filter(
            kind=instance.kind,
            namespace=instance.namespace,
            name__iexact=instance.name,
            is_active=True,
        )
        .order_by("-last_seen")
        .first()
    )


def blocked_by(instance) -> str | None:
    """The repo, if any, whose YAML claim is currently rejected because this
    entity holds the ref."""
    conflict = _active_conflict(instance)
    return conflict.repo_full_name if conflict else None


def blocked_by_reason(instance) -> str | None:
    """The `ConflictRecord.reason`
    (`manual_entity`/`other_repository`/`removed_entity`) behind
    `blocked_by`, so the frontend conflict banner can render a
    reason-specific message (the
    `removed_entity` reason must say "revive or purge", distinct from the
    existing reasons' "adopt to resolve")."""
    conflict = _active_conflict(instance)
    return conflict.reason if conflict else None


def resolve_adopt_repository(repository: str) -> "RegisteredRepository":
    """`repository` is `"<source_id>/<path>"` (matches
    `RegisteredRepository.__str__`) — a `RegisteredRepository` no longer has
    a single unique-by-itself field to adopt by, since `source_id` and `path`
    only jointly identify it
    (models.py's `unique_registered_repository_source_path` constraint),
    following the `source_id`/`path` schema change
    """
    if not _ingestion_available():
        raise APIError(
            format_error(
                "Repository adoption is unavailable: the ingestion plugin "
                "is not active",
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )
    from atlas_plugin_ingestion.models import RegisteredRepository

    source_id, _, path = repository.partition("/")
    if not path:
        raise APIError(
            format_error(
                f"Unknown repository: {repository!r}",
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )
    try:
        return RegisteredRepository.objects.get(source_id=source_id, path=path)
    except RegisteredRepository.DoesNotExist:
        raise APIError(
            format_error(
                f"Unknown repository: {repository!r}",
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        ) from None


def adopt(instance, request, body) -> None:
    EntityWritePermission.check_adopt(request.user, instance)
    instance.source_kind = instance.SOURCE_YAML
    instance.ingested_from = resolve_adopt_repository(body.repository)
    instance.save(update_fields=["source_kind", "ingested_from", "updated_at"])
