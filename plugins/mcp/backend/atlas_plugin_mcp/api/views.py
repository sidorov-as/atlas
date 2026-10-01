"""Catalog controllers for the MCP API: `search_catalog`, `get_entity`,
`create_entity`, `update_entity`, `remove_entity`, `purge_entity`
(`mcp-plugin` spec).

Every operation routes exclusively through `EntityService`
(`atlas_plugin_api.get_entity_service`) — never direct ORM writes — so
authorization, validation, transaction handling, and audit recording stay
identical to the existing web UI/REST catalog paths (`mcp-plugin` spec:
"Catalog operations route through EntityService"). `search_catalog` itself
only reads `CatalogEntity` directly (a plain filtered list, the same shape
`EntityService.list()` doesn't itself offer — text search, tag/owner
filtering, pagination), matching every existing kind-specific list
controller's own convention (`atlas_plugin_standard_catalog.api.views`).

Writes are restricted to `WRITABLE_KINDS` — exactly the kinds the REST/SPA
API itself lets anyone create or update (System/Component/Resource/API).
Group and Actor stay registered Entity Kinds (so `EntityService` itself has
no opinion here), readable through `search_catalog`/`get_entity` like any
other kind, but the REST API deliberately publishes no write path for
either ("Group and User are read-only via API") — partly because Group
membership feeds RBAC — so this API doesn't introduce a new, MCP-only way
to write them either; it only ever exposes what some other public channel
already does.

There is no `delete_entity` tool: the REST API itself retired a raw,
single-step delete in favor of Remove (soft) -> Purge (hard, with full
FK/ref-string reference-scanning) as the sole destructive path (D14) — this
API's `remove_entity`/`purge_entity` tools are that same two-step flow, not
a weaker, MCP-only shortcut around it.

Writes require the `catalog:write` PAT scope in addition to a valid token
(`atlas_plugin_api.require_scope`) — `mcp-plugin` spec: "PAT scopes narrow
the MCP API's effective permissions", checked ahead of, and independent of,
the underlying user's own RBAC (`EntityWritePermission`, still enforced by
`EntityService` itself exactly as for any other caller).

Every operation requires a valid Atlas Personal Access Token
(`atlas_plugin_api.auth.PATBearerAuth`), never a session — this API is for
tool-calling clients, not the SPA (`mcp-plugin` spec: "Every MCP API
request is authenticated by an Atlas Personal Access Token").
"""

from http import HTTPStatus

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    KIND_API,
    KIND_COMPONENT,
    KIND_RESOURCE,
    KIND_SYSTEM,
    EntityKindHandler,
    EntityNotFoundError,
    EntityPath,
    EntityRead,
    PageOut,
    PaginatedOut,
    PATBearerAuth,
    dry_run,
    filter_by_owner,
    filter_by_search,
    filter_by_status,
    filter_by_tags_overlap,
    get_catalog_entity_model,
    get_entity_service,
    metadata_out,
    purge_entity,
    registry,
    remove_entity,
    require_scope,
    spec_owner_ref,
)
from atlas_plugin_api.controllers import AtlasController
from django.core.paginator import Paginator
from dmr import Body, Path, Query, modify
from dmr.errors import ErrorType, format_error
from dmr.response import APIError
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from .dry_run_support import dry_run_out, dump
from .schemas import (
    CatalogEntityOut,
    CatalogEntitySummaryOut,
    CreateEntityIn,
    DryRunOut,
    DryRunQuery,
    SearchCatalogQuery,
    UpdateEntityIn,
)
from .strict_keys import check_spec_keys

# Exactly the kinds the existing REST/SPA API itself lets anyone create or
# update — see module docstring.
WRITABLE_KINDS = frozenset({KIND_SYSTEM, KIND_COMPONENT, KIND_RESOURCE, KIND_API})

_SCOPE_CATALOG_WRITE = "catalog:write"


def _not_found() -> APIError:
    return APIError(
        format_error("Entity not found", error_type=ErrorType.not_found),
        status_code=HTTPStatus.NOT_FOUND,
    )


def _unwritable_kind(kind_id: str) -> APIError:
    return APIError(
        format_error(
            f"Entity kind {kind_id!r} is not writable through the MCP API",
            error_type=ErrorType.value_error,
        ),
        status_code=HTTPStatus.BAD_REQUEST,
    )


def _invalid_spec(exc: PydanticValidationError) -> APIError:
    return APIError(
        format_error(str(exc), error_type=ErrorType.value_error),
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
    )


