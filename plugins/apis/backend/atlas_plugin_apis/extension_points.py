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
- `link_endpoint()`/`unlink_endpoint()`/`link_operation()`/`unlink_operation()`: the one copy of
  the Service-to-Endpoint/Operation link rules, shared by the REST controllers (`source="ui"`)
  and `atlas_plugin_mcp`'s write tools (`source="mcp"`). Each takes the acting user and enforces
  the same dependency create/delete permission on the Service; failures raise `APIError`
  (`AlreadyLinkedError`/`NotLinkedError` are the two a batch caller treats as "no change").
- `find_endpoint()`/`find_operations()`: natural-key target resolution for those functions.
- `link_endpoints()`/`unlink_endpoints()`/`link_operations()`/`unlink_operations()`: the batch
  forms for `atlas_plugin_mcp`'s tools, one Service per call. Each item runs in its own
  savepoint and gets a status; `dry_run` rolls the whole batch back after computing them.
"""

import logging
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from http import HTTPStatus

from atlas_plugin_api import KIND_API, KIND_COMPONENT, CatalogEntity, dry_run
from atlas_plugin_api.refs import RefError, resolve_ref
from atlas_plugin_standard_catalog.extension_points import add_consumed_api
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.core.paginator import Page, Paginator
from django.db import transaction
from django.db.models import Q
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from .consumers import channel_participants, operation_provider_service
from .models import (
    ApiDetails,
    ApiEndpoint,
    ApiOperation,
    ServiceEndpointUsage,
    ServiceOperationUsage,
)
from .permissions import (
    check_endpoint_dependency_create_permission,
    check_endpoint_dependency_delete_permission,
    check_endpoint_dependency_read_permission,
    check_endpoint_read_permission,
    check_operation_dependency_create_permission,
    check_operation_dependency_delete_permission,
    check_operation_dependency_read_permission,
    check_operation_read_permission,
)
from .spec_fetch import resolve_api_spec_url

logger = logging.getLogger("atlas_plugin_apis")

__all__ = [
    "MAX_USAGE_BATCH_SIZE",
    "AlreadyLinkedError",
    "DeleteGuard",
    "DeleteGuardRegistry",
    "DuplicateDeleteGuardError",
    "NotLinkedError",
    "UsageBatchError",
    "UsageBatchResult",
    "UsageItem",
    "UsageItemResult",
    "delete_guards",
    "due_for_spec_refresh",
    "find_endpoint",
    "find_operations",
    "get_endpoint",
    "get_endpoint_consumers",
    "get_operation",
    "get_operation_consumers",
    "link_endpoint",
    "link_endpoints",
    "link_operation",
    "link_operations",
    "register_delete_guard",
    "resolve_endpoint",
    "resolve_endpoints",
    "resolve_operation",
    "resolve_operations",
    "run_delete_guards",
    "search_endpoints",
    "search_operations",
    "unlink_endpoint",
    "unlink_endpoints",
    "unlink_operation",
    "unlink_operations",
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
    aggregated exactly as `OperationConsumersController` does: every active Operation sharing its
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
            status=ApiOperation.STATUS_ACTIVE,
        ).select_related("api", "api__owner"),
    )
    return channel_participants(aggregated)


class AlreadyLinkedError(APIError):
    """409: the Service already holds this link. A batch caller reports `unchanged`."""

    def __init__(self, message: str) -> None:
        super().__init__(
            format_error(message, error_type=ErrorType.value_error),
            status_code=HTTPStatus.CONFLICT,
        )


class NotLinkedError(APIError):
    """404: the Service holds no such link. A batch caller reports `unchanged`."""

    def __init__(self, message: str) -> None:
        super().__init__(
            format_error(message, error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        )


def _conflict(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.value_error),
        status_code=HTTPStatus.CONFLICT,
    )


_YAML_MANAGED_MESSAGE = "This link is managed by ingestion and cannot be removed here"


def find_endpoint(api: CatalogEntity, method: str, path: str) -> ApiEndpoint | None:
    """The one `ApiEndpoint` of `api` with this `(method, path)`, or `None`. The key is unique
    across all rows, so there is at most one; `status` is not filtered, a removed Endpoint still
    resolves (linking to it is refused by `link_endpoint()`, unlinking is allowed)."""
    return (
        ApiEndpoint.objects.select_related("api")
        .filter(api=api, method=method.upper(), path=path)
        .first()
    )


def find_operations(
    api: CatalogEntity, channel_address: str, direction: str
) -> list[ApiOperation]:
    """The active `ApiOperation` rows of `api` on this channel and direction. The natural key is
    not unique (`(api, operation_key)` is), so more than one row may match; the caller decides
    what to do about that, this never picks one."""
    return list(
        ApiOperation.objects.select_related("api")
        .filter(
            api=api,
            channel_address=channel_address,
            direction=direction,
            status=ApiOperation.STATUS_ACTIVE,
        )
        .order_by("operation_key", "id")
    )


def link_endpoint(
    actor: AbstractBaseUser,
    service: CatalogEntity,
    endpoint: ApiEndpoint,
    source: str,
) -> tuple[ServiceEndpointUsage, bool]:
    """Link `service` to `endpoint`; returns the new row and whether `consumesAPI` gained the
    Endpoint's API as a side effect. Raises `APIError`: 403 without dependency create permission
    on `service`; 409 for a removed Endpoint; `AlreadyLinkedError` (409) for a duplicate."""
    check_endpoint_dependency_create_permission(actor, service)
    if endpoint.status == ApiEndpoint.STATUS_REMOVED:
        raise _conflict("This Endpoint has been removed and cannot receive new links")
    if ServiceEndpointUsage.objects.filter(endpoint=endpoint, service=service).exists():
        raise AlreadyLinkedError("This Service is already linked to this Endpoint")
    with transaction.atomic():
        usage = ServiceEndpointUsage.objects.create(
            endpoint=endpoint,
            service=service,
            created_by=actor,
            origin=ServiceEndpointUsage.ORIGIN_MANUAL,
            source=source,
        )
        api_relation_created = add_consumed_api(service, endpoint.api)
    return usage, api_relation_created


def unlink_endpoint(
    actor: AbstractBaseUser, service: CatalogEntity, endpoint: ApiEndpoint
) -> None:
    """Remove `service`'s link to `endpoint`. `consumesAPI` is left alone: the Service may still
    consume other Endpoints of the same API, or have a hand-authored `consumesAPI`. Raises
    `NotLinkedError` (404) with no such link; 403 without dependency delete permission; 409 for a
    `yaml`-origin link."""
    try:
        usage = ServiceEndpointUsage.objects.get(endpoint=endpoint, service=service)
    except ServiceEndpointUsage.DoesNotExist:
        raise NotLinkedError("Service is not linked to this Endpoint") from None
    check_endpoint_dependency_delete_permission(actor, service)
    if usage.origin == ServiceEndpointUsage.ORIGIN_YAML:
        raise _conflict(_YAML_MANAGED_MESSAGE)
    usage.delete()


def link_operation(
    actor: AbstractBaseUser,
    service: CatalogEntity,
    operation: ApiOperation,
    role: str,
    source: str,
) -> ServiceOperationUsage:
    """Link `service` to `operation` in `role`. Raises `APIError`: 403 without dependency create
    permission on `service`; 409 when `service` is the Operation's own document owner;
    `AlreadyLinkedError` (409) for a duplicate `(operation, service, role)`."""
    check_operation_dependency_create_permission(actor, service)
    provider = operation_provider_service(operation.api)
    if provider is not None and provider.id == service.id:
        raise _conflict(
            "This Service is the Operation's own document owner — its role is "
            "already implied by the Operation's direction and cannot be linked",
        )
    if ServiceOperationUsage.objects.filter(
        operation=operation, service=service, role=role
    ).exists():
        raise AlreadyLinkedError(
            "This Service is already linked to this Operation with this role"
        )
    return ServiceOperationUsage.objects.create(
        operation=operation,
        service=service,
        role=role,
        created_by=actor,
        origin=ServiceOperationUsage.ORIGIN_MANUAL,
        source=source,
    )


def unlink_operation(
    actor: AbstractBaseUser,
    service: CatalogEntity,
    operation: ApiOperation,
    role: str,
) -> None:
    """Remove only the `(operation, service, role)` row; a Service holding both roles keeps the
    other. Raises `NotLinkedError` (404) with no such row; 403 without dependency delete
    permission; 409 for a `yaml`-origin row."""
    try:
        usage = ServiceOperationUsage.objects.get(
            operation=operation, service=service, role=role
        )
    except ServiceOperationUsage.DoesNotExist:
        raise NotLinkedError(
            "Service is not linked to this Operation with this role"
        ) from None
    check_operation_dependency_delete_permission(actor, service)
    if usage.origin == ServiceOperationUsage.ORIGIN_YAML:
        raise _conflict(_YAML_MANAGED_MESSAGE)
    usage.delete()


MAX_USAGE_BATCH_SIZE = 200
"""Most items a single batch call accepts. Each item costs a handful of queries and the response
carries a result per item; a caller with more sends several calls, which are safe to repeat."""

STATUS_CREATED = "created"
STATUS_REMOVED = "removed"
STATUS_UNCHANGED = "unchanged"
STATUS_NOT_FOUND = "not_found"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_CONFLICT = "conflict"
STATUS_INVALID = "invalid"

_ROLES = (ServiceOperationUsage.ROLE_PUBLISHER, ServiceOperationUsage.ROLE_SUBSCRIBER)
_METHODS = {value for value, _label in ApiEndpoint.METHOD_CHOICES}
_DIRECTIONS = {value for value, _label in ApiOperation.DIRECTION_CHOICES}


class UsageBatchError(APIError):
    """400: the whole request is rejected and no item is processed."""

    def __init__(self, message: str) -> None:
        super().__init__(
            format_error(message, error_type=ErrorType.value_error),
            status_code=HTTPStatus.BAD_REQUEST,
        )


@dataclass(frozen=True)
class UsageItem:
    """One batch item. A target is named by exactly one of `endpoint_id`/`operation_id` or the
    complete natural key (`api` ref + `method`/`path` for an Endpoint, `api` ref +
    `channel_address`/`direction` for an Operation). `role` applies to Operation items only."""

    endpoint_id: str | None = None
    operation_id: str | None = None
    api: str | None = None
    method: str | None = None
    path: str | None = None
    channel_address: str | None = None
    direction: str | None = None
    role: str | None = None


@dataclass
class UsageItemResult:
    status: str
    message: str | None = None
    endpoint_id: str | None = None
    operation_id: str | None = None
    candidates: list[str] = field(default_factory=list)
    api_relation_created: bool | None = None


@dataclass
class UsageBatchResult:
    items: list[UsageItemResult]
    counts: dict[str, int]
    dry_run: bool = False
    warnings: list[str] = field(default_factory=list)


class _ItemOutcome(Exception):
    """Stops one item with a final non-success result."""

    def __init__(self, result: UsageItemResult) -> None:
        super().__init__(result.status)
        self.result = result


def _outcome(status: str, message: str, **extra) -> _ItemOutcome:
    return _ItemOutcome(UsageItemResult(status=status, message=message, **extra))


def _error_message(error: APIError) -> str:
    """The human message inside an `APIError`'s `format_error` payload."""
    data = error.raw_data
    try:
        return str(data["detail"][0]["msg"])
    except (KeyError, IndexError, TypeError):
        return str(data)


