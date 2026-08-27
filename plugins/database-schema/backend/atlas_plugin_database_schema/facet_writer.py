"""`atlas.ingestion.facet_writers.v1` implementation for the `DatabaseSchema`
Facet.

Registered under key `'database-schema'` by `plugin.register_runtime()`,
which only runs when `atlas.database-schema` is actually selected/composed
for the distribution — `atlas_plugin_ingestion` resolving this key and
finding nothing registered is its reliable signal that this plugin isn't
active, with no capability check and no risk of writing to a
table that was never migrated into existence.
"""

from atlas_plugin_api import CatalogEntity

from .models import DatabaseSchema
from .parser import SqlParseError, parse_schema


class DatabaseSchemaFacetWriter:
    """`apply`/`clear` reuse the same `parse_schema()` the manual CRUD path
    (`api.views._apply_source`) already uses — a failed parse still saves
    `source_sql` verbatim (entity-facets, database-schema-plugin specs: "A
    failed parse preserves the saved SQL")."""

    def apply(self, entity: CatalogEntity, dialect: str, source_sql: str) -> None:
        facet, _ = DatabaseSchema.objects.get_or_create(entity=entity)
        facet.dialect = dialect
        facet.source_sql = source_sql
        try:
            facet.parsed_schema = parse_schema(source_sql, dialect=dialect)
            facet.parse_status = DatabaseSchema.PARSE_STATUS_OK
        except SqlParseError:
            facet.parsed_schema = {}
            facet.parse_status = DatabaseSchema.PARSE_STATUS_FAILED
        facet.save()

    def clear(self, entity: CatalogEntity) -> None:
        DatabaseSchema.objects.filter(pk=entity.pk).delete()