def _resolve_writable_handler(kind_id: str) -> EntityKindHandler:
    """Resolve `kind_id`'s registered handler, rejecting both an unknown
    kind and a known-but-not-writable-through-MCP one (`WRITABLE_KINDS`)
    with the same clear 400 either way — a client can't distinguish
    "no such kind" from "that kind exists but MCP won't write it" by status
    code alone, which is deliberate: neither is information this API needs
    to leak more precisely than that.
    """
    if kind_id not in WRITABLE_KINDS:
        raise _unwritable_kind(kind_id)
    handler = registry.resolve(kind_id)
    if handler is None:
        raise _unwritable_kind(kind_id)
    return handler


def _validate_spec(schema: type[BaseModel], raw: dict) -> BaseModel:
    check_spec_keys(schema, raw)
    try:
        return schema.model_validate(raw)
    except PydanticValidationError as exc:
        raise _invalid_spec(exc) from None


def _summary_out(instance) -> CatalogEntitySummaryOut:
    return CatalogEntitySummaryOut(
        id=instance.id,
        ref=instance.ref,
        kind=instance.kind,
        name=instance.name,
        title=instance.title,
        description=instance.description,
        status=instance.status,
        owner=instance.owner.ref if instance.owner_id else None,
    )


def _entity_out(read: EntityRead) -> CatalogEntityOut:
    return CatalogEntityOut(
        id=read.entity.id,
        ref=read.entity.ref,
        kind=read.entity.kind,
        metadata=metadata_out(read.entity),
        status=read.entity.status,
        spec=read.spec.model_dump(by_alias=True) if read.spec is not None else None,
        unavailable=read.unavailable,
    )


def _written_entity_out(entity, handler: EntityKindHandler) -> CatalogEntityOut:
    """`_entity_out`, for an entity a write operation just returned straight
    from `EntityService` (a `CatalogEntity`, not an `EntityRead`) — builds
    the `EntityRead` from the handler already in hand instead of a second
    `EntityService.get()` round-trip, the same `serialize_details`-right-
    after-the-write pattern the existing REST create/update controllers use
    (e.g. `ComponentListController.post` -> `_component_out(entity, ...)`).
    """
    return _entity_out(
        EntityRead(
            entity=entity,
            spec=handler.serialize_details(entity),
            unavailable=False,
        )
    )


