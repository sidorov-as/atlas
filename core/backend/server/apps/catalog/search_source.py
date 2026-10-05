"""Catalog entities as searchable documents (`add-search-core`).

One document per active entity, id `<entity kind>:<entity uuid>`, so the search
kind is the entity kind (`component:…`) and the UI can filter and label by it.
`user` entities have no detail page to link to and are not indexed.

Visibility follows the catalog's existing read rule: any authenticated user
may read any entity (`SessionAuth` on the read routes, no ownership check).
`resolve` re-loads live rows, so entities removed or purged since indexing
are dropped even if the index is stale.
"""

from collections.abc import Iterable, Iterator, Sequence
from typing import Any
from uuid import UUID

from atlas_plugin_api import (
    KIND_API,
    KIND_COMPONENT,
    KIND_GROUP,
    KIND_RESOURCE,
    KIND_SYSTEM,
    STATUS_ACTIVE,
    SearchDocument,
    SearchHit,
    split_document_id,
)

from server.apps.catalog.models import CatalogEntity

# Mirrors the frontend's `kindToPath`; routes are `<prefix>/<entity id>`.
_LINK_PREFIX = {
    KIND_SYSTEM: "/systems",
    KIND_COMPONENT: "/components",
    KIND_RESOURCE: "/resources",
    KIND_API: "/apis",
    KIND_GROUP: "/teams",
}

_KIND_LABELS = {
    KIND_SYSTEM: "System",
    KIND_COMPONENT: "Component",
    KIND_RESOURCE: "Resource",
    KIND_API: "API",
    KIND_GROUP: "Group",
}


def _text(entity: CatalogEntity) -> str:
    return "\n\n".join(
        part for part in (entity.description, entity.documentation) if part
    )


def _document(entity: CatalogEntity) -> SearchDocument:
    return SearchDocument(
        id=f"{entity.kind}:{entity.pk}",
        kind=entity.kind,
        title=entity.name,
        body=_text(entity),
        summary=entity.description or None,
    )


def _pks(ids: Sequence[str]) -> list[UUID]:
    pks: list[UUID] = []
    for document_id in ids:
        try:
            kind, key = split_document_id(document_id)
            if kind in _LINK_PREFIX:
                pks.append(UUID(key))
        except ValueError:
            continue
    return pks


def _searchable():
    return CatalogEntity.objects.filter(
        status=STATUS_ACTIVE, kind__in=list(_LINK_PREFIX)
    )


class CatalogSearchSource:
    id = "atlas.catalog"
    kinds = tuple(_LINK_PREFIX)
    kind_labels = _KIND_LABELS

    @property
    def watched_models(self) -> tuple[str, ...]:
        return (CatalogEntity._meta.label,)

    def document_ids_for_instance(self, instance: Any) -> Iterable[str]:
        # Also for removed/deleted rows: `documents` then omits the id and the
        # indexer deletes it. State changes (remove, revive) are plain saves.
        if getattr(instance, "kind", None) not in _LINK_PREFIX:
            return []
        return [f"{instance.kind}:{instance.pk}"]

    def documents(self, ids: Sequence[str]) -> Iterable[SearchDocument]:
        return [
            _document(entity)
            for entity in _searchable().filter(pk__in=_pks(ids))
        ]

    def all_documents(self) -> Iterator[SearchDocument]:
        for entity in _searchable().iterator():
            yield _document(entity)

    def resolve(self, ids: Sequence[str], actor: Any) -> Sequence[SearchHit]:
        if not getattr(actor, "is_authenticated", False):
            return []
        return [
            SearchHit(
                id=f"{entity.kind}:{entity.pk}",
                kind=entity.kind,
                title=entity.name,
                link=f"{_LINK_PREFIX[entity.kind]}/{entity.pk}",
                text=_text(entity),
                summary=entity.description or None,
            )
            for entity in _searchable().filter(pk__in=_pks(ids))
        ]


catalog_search_source = CatalogSearchSource()
