"""Diagram controllers — split out of `server.apps.catalog.api.views`.

Every request additionally checks the `atlas.c4.diagram.read` permission
on top of `SessionAuth`'s authenticated-session check.
"""

import logging
from http import HTTPStatus

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    KIND_COMPONENT,
    KIND_SYSTEM,
    PageOut,
    PaginatedOut,
    SessionAuth,
    get_catalog_entity_model,
)
from atlas_plugin_api.controllers import AtlasController
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from dmr import Body, Path, Query, ResponseSpec, modify, validate
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.response import APIError

from .. import c4, custom_view
from ..errors import CustomViewError
from ..models import View
from ..permissions import (
    check_diagram_read_permission,
    check_view_delete_permission,
    check_view_write_permission,
)
from .schemas import (
    ActorKindsOut,
    CustomViewSettings,
    DiagramPath,
    DiagramQuery,
    ViewIn,
    ViewListFilters,
    ViewOut,
    ViewPath,
)

logger = logging.getLogger("atlas_plugin_c4")

_DIAGRAM_TARGETS = {
    ("system", "context"): (KIND_SYSTEM, c4.build_system_context),
    ("system", "architecture"): (KIND_SYSTEM, c4.build_system_architecture),
    ("component", "component"): (KIND_COMPONENT, c4.build_component_diagram),
}


