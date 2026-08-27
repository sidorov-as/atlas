"""Diagram controllers — split out of `server.apps.catalog.api.views`.

Every request additionally checks the `atlas.c4.diagram.read` permission
on top of `SessionAuth`'s authenticated-session check.
"""

import logging
from http import HTTPStatus

from atlas_plugin_api import (
    KIND_COMPONENT,
    KIND_SYSTEM,
    SessionAuth,
    get_catalog_entity_model,
)
from atlas_plugin_api.controllers import AtlasController
from django.http import HttpResponse
from dmr import Path, Query, ResponseSpec, validate
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.response import APIError

from .. import c4
from ..permissions import check_diagram_read_permission
from .schemas import DiagramPath, DiagramQuery

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
