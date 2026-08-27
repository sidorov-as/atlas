"""Request/response schemas for the Database Schema facet endpoint
(`/api/plugins/atlas.database-schema/resources/{entityId}/schema`).
"""

from typing import Literal
from uuid import UUID

from atlas_plugin_api import CamelModel
from pydantic import Field

DatabaseSchemaDialect = Literal["postgresql", "mysql", "mssql"]
ParseStatus = Literal["ok", "failed"]

# Generous DoS-prevention bound, kept
# safely below Django's default (unconfigured) 2.5 MiB
# `DATA_UPLOAD_MAX_MEMORY_SIZE`, which already hard-caps the whole request
# body ahead of any Pydantic validation — see `atlas_plugin_apis.api.schemas`'s
# `_SPEC_CONTENT_MAX_LENGTH` for the same reasoning.
_SOURCE_SQL_MAX_LENGTH = 2 * 1024 * 1024


class DatabaseSchemaIn(CamelModel):
    dialect: DatabaseSchemaDialect = "postgresql"
    source_sql: str = Field(default="", max_length=_SOURCE_SQL_MAX_LENGTH)


class DatabaseSchemaPatch(CamelModel):
    dialect: DatabaseSchemaDialect | None = None
    source_sql: str | None = Field(default=None, max_length=_SOURCE_SQL_MAX_LENGTH)


class DatabaseSchemaOut(CamelModel):
    entity_id: UUID
    dialect: DatabaseSchemaDialect
    source_sql: str
    parsed_schema: dict
    parse_status: ParseStatus
