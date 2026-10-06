"""`set_resource_schema` MCP tool: writes a Resource's database schema inline
(`mcp-upload-tools` spec). The Facet's own REST endpoint is session-only, so
this is the PAT path to the same shared write function.

Only ever imported by `atlas_plugin_mcp.api.urls` after it has confirmed
`atlas_plugin_database_schema` is installed.
"""

from http import HTTPStatus

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    KIND_RESOURCE,
    PATBearerAuth,
    RefError,
    dry_run,
    require_scope,
    resolve_ref,
)
from atlas_plugin_api.controllers import AtlasController
from atlas_plugin_database_schema import extension_points
from dmr import Body, Query, ResponseSpec, modify
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.response import APIError

from .dry_run_support import dry_run_out, dump
from .schemas import (
    DryRunOut,
    DryRunQuery,
    SetResourceSchemaIn,
    SetResourceSchemaOut,
)

_SCOPE_CATALOG_WRITE = "catalog:write"

_RESOURCE_NOT_FOUND_RESPONSE = ResponseSpec(
    ErrorModel,
    status_code=HTTPStatus.NOT_FOUND,
    description="The Resource ref does not resolve",
)


class SetResourceSchemaController(AtlasController):
    """The `set_resource_schema` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="set_resource_schema",
        summary="Set a Resource's database schema",
        description=(
            "Create or replace a Resource's database schema from DDL text "
            "(`resource` as `resource:name`, `dialect`, `sourceSql`). For "
            "large files use `request_attach` instead. A 200 means the SQL "
            "was SAVED; whether it parsed is reported separately as "
            "`parseStatus` (`ok`/`failed`) with the parser's message in "
            "`parseError`. With `dryRun` true nothing is saved. Requires "
            "the `catalog:write` PAT scope."
        ),
        status_code=HTTPStatus.OK,
        extra_responses=[FORBIDDEN_RESPONSE, _RESOURCE_NOT_FOUND_RESPONSE],
    )
    def post(
        self,
        parsed_body: Body[SetResourceSchemaIn],
        parsed_query: Query[DryRunQuery],
    ) -> SetResourceSchemaOut | DryRunOut:
        require_scope(self, _SCOPE_CATALOG_WRITE)
        try:
            entity = resolve_ref(parsed_body.resource, expected_kind=KIND_RESOURCE)
        except RefError as exc:
            raise APIError(
                format_error(str(exc), error_type=ErrorType.not_found),
                status_code=HTTPStatus.NOT_FOUND,
            ) from None

        def write() -> SetResourceSchemaOut:
            try:
                result = extension_points.set_resource_schema(
                    self.request.user,
                    entity,
                    dialect=parsed_body.dialect,
                    source_sql=parsed_body.source_sql,
                )
            except extension_points.SchemaWriteForbiddenError as exc:
                raise APIError(
                    format_error(str(exc), error_type=ErrorType.security),
                    status_code=HTTPStatus.FORBIDDEN,
                ) from None
            return SetResourceSchemaOut(
                resource=entity.ref,
                dialect=parsed_body.dialect,
                parse_status=result.parse_status,
                parse_error=result.parse_error,
                table_count=result.table_count,
            )

        if not parsed_query.dry_run:
            return write()
        before = extension_points.current_schema(entity)
        with dry_run() as context:
            after = dump(write())
        return dry_run_out(before=before, after=after, context=context)