def _check_batch(service: CatalogEntity, items: list[UsageItem]) -> None:
    if service.kind != KIND_COMPONENT:
        raise UsageBatchError(
            f"{service.ref} is a {service.kind}; only a Component (Service) can be linked"
        )
    if not items:
        raise UsageBatchError("At least one item is required")
    if len(items) > MAX_USAGE_BATCH_SIZE:
        raise UsageBatchError(
            f"A batch holds at most {MAX_USAGE_BATCH_SIZE} items; got {len(items)}. "
            "Split it into several calls."
        )


def _resolve_api(ref: str) -> CatalogEntity:
    try:
        return resolve_ref(ref, expected_kind=KIND_API)
    except RefError as exc:
        text = str(exc)
        if text.startswith("No "):
            raise _outcome(STATUS_NOT_FOUND, f"API not found: {ref!r}") from None
        raise _outcome(STATUS_INVALID, text) from None


def _set_fields(item: UsageItem, names: tuple[str, ...]) -> list[str]:
    return [name for name in names if getattr(item, name) not in (None, "")]


def _resolve_endpoint_target(item: UsageItem) -> ApiEndpoint:
    key = ("api", "method", "path")
    id_given = item.endpoint_id not in (None, "")
    given = _set_fields(item, key)
    if id_given and given:
        raise _outcome(
            STATUS_INVALID, "Give either endpoint_id or api, method and path, not both"
        )
    if id_given:
        found = resolve_endpoint(item.endpoint_id)
        if found is None:
            raise _outcome(STATUS_NOT_FOUND, f"Endpoint not found: {item.endpoint_id}")
        return found
    if not given:
        raise _outcome(
            STATUS_INVALID, "Give endpoint_id, or api, method and path together"
        )
    if len(given) != len(key):
        missing = ", ".join(name for name in key if name not in given)
        raise _outcome(STATUS_INVALID, f"Incomplete endpoint key; missing {missing}")
    method = str(item.method).upper()
    if method not in _METHODS:
        raise _outcome(STATUS_INVALID, f"Unknown method {item.method!r}")
    api = _resolve_api(str(item.api))
    found = find_endpoint(api, method, str(item.path))
    if found is None:
        raise _outcome(
            STATUS_NOT_FOUND, f"No endpoint {method} {item.path} on {item.api}"
        )
    return found


