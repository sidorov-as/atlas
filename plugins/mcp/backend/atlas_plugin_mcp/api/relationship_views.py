"""Architecture Relationship controllers for the MCP API:
`list_relationships`, `create_relationship`, `update_relationship`,
`delete_relationship` (`mcp-relationship-tools` spec).

Every operation goes through the published Architecture Relationship service
(`atlas_plugin_api.get_architecture_relationship_service`), never the ORM or
core's REST views, so origin, source-kind, and permission rules are the same
ones the REST endpoints apply. Reads need `catalog:read`, writes
`catalog:write` (`atlas_plugin_api.require_scope`), checked ahead of the
user's own RBAC.
"""

from http import HTTPStatus

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    ArchitectureRelationshipNotFoundError,
    ArchitectureRelationshipReadOnlyError,
    ArchitectureRelationshipSourceKindError,
    PATBearerAuth,
    dry_run,
    get_architecture_relationship_service,
    require_scope,
)
from atlas_plugin_api.controllers import AtlasController
from atlas_plugin_api.refs import RefError
from dmr import Body, Path, Query, modify
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from .dry_run_support import dry_run_out, dump
from .schemas import (
    CreateRelationshipIn,
    DryRunOut,
    DryRunQuery,
    ListRelationshipsQuery,
    RelationshipOut,
    RelationshipPath,
    UpdateRelationshipIn,
)

_SCOPE_CATALOG_READ = "catalog:read"
_SCOPE_CATALOG_WRITE = "catalog:write"

_SERVICE_ERRORS = (
    ArchitectureRelationshipNotFoundError,
    ArchitectureRelationshipReadOnlyError,
    ArchitectureRelationshipSourceKindError,
    RefError,
)


def _error(exc: Exception) -> APIError:
    if isinstance(exc, ArchitectureRelationshipNotFoundError):
        return APIError(
            format_error(
                "Architecture relationship not found",
                error_type=ErrorType.not_found,
            ),
            status_code=HTTPStatus.NOT_FOUND,
        )
    if isinstance(exc, ArchitectureRelationshipReadOnlyError):
        return APIError(
            format_error(
                "This relationship is managed by ingestion (origin `yaml`) "
                "and cannot be changed through MCP",
                error_type=ErrorType.security,
            ),
            status_code=HTTPStatus.FORBIDDEN,
        )
    return APIError(
        format_error(str(exc), error_type=ErrorType.value_error),
        status_code=HTTPStatus.BAD_REQUEST,
    )


def _out(relationship) -> RelationshipOut:
    return RelationshipOut(
        id=relationship.id,
        source=relationship.source.ref,
        source_kind=relationship.source.kind,
        target=relationship.target.ref,
        target_kind=relationship.target.kind,
        label=relationship.label,
        technology=relationship.technology,
        interaction_kind=relationship.interaction_kind,
        tags=relationship.tags,
        origin=relationship.origin,
    )


class RelationshipListController(AtlasController):
    auth = (PATBearerAuth(),)

    @modify(
        operation_id="list_relationships",
        summary="List an entity's architecture relationships",
        description=(
            "List every Architecture Relationship where the entity is the "
            "source or the target, each with its id, endpoints, label, "
            "technology, interaction kind, tags, and origin (`manual` or "
            "`yaml`; `yaml` ones are managed by ingestion and read-only). "
            "Requires the `catalog:read` PAT scope."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def get(self, parsed_query: Query[ListRelationshipsQuery]) -> list[RelationshipOut]:
        require_scope(self, _SCOPE_CATALOG_READ)
        try:
            relationships = get_architecture_relationship_service().list_for_entity(
                entity_ref=parsed_query.entity
            )
        except _SERVICE_ERRORS as exc:
            raise _error(exc) from None
        return [_out(relationship) for relationship in relationships]

    @modify(
        operation_id="create_relationship",
        summary="Create a manual architecture relationship",
        description=(
            "Create a directed manual Architecture Relationship from a "
            "System, Component, Resource, or API to any catalog entity. "
            "With `dryRun` true nothing is saved and the response previews "
            "the result. Requires the `catalog:write` PAT scope and write "
            "permission on the source."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def post(
        self,
        parsed_body: Body[CreateRelationshipIn],
        parsed_query: Query[DryRunQuery],
    ) -> RelationshipOut | DryRunOut:
        require_scope(self, _SCOPE_CATALOG_WRITE)

        def write() -> RelationshipOut:
            return _out(
                get_architecture_relationship_service().create(
                    source_ref=parsed_body.source,
                    target_ref=parsed_body.target,
                    label=parsed_body.label,
                    technology=parsed_body.technology,
                    interaction_kind=parsed_body.interaction_kind,
                    tags=parsed_body.tags,
                    actor=self.request.user,
                )
            )

        try:
            if not parsed_query.dry_run:
                return write()
            with dry_run() as context:
                after = dump(write())
        except _SERVICE_ERRORS as exc:
            raise _error(exc) from None
        return dry_run_out(before=None, after=after, context=context)


class RelationshipDetailController(AtlasController):
    auth = (PATBearerAuth(),)

    @modify(
        operation_id="update_relationship",
        summary="Update a manual architecture relationship",
        description=(
            "Partially update a manual Architecture Relationship by id; an "
            "omitted field is left untouched. YAML-origin relationships are "
            "rejected. With `dryRun` true nothing is saved and the response "
            "lists each field's current and proposed value. Requires the "
            "`catalog:write` PAT scope."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def patch(
        self,
        parsed_path: Path[RelationshipPath],
        parsed_body: Body[UpdateRelationshipIn],
        parsed_query: Query[DryRunQuery],
    ) -> RelationshipOut | DryRunOut:
        require_scope(self, _SCOPE_CATALOG_WRITE)
        fields = {
            field: getattr(parsed_body, field) for field in parsed_body.model_fields_set
        }
        service = get_architecture_relationship_service()

        def write() -> RelationshipOut:
            return _out(
                service.update(
                    relationship_id=parsed_path.id,
                    fields=fields,
                    actor=self.request.user,
                )
            )

        try:
            if not parsed_query.dry_run:
                return write()
            before = dump(_out(service.get(parsed_path.id)))
            with dry_run() as context:
                after = dump(write())
        except _SERVICE_ERRORS as exc:
            raise _error(exc) from None
        return dry_run_out(before=before, after=after, context=context)

    @modify(
        operation_id="delete_relationship",
        summary="Delete a manual architecture relationship",
        description=(
            "Delete a manual Architecture Relationship by id and return "
            "what was deleted. YAML-origin relationships are rejected. "
            "With `dryRun` true nothing is deleted and the response shows "
            "what would be removed. Requires the `catalog:write` PAT scope."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def delete(
        self,
        parsed_path: Path[RelationshipPath],
        parsed_query: Query[DryRunQuery],
    ) -> RelationshipOut | DryRunOut:
        require_scope(self, _SCOPE_CATALOG_WRITE)
        service = get_architecture_relationship_service()
        try:
            deleted = _out(service.get(parsed_path.id))
            if not parsed_query.dry_run:
                service.delete(relationship_id=parsed_path.id, actor=self.request.user)
                return deleted
            with dry_run() as context:
                service.delete(relationship_id=parsed_path.id, actor=self.request.user)
        except _SERVICE_ERRORS as exc:
            raise _error(exc) from None
        return dry_run_out(before=dump(deleted), after=None, context=context)
