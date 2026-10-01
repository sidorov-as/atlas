"""`atlas_plugin_apis`'s cross-plugin function/registration surface
distinct from `contracts.py`'s types-only surface (no Django models or
business logic). The two ORM-backed plugin-to-plugin edges here "can't be fixed by moving types
into a contract package, since Django ORM querying needs the real model
class", so each gets a narrow function/registration surface instead,
letting `atlas_plugin_apis` keep sole ownership of `ApiDetails`'s ORM
queries while still giving other plugins something real to call:

- `due_for_spec_refresh()`: `atlas_plugin_ingestion`'s periodic job calls
  this instead of importing `atlas_plugin_apis.models`/`.spec_fetch`
  directly. Chosen as a function rather than an extension point because
  this is `ingestion`'s own background job pulling data on its own
  schedule, not reacting to an event `atlas_plugin_apis` would need to
  publish.
- `register_delete_guard`/`run_delete_guards`: an ADR 0014-style extension
  point (same keyed-registry shape as `atlas_plugin_ingestion.
  extension_points`'s `connectors`/`parsers`), reused here so a plugin
  that keeps its own reference to an API entity
  (`atlas_plugin_standard_catalog`'s `ComponentDetails.provides_apis`/
  `consumes_apis`) can register a delete-time check without
  `atlas_plugin_apis` importing that plugin's models directly.
- `resolve_endpoint()`/`resolve_operation()`: `atlas_plugin_flows.models.validate_steps()` calls
  these to resolve a step's `query_ref.endpoint`/`event_ref.operation`
  without importing `ApiEndpoint`/`ApiOperation` directly. Plain functions,
  like `due_for_spec_refresh()`, not a registry — this is a one-shot lookup
  by id, not a plugin registering a hook. Each returns `None` rather than
  raising on a not-found/malformed id, so the caller (which already knows
  how to raise its own `StepValidationError`) decides how to report it.
- `resolve_endpoints()`/`resolve_operations()`: the batched counterparts of
  `resolve_endpoint()`/`resolve_operation()`, for `atlas_plugin_flows`'s
  read-time stale-reference indicator — a Flow read resolves every step's
  `query_ref`/`event_ref` id in one `filter(pk__in=...)` call per kind
  rather than one `resolve_endpoint()`/`resolve_operation()` call per step
  (an N+1 pattern for a Flow with many such steps).
- `search_endpoints()`/`search_operations()`/`get_endpoint_consumers()`/`get_operation_consumers()`:
  read-only search and consumer lookups for `atlas_plugin_mcp`'s curated API tools. Unlike
  `resolve_*`, each takes the acting user and enforces the same `permissions.py` read check its
  REST controller counterpart does, so the caller can't forget it.
"""

import logging
import uuid
from collections.abc import Callable, Iterable

from atlas_plugin_api import CatalogEntity
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.core.paginator import Page, Paginator
from django.db.models import Q

from .consumers import channel_participants
from .models import (
    ApiDetails,
    ApiEndpoint,
    ApiOperation,
    ServiceEndpointUsage,
)
from .permissions import (
    check_endpoint_dependency_read_permission,
    check_endpoint_read_permission,
    check_operation_dependency_read_permission,
    check_operation_read_permission,
)
from .spec_fetch import resolve_api_spec_url

logger = logging.getLogger("atlas_plugin_apis")

__all__ = [
    "DeleteGuard",
    "DeleteGuardRegistry",
    "DuplicateDeleteGuardError",
    "delete_guards",
    "due_for_spec_refresh",
    "get_endpoint",
    "get_endpoint_consumers",
    "get_operation",
    "get_operation_consumers",
    "register_delete_guard",
    "resolve_endpoint",
    "resolve_endpoints",
    "resolve_operation",
    "resolve_operations",
    "run_delete_guards",
    "search_endpoints",
    "search_operations",
]


def _valid_uuids(ids: Iterable[object]) -> list[str]:
    """Filters `ids` down to the ones that parse as a UUID, deduplicated and stringified —
    so a batched `filter(pk__in=...)` never raises on a malformed id the way a bare
    queryset filter would."""
    valid: set[str] = set()
    for candidate in ids:
        try:
            valid.add(str(uuid.UUID(str(candidate))))
        except (ValueError, AttributeError, TypeError):
            continue
    return list(valid)