def _resolve_operation_target(item: UsageItem) -> ApiOperation:
    key = ("api", "channel_address", "direction")
    id_given = item.operation_id not in (None, "")
    given = _set_fields(item, key)
    if id_given and given:
        raise _outcome(
            STATUS_INVALID,
            "Give either operation_id or api, channel_address and direction, not both",
        )
    if id_given:
        found = resolve_operation(item.operation_id)
        if found is None:
            raise _outcome(
                STATUS_NOT_FOUND, f"Operation not found: {item.operation_id}"
            )
        return found
    if not given:
        raise _outcome(
            STATUS_INVALID,
            "Give operation_id, or api, channel_address and direction together",
        )
    if len(given) != len(key):
        missing = ", ".join(name for name in key if name not in given)
        raise _outcome(STATUS_INVALID, f"Incomplete operation key; missing {missing}")
    if item.direction not in _DIRECTIONS:
        raise _outcome(STATUS_INVALID, f"Unknown direction {item.direction!r}")
    api = _resolve_api(str(item.api))
    matches = find_operations(api, str(item.channel_address), str(item.direction))
    if not matches:
        raise _outcome(
            STATUS_NOT_FOUND,
            f"No active operation {item.direction} {item.channel_address} on {item.api}",
        )
    if len(matches) > 1:
        raise _outcome(
            STATUS_AMBIGUOUS,
            f"{len(matches)} operations match; retry with operation_id",
            candidates=[str(match.id) for match in matches],
        )
    return matches[0]