class SearchCatalogController(AtlasController):
    """The `search_catalog` MCP tool: a kind-agnostic, filtered, paginated
    catalog search — curated for tool calling, not a re-export of any
    kind-specific SPA list endpoint."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="search_catalog",
        summary="Search the catalog",
        description=(
            "Search catalog entities (System, Component, Resource, API, "
            "Group, Actor) by free-text query, kind, owner, tags, or "
            "status. Returns a summary per entity — call `get_entity` for "
            "a given id to read its full metadata and kind-specific spec."
        ),
    )
    def get(
        self, parsed_query: Query[SearchCatalogQuery]
    ) -> PaginatedOut[CatalogEntitySummaryOut]:
        queryset = get_catalog_entity_model().objects.select_related("owner")
        if parsed_query.kind:
            queryset = queryset.filter(kind=parsed_query.kind)
        queryset = filter_by_owner(queryset, parsed_query.owner)
        queryset = filter_by_search(queryset, parsed_query.q)
        queryset = filter_by_tags_overlap(queryset, parsed_query.tags)
        queryset = filter_by_status(queryset, parsed_query.status)
        page = Paginator(
            queryset.order_by(parsed_query.sort, "id"), parsed_query.page_size
        ).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[_summary_out(instance) for instance in page.object_list],
            ),
        )


class CreateEntityController(AtlasController):
    """The `create_entity` MCP tool — its own path (`catalog/`), distinct
    from `search_catalog`'s `catalog/search/`: a search is a filtered list,
    not a collection a client also posts new entities to.
    """

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="create_entity",
        summary="Create a catalog entity",
        description=(
            "Create a System, Component, Resource, or API in the catalog. "
            "`spec` is validated against the target kind's own schema "
            "(see `describe_kinds`). With `dryRun` true nothing is saved "
            "and the response previews the result. "
            "Requires the `catalog:write` PAT scope."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def post(
        self,
        parsed_body: Body[CreateEntityIn],
        parsed_query: Query[DryRunQuery],
    ) -> CatalogEntityOut | DryRunOut:
        require_scope(self, _SCOPE_CATALOG_WRITE)
        handler = _resolve_writable_handler(parsed_body.kind)
        spec = _validate_spec(handler.spec_schema, parsed_body.spec)

        def write() -> CatalogEntityOut:
            entity = get_entity_service().create(
                kind_id=parsed_body.kind,
                owner_ref=spec_owner_ref(spec),
                metadata=parsed_body.metadata,
                spec=spec,
                actor=self.request.user,
            )
            return _written_entity_out(entity, handler)

        if not parsed_query.dry_run:
            return write()
        with dry_run() as context:
            after = dump(write())
        return dry_run_out(before=None, after=after, context=context)


class EntityDetailController(AtlasController):
    """The `get_entity` (GET) and `update_entity` (PATCH) MCP tools, one
    entity's full metadata plus its kind handler's own `spec` — the same
    get+patch-on-one-path split the REST System/Component/Resource/API
    detail controllers use.
    """

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="get_entity",
        summary="Get a catalog entity",
        description=(
            "Read one catalog entity by id: its full metadata plus its "
            "kind-specific spec."
        ),
    )
    def get(self, parsed_path: Path[EntityPath]) -> CatalogEntityOut:
        try:
            read = get_entity_service().get(parsed_path.id)
        except EntityNotFoundError:
            raise _not_found() from None
        return _entity_out(read)

    @modify(
        operation_id="update_entity",
        summary="Update a catalog entity",
        description=(
            "Partially update a catalog entity by id — an omitted field is "
            "left untouched. With `dryRun` true nothing is saved and the "
            "response lists each field's current and proposed value. "
            "Requires the `catalog:write` PAT scope."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def patch(
        self,
        parsed_path: Path[EntityPath],
        parsed_body: Body[UpdateEntityIn],
        parsed_query: Query[DryRunQuery],
    ) -> CatalogEntityOut | DryRunOut:
        require_scope(self, _SCOPE_CATALOG_WRITE)
        try:
            existing = get_entity_service().get(parsed_path.id)
        except EntityNotFoundError:
            raise _not_found() from None
        handler = _resolve_writable_handler(existing.entity.kind)
        spec = (
            _validate_spec(handler.patch_schema, parsed_body.spec)
            if parsed_body.spec is not None
            else None
        )

        def write() -> CatalogEntityOut:
            entity = get_entity_service().update(
                entity_id=parsed_path.id,
                owner_ref=spec_owner_ref(spec),
                metadata=parsed_body.metadata,
                spec=spec,
                actor=self.request.user,
            )
            return _written_entity_out(entity, handler)

        if not parsed_query.dry_run:
            return write()
        before = dump(_entity_out(existing))
        with dry_run() as context:
            after = dump(write())
        return dry_run_out(before=before, after=after, context=context)


class EntityRemoveController(AtlasController):
    """The `remove_entity` MCP tool: step one of catalog delete (Remove ->
    Purge) — flips `status` to `removed`, same as the REST Remove endpoints
    (e.g. `SystemRemoveController`)."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="remove_entity",
        summary="Remove a catalog entity",
        description=(
            "Step one of catalog delete: flip a catalog entity's status to "
            "`removed` (soft delete). Follow with `purge_entity` to "
            "permanently delete it. Requires the `catalog:write` PAT scope."
        ),
        status_code=HTTPStatus.OK,
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def post(self, parsed_path: Path[EntityPath]) -> CatalogEntityOut:
        require_scope(self, _SCOPE_CATALOG_WRITE)
        try:
            existing = get_entity_service().get(parsed_path.id)
        except EntityNotFoundError:
            raise _not_found() from None
        handler = _resolve_writable_handler(existing.entity.kind)
        entity = remove_entity(parsed_path.id, self.request.user)
        return _written_entity_out(entity, handler)


class EntityPurgeController(AtlasController):
    """The `purge_entity` MCP tool: step two of catalog delete — permanently
    deletes a `removed` entity's row after full FK/ref-string
    reference-scanning (`EntityService.purge`), same as the REST Purge
    endpoints."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="purge_entity",
        summary="Purge a catalog entity",
        description=(
            "Step two of catalog delete: permanently delete a `removed` "
            "catalog entity after scanning for remaining references. "
            "Requires the `catalog:write` PAT scope."
        ),
        status_code=HTTPStatus.NO_CONTENT,
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def post(self, parsed_path: Path[EntityPath]) -> None:
        require_scope(self, _SCOPE_CATALOG_WRITE)
        try:
            existing = get_entity_service().get(parsed_path.id)
        except EntityNotFoundError:
            raise _not_found() from None
        _resolve_writable_handler(existing.entity.kind)
        purge_entity(parsed_path.id, self.request.user)
