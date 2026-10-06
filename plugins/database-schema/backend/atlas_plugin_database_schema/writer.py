"""The one schema write path shared by the CRUD endpoint, the ingestion facet
writer, and (later) the MCP schema write and the upload adapter, so they
cannot diverge on what gets stored or who may write.
"""

from dataclasses import dataclass

from atlas_plugin_api import SOURCE_YAML, CatalogEntity, get_policy_evaluator
from django.contrib.auth.base_user import AbstractBaseUser

from .models import DatabaseSchema
from .parser import SqlParseError, parse_schema

YAML_MANAGED_MESSAGE = "This entity is managed by catalog-info.yaml and is read-only"
NOT_OWNER_MESSAGE = "You are not a member of the owner Group"


class SchemaWriteForbiddenError(Exception):
    """The caller may not write this Resource's schema."""


def check_schema_write_permission(
    user: AbstractBaseUser, entity: CatalogEntity
) -> None:
    """Reject a write to a YAML-managed Resource (unconditionally on
    `source_kind`) and require `<kind>.edit` on the entity through the one
    guarded evaluator, so a Facet write gets the same owner-Group/read-only
    guard as every other Resource write.
    """
    if entity.source_kind == SOURCE_YAML:
        raise SchemaWriteForbiddenError(YAML_MANAGED_MESSAGE)
    if not get_policy_evaluator().check(user, f"{entity.kind}.edit", entity):
        raise SchemaWriteForbiddenError(NOT_OWNER_MESSAGE)


def apply_schema_source(
    facet: DatabaseSchema, *, dialect: str, source_sql: str
) -> tuple[str, str]:
    """Save `source_sql` unconditionally and set `parse_status` from the parse
    attempt; a failed parse never blocks the save. Returns
    `(parse_status, parse_error)`, where `parse_error` is the parser's message
    on failure and empty on success.
    """
    facet.dialect = dialect
    facet.source_sql = source_sql
    parse_error = ""
    try:
        facet.parsed_schema = parse_schema(source_sql, dialect=dialect)
        facet.parse_status = DatabaseSchema.PARSE_STATUS_OK
    except SqlParseError as exc:
        facet.parsed_schema = {}
        facet.parse_status = DatabaseSchema.PARSE_STATUS_FAILED
        parse_error = str(exc)
    facet.save()
    return facet.parse_status, parse_error


@dataclass(frozen=True)
class SchemaWriteResult:
    """What every schema write reports: `ok` elsewhere means saved; these
    describe the parse."""

    parse_status: str
    parse_error: str
    table_count: int


def write_resource_schema(
    entity: CatalogEntity, *, dialect: str, source_sql: str
) -> SchemaWriteResult:
    """Create the Resource's facet if absent, otherwise replace it. The
    caller checks permission (`check_schema_write_permission`)."""
    facet, _ = DatabaseSchema.objects.get_or_create(entity=entity)
    parse_status, parse_error = apply_schema_source(
        facet, dialect=dialect, source_sql=source_sql
    )
    return SchemaWriteResult(
        parse_status=parse_status,
        parse_error=parse_error,
        table_count=len(facet.parsed_schema.get("tables", [])),
    )