def due_for_spec_refresh() -> None:
    """Refresh every URL-sourced API spec that's due for its periodic re-check
    the ORM query, the fetch, and the save all
    stay inside `atlas_plugin_apis`, so `atlas_plugin_ingestion`'s periodic
    job never needs to import `ApiDetails`/`spec_fetch` directly.

    One API's fetch failing is caught and logged so it doesn't block the
    others; `resolve_api_spec_url` itself never raises for a fetch failure —
    it flags `spec_resolve_failed` and leaves `spec_content` untouched
    instead.
    """
    for details in ApiDetails.objects.filter(
        spec_source=ApiDetails.SPEC_SOURCE_URL
    ).select_related("entity"):
        try:
            resolve_api_spec_url(details)
            details.save(
                update_fields=[
                    "spec_content",
                    "spec_resolved_at",
                    "spec_resolve_failed",
                ]
            )
        except Exception:
            logger.exception(
                "Failed to refresh spec_url for API %s", details.entity.name
            )


def resolve_endpoint(endpoint_id) -> ApiEndpoint | None:
    """Resolve an Endpoint id to its `ApiEndpoint` row (with `.api` pre-fetched
    via `select_related`), for a Flow step's `query_ref.endpoint`

    Returns `None` for both a nonexistent id and a malformed one (not a
    valid UUID) — `validate_steps()` treats both as "doesn't resolve" and
    raises its own `StepValidationError`, so this never raises. A `removed`
    Endpoint still resolves — status filtering is the caller's business,
    not this lookup's.
    """
    try:
        return ApiEndpoint.objects.select_related("api").get(pk=endpoint_id)
    except (ApiEndpoint.DoesNotExist, ValidationError, ValueError, TypeError):
        return None


def resolve_operation(operation_id) -> ApiOperation | None:
    """Resolve an Operation id to its `ApiOperation` row — mirrors
    `resolve_endpoint()` exactly for a Flow step's `event_ref.operation`."""
    try:
        return ApiOperation.objects.select_related("api").get(pk=operation_id)
    except (ApiOperation.DoesNotExist, ValidationError, ValueError, TypeError):
        return None


def resolve_endpoints(endpoint_ids: Iterable[object]) -> dict[str, ApiEndpoint]:
    """Batch-resolve Endpoint ids to their rows, keyed by `str(id)` — the N+1-avoiding
    counterpart to `resolve_endpoint()` for a Flow's read-time stale-reference indicator
    One `filter(pk__in=...)` call
    regardless of how many ids are passed. An id that doesn't resolve (deleted, or
    malformed) is simply absent from the result rather than raising."""
    return {
        str(endpoint.id): endpoint
        for endpoint in ApiEndpoint.objects.filter(pk__in=_valid_uuids(endpoint_ids))
    }


def resolve_operations(operation_ids: Iterable[object]) -> dict[str, ApiOperation]:
    """Mirrors `resolve_endpoints()` exactly, for Operation ids."""
    return {
        str(operation.id): operation
        for operation in ApiOperation.objects.filter(pk__in=_valid_uuids(operation_ids))
    }


def _scoped_to_api(queryset, api_id):
    """Narrows `queryset` to one API; a malformed `api_id` matches nothing rather than raising."""
    if api_id is None:
        return queryset
    valid = _valid_uuids([api_id])
    return queryset.filter(api_id=valid[0]) if valid else queryset.none()


def search_endpoints(
    actor: AbstractBaseUser,
    query: str = "",
    api_id=None,
    page: int = 1,
    page_size: int = 20,
) -> Page:
    """Page of active `ApiEndpoint` rows (with `.api` pre-fetched) matching `query` against
    path/summary/operation id — across every API, or only `api_id`'s when given. Mirrors
    `ApiEndpointSearchController`'s query shape. Raises `APIError` (403) without endpoint read
    permission; raises `EmptyPage` for an out-of-range `page`, like the REST controller."""
    check_endpoint_read_permission(actor)
    queryset = _scoped_to_api(
        ApiEndpoint.objects.filter(status=ApiEndpoint.STATUS_ACTIVE).select_related(
            "api"
        ),
        api_id,
    )
    if query:
        queryset = queryset.filter(
            Q(path__icontains=query)
            | Q(summary__icontains=query)
            | Q(operation_id__icontains=query),
        )
    return Paginator(queryset, page_size).page(page)


def search_operations(
    actor: AbstractBaseUser,
    query: str = "",
    api_id=None,
    page: int = 1,
    page_size: int = 20,
) -> Page:
    """Mirrors `search_endpoints()` for `ApiOperation`, matching `query` against channel
    address/summary/operation id; gated on operation read permission."""
    check_operation_read_permission(actor)
    queryset = _scoped_to_api(
        ApiOperation.objects.filter(status=ApiOperation.STATUS_ACTIVE).select_related(
            "api"
        ),
        api_id,
    )
    if query:
        queryset = queryset.filter(
            Q(channel_address__icontains=query)
            | Q(summary__icontains=query)
            | Q(operation_id__icontains=query),
        )
    return Paginator(queryset, page_size).page(page)


