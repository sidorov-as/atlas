from typing import ClassVar

from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.db import models


class DatabaseSchema(models.Model):
    """The `DatabaseSchema` Facet: a plugin-owned, persisted
    aspect of a `CatalogEntity`, independent of the owning kind's own details
    model (`OneToOneField(CatalogEntity, primary_key=True)`,
    not `OneToOneField(ResourceDetails, primary_key=True)`) and of any view
    contribution that renders it (a Facet's data outlives a
    view contribution)."""

    DIALECT_POSTGRESQL = "postgresql"
    DIALECT_MYSQL = "mysql"
    DIALECT_MSSQL = "mssql"
    DIALECT_CHOICES: ClassVar[list] = [
        (DIALECT_POSTGRESQL, "PostgreSQL"),
        (DIALECT_MYSQL, "MySQL"),
        (DIALECT_MSSQL, "MS SQL"),
    ]

    PARSE_STATUS_OK = "ok"
    PARSE_STATUS_FAILED = "failed"
    PARSE_STATUS_CHOICES: ClassVar[list] = [
        (PARSE_STATUS_OK, "Ok"),
        (PARSE_STATUS_FAILED, "Failed"),
    ]

    entity = models.OneToOneField(
        CATALOG_ENTITY_LABEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="database_schema",
    )
    dialect = models.CharField(
        max_length=32, choices=DIALECT_CHOICES, default=DIALECT_POSTGRESQL
    )
    source_sql = models.TextField(blank=True)
    # Structured, parsed from `source_sql` on save (parsed
    # synchronously, not re-parsed on read) — provisional/internal shape, no
    # external contract promised yet.
    parsed_schema = models.JSONField(default=dict, blank=True)
    parse_status = models.CharField(
        max_length=16, choices=PARSE_STATUS_CHOICES, default=PARSE_STATUS_OK
    )
    # Audit timestamps. Bulk updates (`QuerySet.update`) bypass `auto_now`, so these are not a
    # reliable sync cursor — search indexing does not depend on them.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.entity.name
