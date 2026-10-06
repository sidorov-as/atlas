"""`(resource, schema)` upload target (`database-schema-plugin` spec): the
body is the SQL text, the dialect is a ticket parameter. Goes through the
shared `writer.write_resource_schema`, so it stores exactly what the CRUD
endpoint, ingestion, and the MCP write store.
"""

from collections.abc import Mapping
from typing import Any

from atlas_plugin_api import (
    KIND_RESOURCE,
    UploadResult,
    UploadTarget,
    UploadValidationError,
)
from django.conf import settings

from .models import DatabaseSchema
from .writer import write_resource_schema

SCHEMA_FIELD = "schema"
SCHEMA_UPLOAD_SCOPE = "catalog:write"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024

DIALECTS = tuple(value for value, _ in DatabaseSchema.DIALECT_CHOICES)


class SchemaUploadAdapter:
    def validate_params(self, params: Mapping[str, Any]) -> dict[str, Any]:
        dialect = params.get("dialect", DatabaseSchema.DIALECT_POSTGRESQL)
        if dialect not in DIALECTS:
            msg = f"Unsupported dialect {dialect!r} (supported: {', '.join(DIALECTS)})"
            raise UploadValidationError(msg)
        return {"dialect": dialect}

    def apply(
        self, entity: Any, body: bytes, params: Mapping[str, Any], user: Any
    ) -> UploadResult:
        try:
            source_sql = body.decode("utf-8")
        except UnicodeDecodeError:
            msg = "The body is not valid UTF-8"
            raise UploadValidationError(msg) from None
        result = write_resource_schema(
            entity, dialect=params["dialect"], source_sql=source_sql
        )
        return UploadResult(
            summary={
                "parse_status": result.parse_status,
                "parse_error": result.parse_error,
                "table_count": result.table_count,
            }
        )


def schema_upload_target() -> UploadTarget:
    return UploadTarget(
        kind=KIND_RESOURCE,
        field=SCHEMA_FIELD,
        required_scope=SCHEMA_UPLOAD_SCOPE,
        max_bytes=getattr(
            settings, "ATLAS_DATABASE_SCHEMA_UPLOAD_MAX_BYTES", DEFAULT_MAX_BYTES
        ),
        adapter=SchemaUploadAdapter(),
    )