def _check_role(item: UsageItem) -> str:
    if item.role not in _ROLES:
        raise _outcome(STATUS_INVALID, "role must be 'publisher' or 'subscriber'")
    return item.role


def _run_batch(
    items: list[UsageItem],
    process: Callable[[UsageItem], UsageItemResult],
    dry: bool,
) -> UsageBatchResult:
    def run() -> list[UsageItemResult]:
        results = []
        for item in items:
            try:
                with transaction.atomic():
                    results.append(process(item))
            except _ItemOutcome as outcome:
                results.append(outcome.result)
        return results

    warnings: list[str] = []
    if dry:
        with dry_run() as context:
            results = run()
        warnings = list(context.warnings)
    else:
        results = run()
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    return UsageBatchResult(
        items=results, counts=counts, dry_run=dry, warnings=warnings
    )


def link_endpoints(
    actor: AbstractBaseUser,
    service: CatalogEntity,
    items: list[UsageItem],
    source: str,
    dry: bool = False,
) -> UsageBatchResult:
    """Link `service` to every Endpoint in `items`, one savepoint and one result per item, in
    request order. Raises `APIError` for the whole request: 400 (`UsageBatchError`) for a
    non-Component, an empty batch or one over `MAX_USAGE_BATCH_SIZE`; 403 without dependency
    create permission on `service`."""
    _check_batch(service, items)
    check_endpoint_dependency_create_permission(actor, service)

    def process(item: UsageItem) -> UsageItemResult:
        endpoint = _resolve_endpoint_target(item)
        try:
            _, api_relation_created = link_endpoint(actor, service, endpoint, source)
        except AlreadyLinkedError:
            return UsageItemResult(STATUS_UNCHANGED, endpoint_id=str(endpoint.id))
        except APIError as error:
            if error.status_code != HTTPStatus.CONFLICT:
                raise
            raise _outcome(
                STATUS_CONFLICT, _error_message(error), endpoint_id=str(endpoint.id)
            ) from None
        return UsageItemResult(
            STATUS_CREATED,
            endpoint_id=str(endpoint.id),
            api_relation_created=api_relation_created,
        )

    return _run_batch(items, process, dry)


