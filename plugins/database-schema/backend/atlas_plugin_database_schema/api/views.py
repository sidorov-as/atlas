"""Facet CRUD controller for the `DatabaseSchema` Facet:
`POST/GET/PATCH /api/plugins/atlas.database-schema/resources/{entityId}/schema`,
a plugin-owned endpoint — not `PATCH /api/resources/{id}` with a `spec`
sub-object, and not routed through the core Entity Service (a Facet
write does not invoke the entity's kind handler).
"""

from http import HTTPStatus

from atlas_plugin_api import (
    KIND_RESOURCE,
    SCHEMA_HOST_V1,
    CatalogEntity,
    EntityPath,
    Ok,
    SessionAuth,
    get_catalog_entity_model,
    resolve_capability,
)
from atlas_plugin_api.controllers import AtlasController
from django.contrib.auth.base_user import AbstractBaseUser
from dmr import Body, Path, ResponseSpec, modify
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.response import APIError

from ..models import DatabaseSchema
from ..writer import (
    SchemaWriteForbiddenError,
    apply_schema_source,
    check_schema_write_permission,
)
from .schemas import DatabaseSchemaIn, DatabaseSchemaOut, DatabaseSchemaPatch


def _not_found(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.not_found),
        status_code=HTTPStatus.NOT_FOUND,
    )


def _check_write_permission(user: AbstractBaseUser, entity: CatalogEntity) -> None:
    """Map the shared write guard (`writer.check_schema_write_permission`) to
    a 403."""
    try:
        check_schema_write_permission(user, entity)
    except SchemaWriteForbiddenError as exc:
        raise APIError(
            format_error(str(exc), error_type=ErrorType.security),
            status_code=HTTPStatus.FORBIDDEN,
        ) from None


def _conflict(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.value_error),
        status_code=HTTPStatus.CONFLICT,
    )


CONFLICT_RESPONSE = ResponseSpec(
    ErrorModel,
    status_code=HTTPStatus.CONFLICT,
    description="This Resource already has a Database Schema facet",
)

FORBIDDEN_RESPONSE = ResponseSpec(
    ErrorModel,
    status_code=HTTPStatus.FORBIDDEN,
    description="Not permitted, or the Resource is YAML-managed",
)


def _get_schema_host(pk) -> CatalogEntity:
    catalog_entity_model = get_catalog_entity_model()
    try:
        entity = catalog_entity_model.objects.select_related("database_schema").get(
            pk=pk,
            kind=KIND_RESOURCE,
        )
    except catalog_entity_model.DoesNotExist:
        raise _not_found("Resource not found") from None
    # Typed `resolve_capability` distinguishes
    # "resource kind unavailable" from "registered but lacks the capability" —
    # both still 404 here today, since this endpoint has no distinct handling
    # for either, but the check is now explicit about which is which.
    match resolve_capability(entity.kind, SCHEMA_HOST_V1):
        case Ok(True):
            return entity
        case _:
            raise _not_found("Resource not found") from None


def _get_facet(entity: CatalogEntity) -> DatabaseSchema:
    try:
        return entity.database_schema
    except DatabaseSchema.DoesNotExist:
        raise _not_found("This Resource has no Database Schema facet") from None


def _facet_out(entity_id, facet: DatabaseSchema) -> DatabaseSchemaOut:
    return DatabaseSchemaOut(
        entity_id=entity_id,
        dialect=facet.dialect,
        source_sql=facet.source_sql,
        parsed_schema=facet.parsed_schema,
        parse_status=facet.parse_status,
    )


class DatabaseSchemaController(AtlasController):
    auth = (SessionAuth(),)

    def get(self, parsed_path: Path[EntityPath]) -> DatabaseSchemaOut:
        entity = _get_schema_host(parsed_path.id)
        return _facet_out(entity.id, _get_facet(entity))

    @modify(extra_responses=[CONFLICT_RESPONSE, FORBIDDEN_RESPONSE])
    def post(
        self,
        parsed_path: Path[EntityPath],
        parsed_body: Body[DatabaseSchemaIn],
    ) -> DatabaseSchemaOut:
        entity = _get_schema_host(parsed_path.id)
        _check_write_permission(self.request.user, entity)
        if DatabaseSchema.objects.filter(pk=entity.pk).exists():
            raise _conflict("This Resource already has a Database Schema facet")
        facet = DatabaseSchema(entity=entity)
        apply_schema_source(
            facet, dialect=parsed_body.dialect, source_sql=parsed_body.source_sql
        )
        return _facet_out(entity.id, facet)

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self,
        parsed_path: Path[EntityPath],
        parsed_body: Body[DatabaseSchemaPatch],
    ) -> DatabaseSchemaOut:
        entity = _get_schema_host(parsed_path.id)
        _check_write_permission(self.request.user, entity)
        facet = _get_facet(entity)
        dialect = (
            parsed_body.dialect if parsed_body.dialect is not None else facet.dialect
        )
        source_sql = (
            parsed_body.source_sql
            if parsed_body.source_sql is not None
            else facet.source_sql
        )
        apply_schema_source(facet, dialect=dialect, source_sql=source_sql)
        return _facet_out(entity.id, facet)