def get_endpoint(actor: AbstractBaseUser, endpoint_id) -> ApiEndpoint | None:
    """`resolve_endpoint()` gated on endpoint read permission — for a caller reading one
    Endpoint on a user's behalf rather than resolving a stored reference. `None` if it doesn't
    resolve; a `removed` Endpoint still resolves. Raises `APIError` (403) without permission."""
    check_endpoint_read_permission(actor)
    return resolve_endpoint(endpoint_id)


def get_operation(actor: AbstractBaseUser, operation_id) -> ApiOperation | None:
    """Mirrors `get_endpoint()` for an Operation, gated on operation read permission."""
    check_operation_read_permission(actor)
    return resolve_operation(operation_id)


def get_endpoint_consumers(
    actor: AbstractBaseUser, endpoint_id
) -> list[CatalogEntity] | None:
    """The Services explicitly linked to an Endpoint via `ServiceEndpointUsage` (with `.owner`
    pre-fetched), ordered by title then name — never the coarser Component-level `consumesApi`
    relation. `None` if `endpoint_id` doesn't resolve (see `resolve_endpoint()`); `[]` if it
    resolves with no links. Raises `APIError` (403) without endpoint dependency read
    permission."""
    check_endpoint_dependency_read_permission(actor)
    endpoint = resolve_endpoint(endpoint_id)
    if endpoint is None:
        return None
    usages = (
        ServiceEndpointUsage.objects.filter(endpoint=endpoint)
        .select_related("service", "service__owner")
        .order_by("service__title", "service__name")
    )
    return [usage.service for usage in usages]


def get_operation_consumers(
    actor: AbstractBaseUser, operation_id
) -> list[tuple[CatalogEntity, str]] | None:
    """`(service, role)` pairs (`role` is `publisher`/`subscriber`) for an Operation's channel,
    aggregated exactly as `OperationConsumersController` does: every Operation sharing its
    channel address contributes its document-owning Service's implied role, plus every explicit
    `ServiceOperationUsage` link. `None` if `operation_id` doesn't resolve. Raises `APIError`
    (403) without operation dependency read permission."""
    check_operation_dependency_read_permission(actor)
    operation = resolve_operation(operation_id)
    if operation is None:
        return None
    aggregated = list(
        ApiOperation.objects.filter(
            channel_address=operation.channel_address,
        ).select_related("api", "api__owner"),
    )
    return channel_participants(aggregated)


DeleteGuard = Callable[[CatalogEntity], None]


class DuplicateDeleteGuardError(ValueError):
    """Raised when a second registration tries to claim an already-registered owner id."""

    def __init__(self, owner: str) -> None:
        super().__init__(
            f"A delete guard for atlas_plugin_apis is already registered by owner={owner!r}"
        )
        self.owner = owner


class DeleteGuardRegistry:
    """Maps a registering plugin id to its delete guard for the `api` kind —
    same shape as `atlas_plugin_api.kinds.EntityKindRegistry`/`atlas_plugin_
    ingestion.extension_points.KeyedExtensionPoint`, so tests that run real
    runtime hooks repeatedly (`server.apps.plugins.tests.test_composition`)
    can swap in a fresh instance the same way they already do for those.
    """

    def __init__(self) -> None:
        self._guards: dict[str, DeleteGuard] = {}

    def register(self, owner: str, guard: DeleteGuard) -> None:
        if owner in self._guards:
            raise DuplicateDeleteGuardError(owner)
        self._guards[owner] = guard

    def run(self, entity: CatalogEntity) -> None:
        """Run every registered guard against `entity`, in registration order."""
        for guard in self._guards.values():
            guard(entity)


# Process-wide registry populated by the runtime entry-point-loading phase —
# one registry for the whole process, matching `atlas_plugin_api.kinds.registry`.
delete_guards = DeleteGuardRegistry()


def register_delete_guard(owner: str, guard: DeleteGuard) -> None:
    """Register `guard`, called with the `api`-kind entity being deleted.

    `owner` identifies the registering plugin (used only for the
    duplicate-registration error message); each plugin registers at most
    one guard.
    """
    delete_guards.register(owner, guard)


def run_delete_guards(entity: CatalogEntity) -> None:
    """Run every registered guard against `entity` (see `DeleteGuardRegistry.run`).

    Called by `ApiKindHandler.validate_delete`; a guard raises
    `ValidateDeleteError` to veto the delete.
    """
    delete_guards.run(entity)