def unlink_endpoints(
    actor: AbstractBaseUser,
    service: CatalogEntity,
    items: list[UsageItem],
    dry: bool = False,
) -> UsageBatchResult:
    """The unlink counterpart of `link_endpoints()`; requires dependency delete permission.
    A removed Endpoint can still be unlinked."""
    _check_batch(service, items)
    check_endpoint_dependency_delete_permission(actor, service)

    def process(item: UsageItem) -> UsageItemResult:
        endpoint = _resolve_endpoint_target(item)
        try:
            unlink_endpoint(actor, service, endpoint)
        except NotLinkedError:
            return UsageItemResult(STATUS_UNCHANGED, endpoint_id=str(endpoint.id))
        except APIError as error:
            if error.status_code != HTTPStatus.CONFLICT:
                raise
            raise _outcome(
                STATUS_CONFLICT, _error_message(error), endpoint_id=str(endpoint.id)
            ) from None
        return UsageItemResult(STATUS_REMOVED, endpoint_id=str(endpoint.id))

    return _run_batch(items, process, dry)


def link_operations(
    actor: AbstractBaseUser,
    service: CatalogEntity,
    items: list[UsageItem],
    source: str,
    dry: bool = False,
) -> UsageBatchResult:
    """Link `service` to every Operation in `items` with each item's `role`. Same shape, errors
    and per-item statuses as `link_endpoints()`, plus `ambiguous` for an Operation key matching
    several active Operations; never changes the Service's `consumesAPI`."""
    _check_batch(service, items)
    check_operation_dependency_create_permission(actor, service)

    def process(item: UsageItem) -> UsageItemResult:
        role = _check_role(item)
        operation = _resolve_operation_target(item)
        try:
            link_operation(actor, service, operation, role, source)
        except AlreadyLinkedError:
            return UsageItemResult(STATUS_UNCHANGED, operation_id=str(operation.id))
        except APIError as error:
            if error.status_code != HTTPStatus.CONFLICT:
                raise
            raise _outcome(
                STATUS_CONFLICT, _error_message(error), operation_id=str(operation.id)
            ) from None
        return UsageItemResult(STATUS_CREATED, operation_id=str(operation.id))

    return _run_batch(items, process, dry)


def unlink_operations(
    actor: AbstractBaseUser,
    service: CatalogEntity,
    items: list[UsageItem],
    dry: bool = False,
) -> UsageBatchResult:
    """The unlink counterpart of `link_operations()`; removes only each item's role."""
    _check_batch(service, items)
    check_operation_dependency_delete_permission(actor, service)

    def process(item: UsageItem) -> UsageItemResult:
        role = _check_role(item)
        operation = _resolve_operation_target(item)
        try:
            unlink_operation(actor, service, operation, role)
        except NotLinkedError:
            return UsageItemResult(STATUS_UNCHANGED, operation_id=str(operation.id))
        except APIError as error:
            if error.status_code != HTTPStatus.CONFLICT:
                raise
            raise _outcome(
                STATUS_CONFLICT, _error_message(error), operation_id=str(operation.id)
            ) from None
        return UsageItemResult(STATUS_REMOVED, operation_id=str(operation.id))

    return _run_batch(items, process, dry)


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
