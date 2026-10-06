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
from .writer import apply_schema_source


class DatabaseSchemaFacetWriter:
    """`apply`/`clear` go through the same `apply_schema_source()` the manual
    CRUD path uses — a failed parse still saves `source_sql` verbatim (entity-facets, database-schema-plugin specs: "A
    failed parse preserves the saved SQL")."""

    def apply(self, entity: CatalogEntity, dialect: str, source_sql: str) -> None:
        facet, _ = DatabaseSchema.objects.get_or_create(entity=entity)
        apply_schema_source(facet, dialect=dialect, source_sql=source_sql)

    def clear(self, entity: CatalogEntity) -> None:
        DatabaseSchema.objects.filter(pk=entity.pk).delete()
