"""The contract surface other plugins (the MCP plugin) may import from
`atlas.database-schema`, so they never touch its models or writer directly.
"""

from atlas_plugin_api import CatalogEntity
from django.contrib.auth.base_user import AbstractBaseUser

from .models import DatabaseSchema
from .writer import (
    SchemaWriteForbiddenError,
    SchemaWriteResult,
    check_schema_write_permission,
    write_resource_schema,
)

DIALECTS = tuple(value for value, _ in DatabaseSchema.DIALECT_CHOICES)


def set_resource_schema(
    user: AbstractBaseUser, entity: CatalogEntity, *, dialect: str, source_sql: str
) -> SchemaWriteResult:
    """Permission-checked create-or-replace of `entity`'s schema. Raises
    `SchemaWriteForbiddenError`."""
    check_schema_write_permission(user, entity)
    return write_resource_schema(entity, dialect=dialect, source_sql=source_sql)


def current_schema(entity: CatalogEntity) -> dict | None:
    """The stored schema's dialect, SQL and parse status, or `None`."""
    facet = DatabaseSchema.objects.filter(pk=entity.pk).first()
    if facet is None:
        return None
    return {
        "dialect": facet.dialect,
        "sourceSql": facet.source_sql,
        "parseStatus": facet.parse_status,
    }


__all__ = [
    "DIALECTS",
    "SchemaWriteForbiddenError",
    "SchemaWriteResult",
    "current_schema",
    "set_resource_schema",
]
