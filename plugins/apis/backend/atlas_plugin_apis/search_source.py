"""API endpoints and operations as searchable documents (`add-search-sources`).

Two kinds from one source: `endpoint:<uuid>` (title `METHOD /path`) and
`operation:<uuid>` (title `direction channel`); the body holds the summary and
operation id. Only `active` rows are indexed, so a removed row disappears and a
restored one comes back as plain saves. Stored specification documents and
descriptions are deliberately not indexed.

API entities themselves are already covered by the catalog source. A hit shows
its owning API's name (in the hit title, the only text the dialog shows) from the live
entity at `resolve` time and links to the
endpoint or operation inside that API's page, so renaming an API needs no
reindex. Visibility follows the plugin's endpoint and operation read
permissions; `resolve` re-checks them and re-loads live rows, and also drops
rows whose API is no longer active.
"""

import re
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, ClassVar
from uuid import UUID

from atlas_plugin_api import (
    STATUS_ACTIVE,
    SearchDocument,
    SearchHit,
    get_policy_evaluator,
    split_document_id,
)

from .models import ApiEndpoint, ApiOperation
from .plugin import ENDPOINT_READ_PERMISSION, OPERATION_READ_PERMISSION

KIND_ENDPOINT = "endpoint"
KIND_OPERATION = "operation"


_NON_WORD = re.compile(r"[\W_]+")


def _words(text: str) -> str:
    """`/pets/{petId}` -> `pets petId`.

    PostgreSQL's text parser keeps paths and dotted names such as `/pets` or
    `orders.created` as one token, so a search for `pets` or `created` would
    miss them. The title is shown as is; this word-split copy goes into the
    body, where the engine tokenizes it.
    """
    return _NON_WORD.sub(" ", text).strip()


def _body(row: ApiEndpoint | ApiOperation) -> str:
    address = row.path if isinstance(row, ApiEndpoint) else row.channel_address
    return "\n".join(
        part for part in (_words(address), row.summary, row.operation_id) if part
    )


def _endpoint_title(endpoint: ApiEndpoint) -> str:
    return f"{endpoint.method} {endpoint.path}"


def _operation_title(operation: ApiOperation) -> str:
    return f"{operation.direction} {operation.channel_address}"


def _endpoint_document(endpoint: ApiEndpoint) -> SearchDocument:
    return SearchDocument(
        id=f"{KIND_ENDPOINT}:{endpoint.pk}",
        kind=KIND_ENDPOINT,
        title=_endpoint_title(endpoint),
        body=_body(endpoint),
        summary=endpoint.summary or None,
    )


def _operation_document(operation: ApiOperation) -> SearchDocument:
    return SearchDocument(
        id=f"{KIND_OPERATION}:{operation.pk}",
        kind=KIND_OPERATION,
        title=_operation_title(operation),
        body=_body(operation),
        summary=operation.summary or None,
    )


def _uuids(ids: Sequence[str], kind: str) -> list[UUID]:
    pks: list[UUID] = []
    for document_id in ids:
        try:
            id_kind, key = split_document_id(document_id)
            if id_kind == kind:
                pks.append(UUID(key))
        except ValueError:
            continue
    return pks


def _active_endpoints():
    return ApiEndpoint.objects.filter(status=ApiEndpoint.STATUS_ACTIVE)


def _active_operations():
    return ApiOperation.objects.filter(status=ApiOperation.STATUS_ACTIVE)


def _api_name(api: Any) -> str:
    return api.title or api.name


def _hit_title(title: str, api: Any) -> str:
    """The dialog shows only the title, so the live API name goes there."""
    return f"{title} — {_api_name(api)}"


class ApiSearchSource:
    id = "atlas.apis"
    kinds = (KIND_ENDPOINT, KIND_OPERATION)
    kind_labels: ClassVar[dict[str, str]] = {
        KIND_ENDPOINT: "Endpoint",
        KIND_OPERATION: "Operation",
    }

    @property
    def watched_models(self) -> tuple[str, ...]:
        return (ApiEndpoint._meta.label, ApiOperation._meta.label)

    def document_ids_for_instance(self, instance: Any) -> Iterable[str]:
        # Also for removed/deleted rows: `documents` then omits the id and the
        # indexer deletes it. Status changes (remove, restore) are plain saves.
        if isinstance(instance, ApiEndpoint):
            return [f"{KIND_ENDPOINT}:{instance.pk}"]
        if isinstance(instance, ApiOperation):
            return [f"{KIND_OPERATION}:{instance.pk}"]
        return []

    def documents(self, ids: Sequence[str]) -> Iterable[SearchDocument]:
        documents = [
            _endpoint_document(endpoint)
            for endpoint in _active_endpoints().filter(
                pk__in=_uuids(ids, KIND_ENDPOINT)
            )
        ]
        documents.extend(
            _operation_document(operation)
            for operation in _active_operations().filter(
                pk__in=_uuids(ids, KIND_OPERATION)
            )
        )
        return documents

    def all_documents(self) -> Iterator[SearchDocument]:
        for endpoint in _active_endpoints().iterator():
            yield _endpoint_document(endpoint)
        for operation in _active_operations().iterator():
            yield _operation_document(operation)

    def resolve(self, ids: Sequence[str], actor: Any) -> Sequence[SearchHit]:
        if not getattr(actor, "is_authenticated", False):
            return []
        evaluator = get_policy_evaluator()
        hits: list[SearchHit] = []
        if evaluator.check(actor, ENDPOINT_READ_PERMISSION, None):
            endpoints = (
                _active_endpoints()
                .filter(
                    pk__in=_uuids(ids, KIND_ENDPOINT),
                    api__status=STATUS_ACTIVE,
                )
                .select_related("api")
            )
            hits.extend(
                SearchHit(
                    id=f"{KIND_ENDPOINT}:{endpoint.pk}",
                    kind=KIND_ENDPOINT,
                    title=_hit_title(_endpoint_title(endpoint), endpoint.api),
                    link=f"/apis/{endpoint.api_id}/endpoints/{endpoint.pk}",
                    text=_body(endpoint),
                    summary=endpoint.summary or None,
                )
                for endpoint in endpoints
            )
        if evaluator.check(actor, OPERATION_READ_PERMISSION, None):
            operations = (
                _active_operations()
                .filter(
                    pk__in=_uuids(ids, KIND_OPERATION),
                    api__status=STATUS_ACTIVE,
                )
                .select_related("api")
            )
            hits.extend(
                SearchHit(
                    id=f"{KIND_OPERATION}:{operation.pk}",
                    kind=KIND_OPERATION,
                    title=_hit_title(_operation_title(operation), operation.api),
                    link=f"/apis/{operation.api_id}/operations/{operation.pk}",
                    text=_body(operation),
                    summary=operation.summary or None,
                )
                for operation in operations
            )
        return hits


api_search_source = ApiSearchSource()