class DiagramController(AtlasController):
    """Serve locally rendered System Context, Architecture, and Component diagrams."""

    auth = (SessionAuth(),)

    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            limit_to_content_types={"image/svg+xml"},
        ),
        ResponseSpec(ErrorModel, status_code=HTTPStatus.NOT_FOUND),
        ResponseSpec(ErrorModel, status_code=HTTPStatus.BAD_REQUEST),
        validate_responses=False,
    )
    def get(
        self, parsed_path: Path[DiagramPath], parsed_query: Query[DiagramQuery]
    ) -> HttpResponse:
        check_diagram_read_permission(self.request.user)
        target = _DIAGRAM_TARGETS.get((parsed_path.kind, parsed_query.view))
        if target is None:
            raise APIError(
                format_error(
                    "Only system/context, system/architecture, and "
                    "component/component diagrams are supported",
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )
        kind, build_payload = target
        catalog_entity_model = get_catalog_entity_model()
        try:
            entity = catalog_entity_model.objects.get(pk=parsed_path.id, kind=kind)
        except catalog_entity_model.DoesNotExist:
            raise APIError(
                format_error("Unknown diagram target", error_type=ErrorType.not_found),
                status_code=HTTPStatus.NOT_FOUND,
            ) from None
        payload = build_payload(
            entity,
            c4.DiagramRenderingSettings(
                layout=parsed_query.layout,
                show_title=parsed_query.show_title,
                show_legend=parsed_query.show_legend,
                show_selected_label=parsed_query.show_selected_label,
                show_person_sprite=parsed_query.show_person_sprite,
                show_stereotypes=parsed_query.show_stereotypes,
            ),
        )
        try:
            image = c4.render(payload, format=parsed_query.format)
        except c4.DiagramRenderError:
            logger.exception("C4 diagram rendering failed")
            raise APIError(
                format_error(
                    "Unable to render diagram", error_type=ErrorType.value_error
                ),
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            ) from None
        content_type = "image/svg+xml" if parsed_query.format == "svg" else "image/png"
        response = HttpResponse(image, content_type=content_type)
        if parsed_query.download:
            view_suffix = "-architecture" if parsed_query.view == "architecture" else ""
            filename = (
                f"{parsed_path.kind}-{entity.id}{view_suffix}.{parsed_query.format}"
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SystemLandscapeDiagramController(AtlasController):
    """Serve the catalog-wide System Landscape without an entity target."""

    auth = (SessionAuth(),)

    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            limit_to_content_types={"image/svg+xml"},
        ),
        ResponseSpec(ErrorModel, status_code=HTTPStatus.BAD_REQUEST),
        validate_responses=False,
    )
    def get(self, parsed_query: Query[DiagramQuery]) -> HttpResponse:
        check_diagram_read_permission(self.request.user)
        if parsed_query.view not in (None, "landscape"):
            raise APIError(
                format_error(
                    "Only the landscape diagram view is supported",
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.BAD_REQUEST,
            )
        try:
            image = c4.render(
                c4.build_system_landscape(
                    c4.DiagramRenderingSettings(
                        layout=parsed_query.layout,
                        show_title=parsed_query.show_title,
                        show_legend=parsed_query.show_legend,
                        show_selected_label=parsed_query.show_selected_label,
                        show_person_sprite=parsed_query.show_person_sprite,
                        show_stereotypes=parsed_query.show_stereotypes,
                    )
                ),
                format=parsed_query.format,
            )
        except c4.DiagramRenderError:
            logger.exception("C4 system landscape rendering failed")
            raise APIError(
                format_error(
                    "Unable to render diagram", error_type=ErrorType.value_error
                ),
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            ) from None
        content_type = "image/svg+xml" if parsed_query.format == "svg" else "image/png"
        response = HttpResponse(image, content_type=content_type)
        if parsed_query.download:
            response["Content-Disposition"] = (
                f'attachment; filename="system-landscape.{parsed_query.format}"'
            )
        return response


def custom_view_request(settings: CustomViewSettings) -> custom_view.CustomViewRequest:
    """Map validated view settings (request body or stored view) to a builder request."""
    return custom_view.CustomViewRequest(
        level=settings.level,
        selection=settings.selection,
        entities=tuple(settings.entities),
        depth=None if settings.depth == "all" else settings.depth,
        direction=settings.direction or "both",
        entity_types=(
            frozenset(settings.entity_types)
            if settings.entity_types is not None
            else None
        ),
        relationships=settings.relationships,
    )


def render_custom_view(
    settings: CustomViewSettings, query: DiagramQuery, filename: str
) -> HttpResponse:
    """Build, render, and wrap a custom view diagram; shared by preview and saved views."""
    try:
        payload = custom_view.build_custom_view(
            custom_view_request(settings),
            c4.DiagramRenderingSettings(
                layout=query.layout,
                show_title=query.show_title,
                show_legend=query.show_legend,
                show_selected_label=query.show_selected_label,
                show_person_sprite=query.show_person_sprite,
                show_stereotypes=query.show_stereotypes,
            ),
        )
    except CustomViewError as error:
        raise APIError(
            error.body(),  # type: ignore[arg-type]
            status_code=error.status_code,
        ) from None
    try:
        image = c4.render(payload, format=query.format)
    except c4.DiagramRenderError:
        logger.exception("C4 custom view rendering failed")
        raise APIError(
            format_error("Unable to render diagram", error_type=ErrorType.value_error),
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from None
    content_type = "image/svg+xml" if query.format == "svg" else "image/png"
    response = HttpResponse(image, content_type=content_type)
    if query.download:
        response["Content-Disposition"] = (
            f'attachment; filename="{filename}.{query.format}"'
        )
    return response


CUSTOM_VIEW_RESPONSES = (
    ResponseSpec(
        str,
        status_code=HTTPStatus.OK,
        limit_to_content_types={"image/svg+xml"},
    ),
    ResponseSpec(ErrorModel, status_code=HTTPStatus.BAD_REQUEST),
    ResponseSpec(ErrorModel, status_code=HTTPStatus.NOT_FOUND),
    ResponseSpec(ErrorModel, status_code=HTTPStatus.FORBIDDEN),
    ResponseSpec(ErrorModel, status_code=HTTPStatus.UNPROCESSABLE_ENTITY),
)


class CustomViewDiagramController(AtlasController):
    """Preview the diagram of unsaved view settings posted as a JSON body."""

    auth = (SessionAuth(),)

    @validate(
        *CUSTOM_VIEW_RESPONSES,
        validate_responses=False,
    )
    def post(
        self,
        parsed_body: Body[CustomViewSettings],
        parsed_query: Query[DiagramQuery],
    ) -> HttpResponse:
        check_diagram_read_permission(self.request.user)
        return render_custom_view(parsed_body, parsed_query, "custom-view")


class ActorKindsController(AtlasController):
    """List the entity kinds that act as C4 actors, for the view builder's picker."""

    auth = (SessionAuth(),)

    @modify(
        extra_responses=[ResponseSpec(ErrorModel, status_code=HTTPStatus.FORBIDDEN)]
    )
    def get(self) -> ActorKindsOut:
        check_diagram_read_permission(self.request.user)
        return ActorKindsOut.model_validate({"items": custom_view.actor_kinds()})


def _view_out(view: View) -> ViewOut:
    settings = CustomViewSettings.model_validate(view.settings)
    return ViewOut(
        id=view.id,
        name=view.name,
        description=view.description,
        settings=settings,
        missing_entities=custom_view.missing_entity_ids(settings.entities),
        created_at=view.created_at,
        updated_at=view.updated_at,
    )


def _view_not_found() -> APIError:
    return APIError(
        format_error("View not found", error_type=ErrorType.not_found),
        status_code=HTTPStatus.NOT_FOUND,
    )


def _duplicate_name() -> APIError:
    return APIError(
        format_error(
            "A view with this name already exists",
            loc=["parsed_body", "name"],
            error_type=ErrorType.value_error,
        ),
        status_code=HTTPStatus.BAD_REQUEST,
    )


def _validate_view_body(body: ViewIn, view: View | None = None) -> None:
    """Resolve the selection (unknown, removed, or level-incompatible entities are
    rejected by name) and check the name is free, ignoring case."""
    try:
        custom_view.resolve_selection(custom_view_request(body.settings))
    except CustomViewError as error:
        raise APIError(
            error.body(),  # type: ignore[arg-type]
            status_code=error.status_code,
        ) from None
    taken = View.objects.filter(name__iexact=body.name)
    if view is not None:
        taken = taken.exclude(pk=view.pk)
    if taken.exists():
        raise _duplicate_name()


def _store_view(view: View, body: ViewIn) -> View:
    view.name = body.name
    view.description = body.description
    view.settings = body.settings.model_dump(mode="json", by_alias=True)
    try:
        with transaction.atomic():
            view.save()
    except IntegrityError:
        # Lost a race against another save of the same name.
        raise _duplicate_name() from None
    return view


_VALIDATION_RESPONSES = (
    ResponseSpec(ErrorModel, status_code=HTTPStatus.NOT_FOUND),
    ResponseSpec(ErrorModel, status_code=HTTPStatus.BAD_REQUEST),
)


class ViewListController(AtlasController):
    """List and create saved views. Views are shared; see `plugin.VIEW_CREATE_PERMISSION`."""

    auth = (SessionAuth(),)

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def get(self, parsed_query: Query[ViewListFilters]) -> PaginatedOut[ViewOut]:
        check_diagram_read_permission(self.request.user)
        queryset = View.objects.all()
        if parsed_query.q:
            queryset = queryset.filter(name__icontains=parsed_query.q)
        page = Paginator(
            queryset.order_by(parsed_query.sort, "id"), parsed_query.page_size
        ).page(parsed_query.page)
        return PaginatedOut(
            count=page.paginator.count,
            num_pages=page.paginator.num_pages,
            per_page=page.paginator.per_page,
            page=PageOut(
                number=page.number,
                object_list=[_view_out(view) for view in page.object_list],
            ),
        )

    @modify(
        status_code=HTTPStatus.CREATED,
        extra_responses=[FORBIDDEN_RESPONSE, *_VALIDATION_RESPONSES],
    )
    def post(self, parsed_body: Body[ViewIn]) -> ViewOut:
        check_view_write_permission(self.request.user)
        _validate_view_body(parsed_body)
        return _view_out(_store_view(View(), parsed_body))


class ViewDetailController(AtlasController):
    auth = (SessionAuth(),)

    @modify(extra_responses=[FORBIDDEN_RESPONSE, *_VALIDATION_RESPONSES])
    def get(self, parsed_path: Path[ViewPath]) -> ViewOut:
        check_diagram_read_permission(self.request.user)
        return _view_out(_get_view(parsed_path.id))

    @modify(extra_responses=[FORBIDDEN_RESPONSE, *_VALIDATION_RESPONSES])
    def put(self, parsed_path: Path[ViewPath], parsed_body: Body[ViewIn]) -> ViewOut:
        check_view_write_permission(self.request.user)
        view = _get_view(parsed_path.id)
        _validate_view_body(parsed_body, view)
        return _view_out(_store_view(view, parsed_body))

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        extra_responses=[FORBIDDEN_RESPONSE, *_VALIDATION_RESPONSES],
    )
    def delete(self, parsed_path: Path[ViewPath]) -> None:
        check_view_delete_permission(self.request.user)
        _get_view(parsed_path.id).delete()


class ViewDiagramController(AtlasController):
    """Serve the diagram of a saved view; a removed entity fails with `unknown_entity`."""

    auth = (SessionAuth(),)

    @validate(*CUSTOM_VIEW_RESPONSES, validate_responses=False)
    def get(
        self, parsed_path: Path[ViewPath], parsed_query: Query[DiagramQuery]
    ) -> HttpResponse:
        check_diagram_read_permission(self.request.user)
        view = _get_view(parsed_path.id)
        return render_custom_view(
            CustomViewSettings.model_validate(view.settings),
            parsed_query,
            f"view-{view.id}",
        )


def _get_view(view_id) -> View:
    try:
        return View.objects.get(pk=view_id)
    except View.DoesNotExist:
        raise _view_not_found() from None
