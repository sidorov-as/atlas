"""Database schemas as searchable documents (`add-search-sources`).

One document per schema facet, id `schema:<owning entity uuid>`. The title is
the owning resource's name, taken from the live entity, so the source also
watches catalog entities: renaming the owner refreshes its schema document. The
body holds table and column names flattened from the parsed structure; raw SQL
is never indexed. A schema whose parse failed keeps its title only.

A hit opens the owning resource's schema tab as a whole, never a table or
column. `resolve` follows the facet endpoint's read rules: the owner must be an
active entity of a kind that hosts schemas (`schema.host.v1`), and any
authenticated user may read it.
"""

import re
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, ClassVar
from uuid import UUID

from atlas_plugin_api import (
    SCHEMA_HOST_V1,
    STATUS_ACTIVE,
    Ok,
    SearchDocument,
    SearchHit,
    get_catalog_entity_model,
    resolve_capability,
    split_document_id,
)

from .models import DatabaseSchema

KIND_SCHEMA = "schema"

_NON_WORD = re.compile(r"[\W_]+")


def _name_terms(name: str) -> list[str]:
    """A name plus its word parts: `order_items` -> `order_items`, `order items`.

    The exact name stays searchable and so do its parts, which PostgreSQL's
    parser would otherwise keep glued together.
    """
    words = _NON_WORD.sub(" ", name).strip()
    return [name, words] if words and words != name else [name]


def flatten_schema_text(parsed_schema: object) -> str:
    """Table and column names of a parsed schema, one table per line.

    Reads only `tables[].name` and `tables[].columns[].name` of the parser's
    structure, whose shape is internal and provisional; keeping that knowledge
    in this one function means a shape change breaks its test, not search.
    Anything unexpected is skipped rather than raised.
    """
    if not isinstance(parsed_schema, dict):
        return ""
    tables = parsed_schema.get("tables")
    if not isinstance(tables, list):
        return ""
    lines: list[str] = []
    for table in tables:
        if not isinstance(table, dict):
            continue
        terms: list[str] = []
        name = table.get("name")
        if isinstance(name, str) and name.strip():
            terms.extend(_name_terms(name.strip()))
        columns = table.get("columns")
        for column in columns if isinstance(columns, list) else []:
            column_name = column.get("name") if isinstance(column, dict) else None
            if isinstance(column_name, str) and column_name.strip():
                terms.extend(_name_terms(column_name.strip()))
        if terms:
            lines.append(" ".join(terms))
    return "\n".join(lines)


def _text(facet: DatabaseSchema) -> str:
    if facet.parse_status != DatabaseSchema.PARSE_STATUS_OK:
        return ""
    return flatten_schema_text(facet.parsed_schema)


def _hosts_schemas(entity: Any, memo: dict[str, bool]) -> bool:
    """Active and of a kind declaring `schema.host.v1` (the facet endpoint's rule)."""
    if entity.status != STATUS_ACTIVE:
        return False
    if entity.kind not in memo:
        match resolve_capability(entity.kind, SCHEMA_HOST_V1):
            case Ok(True):
                memo[entity.kind] = True
            case _:
                memo[entity.kind] = False
    return memo[entity.kind]


def _facets(pks: Sequence[UUID] | None = None):
    queryset = DatabaseSchema.objects.select_related("entity")
    if pks is not None:
        queryset = queryset.filter(pk__in=pks)
    return queryset


def _eligible(queryset) -> Iterator[DatabaseSchema]:
    memo: dict[str, bool] = {}
    for facet in queryset:
        if _hosts_schemas(facet.entity, memo):
            yield facet


def _document(facet: DatabaseSchema) -> SearchDocument:
    return SearchDocument(
        id=f"{KIND_SCHEMA}:{facet.pk}",
        kind=KIND_SCHEMA,
        title=facet.entity.name,
        body=_text(facet),
    )


def _uuids(ids: Sequence[str]) -> list[UUID]:
    pks: list[UUID] = []
    for document_id in ids:
        try:
            kind, key = split_document_id(document_id)
            if kind == KIND_SCHEMA:
                pks.append(UUID(key))
        except ValueError:
            continue
    return pks


class DatabaseSchemaSearchSource:
    id = "atlas.database-schema"
    kinds = (KIND_SCHEMA,)
    kind_labels: ClassVar[dict[str, str]] = {KIND_SCHEMA: "Database schema"}

    @property
    def watched_models(self) -> tuple[str, ...]:
        # The owning entity is watched because its name is the document title
        # and its status decides whether the schema is searchable.
        return (DatabaseSchema._meta.label, get_catalog_entity_model()._meta.label)

    def document_ids_for_instance(self, instance: Any) -> Iterable[str]:
        # Also for deleted rows: `documents` then omits the id and the indexer
        # deletes it.
        if isinstance(instance, DatabaseSchema):
            return [f"{KIND_SCHEMA}:{instance.pk}"]
        if DatabaseSchema.objects.filter(pk=instance.pk).exists():
            return [f"{KIND_SCHEMA}:{instance.pk}"]
        return []

    def documents(self, ids: Sequence[str]) -> Iterable[SearchDocument]:
        return [_document(facet) for facet in _eligible(_facets(_uuids(ids)))]

    def all_documents(self) -> Iterator[SearchDocument]:
        for facet in _eligible(_facets().iterator()):
            yield _document(facet)

    def resolve(self, ids: Sequence[str], actor: Any) -> Sequence[SearchHit]:
        if not getattr(actor, "is_authenticated", False):
            return []
        return [
            SearchHit(
                id=f"{KIND_SCHEMA}:{facet.pk}",
                kind=KIND_SCHEMA,
                title=facet.entity.name,
                link=f"/resources/{facet.pk}?tab=schema",
                text=_text(facet),
            )
            for facet in _eligible(_facets(_uuids(ids)))
        ]


database_schema_search_source = DatabaseSchemaSearchSource()
