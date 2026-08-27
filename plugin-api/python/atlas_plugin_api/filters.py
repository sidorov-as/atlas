"""List-endpoint filtering shared by every kind's CRUD API
(`core-plugin-contract-surface` spec: "Core publishes its plugin-facing
surface as contract types").

`?owner=` is matched by parsing (not resolving) the ref, so a syntactically
valid ref for a Group that doesn't exist yields an empty list rather than an
error — only a malformed ref string is rejected.

`?system=`/`?type=`/`?lifecycle=` target a kind-specific `*Details` field
(`system`/`type`/`lifecycle` don't live on the shared `CatalogEntity` row),
so callers pass the ORM lookup `prefix` for the details relation to filter
through (e.g. `"component_details__"`); `owner` stays on `CatalogEntity`
itself and needs no prefix.

Needs only `refs.py`'s ref parser and a plain `QuerySet`, no Django
model/Core dependency, so it moves here outright, the same way `kinds.py`
did. `server.apps.catalog.api.filters` re-exports it for Core's own internal
call sites.
"""

from http import HTTPStatus

from django.db.models import Q, QuerySet
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from . import refs


def filter_by_owner(queryset: QuerySet, owner: str | None) -> QuerySet:
    if not owner:
        return queryset
    try:
        _kind, namespace, name = refs.parse_ref(owner, default_kind="group")
    except refs.RefError as exc:
        raise APIError(
            format_error(str(exc), error_type=ErrorType.value_error),
            status_code=HTTPStatus.BAD_REQUEST,
        ) from None
    return queryset.filter(owner__namespace=namespace, owner__name__iexact=name)


def filter_by_system(
    queryset: QuerySet, system: str | None, *, prefix: str = ""
) -> QuerySet:
    if not system:
        return queryset
    try:
        _kind, namespace, name = refs.parse_ref(system, default_kind="system")
    except refs.RefError as exc:
        raise APIError(
            format_error(str(exc), error_type=ErrorType.value_error),
            status_code=HTTPStatus.BAD_REQUEST,
        ) from None
    return queryset.filter(
        **{
            f"{prefix}system__namespace": namespace,
            f"{prefix}system__name__iexact": name,
        }
    )


def filter_by_team(queryset: QuerySet, team: str | None) -> QuerySet:
    if not team:
        return queryset
    try:
        _kind, namespace, name = refs.parse_ref(team, default_kind="group")
    except refs.RefError as exc:
        raise APIError(
            format_error(str(exc), error_type=ErrorType.value_error),
            status_code=HTTPStatus.BAD_REQUEST,
        ) from None
    return queryset.filter(
        system__owner__namespace=namespace, system__owner__name__iexact=name
    )


def filter_by_field(
    queryset: QuerySet, field: str, value: str | None, *, prefix: str = ""
) -> QuerySet:
    if not value:
        return queryset
    return queryset.filter(**{f"{prefix}{field}": value})


def filter_by_search(queryset: QuerySet, query: str | None) -> QuerySet:
    if not query:
        return queryset
    return queryset.filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(documentation__icontains=query),
    )


def filter_by_tags_overlap(queryset: QuerySet, tags: list[str]) -> QuerySet:
    if not tags:
        return queryset
    return queryset.filter(tags__overlap=tags)


def filter_by_status(queryset: QuerySet, status: str) -> QuerySet:
    """`entity-catalog` spec's "List filtering and search" requirement: default list/search
    views exclude `removed` entities; `?status=all` is the explicit, ungated opt-in any
    authenticated caller may request (`entity-removal-lifecycle`'s "hidden with an ungated
    toggle" requirement) — no separate `removed`-only value, since nothing asks for that view
    at the whole-entity level (unlike `ApiEndpoint`/`ApiOperation`'s own status filter)."""
    if status == "all":
        return queryset
    return queryset.filter(status="active")
