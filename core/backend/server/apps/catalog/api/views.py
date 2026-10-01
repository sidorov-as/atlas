"""Entity CRUD controllers for the kinds still owned by `server.apps.catalog`
ArchitectureRelationship and Tag. Flow's
controllers moved to `atlas_plugin_flows.api.views`;
System/Component/Resource/Group/Actor's controllers moved to
`atlas_plugin_standard_catalog.api.views`,
API's to `atlas_plugin_apis.api.views`, the generated
C4 diagram endpoints to `atlas_plugin_c4.api.views` —
shared helpers both modules use live in `.helpers`.

Every entity is one `CatalogEntity` row joined to its kind-specific
`*Details` row — `_get_<kind>` fetches
the `CatalogEntity` with the matching `kind` filter and the right
`select_related`/`prefetch_related` path into its details, for reads and for
the pre-write existence/kind check. API writes (create/update/delete) go
exclusively through the core `EntityService` — this module owns request
parsing, response shaping, and the
`_get_<kind>` 404/kind guard, not persistence.
"""

from http import HTTPStatus

from atlas_plugin_api import (
    ArchitectureRelationshipNotFoundError,
    ArchitectureRelationshipReadOnlyError,
    ArchitectureRelationshipSourceKindError,
    entity_deprecated,
)
from dmr import Body, Path, Query, modify
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from server.apps.catalog.authorization import is_account_read_only
from server.apps.catalog.models import (
    ArchitectureRelationship,
    CatalogHomeSettings,
    Tag,
)
from server.apps.catalog.services.architecture_relationship_service import (
    architecture_relationship_service,
)

from .auth import SessionAuth
from .helpers import FORBIDDEN_RESPONSE, AtlasController
from .permissions import (
    CatalogHomeSettingsWritePermission,
    TagWritePermission,
)
from .schemas import (
    ArchitectureRelationshipIn,
    ArchitectureRelationshipOut,
    ArchitectureRelationshipPatch,
    ArchitectureRelationshipPath,
    ArchitectureRelationshipQuery,
    CatalogHomeSettingsOut,
    CatalogHomeSettingsPatch,
    MeOut,
    TagOut,
    TagPatch,
    TagPath,
)


class MeController(AtlasController):
    """Authorization-role signal for the current session

    Separate from allauth's own headless session endpoint on purpose
    allauth owns authentication identity, this
    Atlas-owned endpoint owns the `isAdmin`/`isReadOnly` role signals.
    """

    auth = (SessionAuth(),)

    def get(self) -> MeOut:
        return MeOut(
            is_admin=self.request.user.is_superuser,
            is_read_only=is_account_read_only(self.request.user),
        )


def _architecture_relationship_out(
    instance: ArchitectureRelationship,
) -> ArchitectureRelationshipOut:
    return ArchitectureRelationshipOut(
        id=instance.id,
        source=instance.source.ref,
        source_kind=instance.source.kind,
        source_id=instance.source.id,
        source_status=instance.source.status,
        source_deprecated=entity_deprecated(instance.source),
        target=instance.target.ref,
        target_kind=instance.target.kind,
        target_id=instance.target.id,
        target_status=instance.target.status,
        target_deprecated=entity_deprecated(instance.target),
        label=instance.label,
        technology=instance.technology,
        interaction_kind=instance.interaction_kind,
        tags=instance.tags,
        origin=instance.origin,
    )


def _relationship_error(exc: Exception) -> APIError:
    """Map the service's contract exceptions to the REST error shapes the
    controllers have always returned."""
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
            format_error(str(exc), error_type=ErrorType.security),
            status_code=HTTPStatus.FORBIDDEN,
        )
    return APIError(
        format_error(str(exc), error_type=ErrorType.value_error),
        status_code=HTTPStatus.BAD_REQUEST,
    )


_RELATIONSHIP_ERRORS = (
    ArchitectureRelationshipNotFoundError,
    ArchitectureRelationshipReadOnlyError,
    ArchitectureRelationshipSourceKindError,
)


class ArchitectureRelationshipListController(AtlasController):
    """List directed participation or create a manual relationship."""

    auth = (SessionAuth(),)

    def get(
        self, parsed_query: Query[ArchitectureRelationshipQuery]
    ) -> list[ArchitectureRelationshipOut]:
        relationships = architecture_relationship_service.list_for_entity(
            entity_ref=parsed_query.source
        )
        return [
            _architecture_relationship_out(relationship)
            for relationship in relationships
        ]

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def post(
        self, parsed_body: Body[ArchitectureRelationshipIn]
    ) -> ArchitectureRelationshipOut:
        try:
            relationship = architecture_relationship_service.create(
                source_ref=parsed_body.source,
                target_ref=parsed_body.target,
                label=parsed_body.label,
                technology=parsed_body.technology,
                interaction_kind=parsed_body.interaction_kind,
                tags=parsed_body.tags,
                actor=self.request.user,
            )
        except _RELATIONSHIP_ERRORS as exc:
            raise _relationship_error(exc) from None
        return _architecture_relationship_out(relationship)


class ArchitectureRelationshipDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(
        self, parsed_path: Path[ArchitectureRelationshipPath]
    ) -> ArchitectureRelationshipOut:
        try:
            relationship = architecture_relationship_service.get(parsed_path.id)
        except _RELATIONSHIP_ERRORS as exc:
            raise _relationship_error(exc) from None
        return _architecture_relationship_out(relationship)

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self,
        parsed_path: Path[ArchitectureRelationshipPath],
        parsed_body: Body[ArchitectureRelationshipPatch],
    ) -> ArchitectureRelationshipOut:
        fields = {
            field: getattr(parsed_body, field)
            for field in parsed_body.model_fields_set
        }
        try:
            relationship = architecture_relationship_service.update(
                relationship_id=parsed_path.id,
                fields=fields,
                actor=self.request.user,
            )
        except _RELATIONSHIP_ERRORS as exc:
            raise _relationship_error(exc) from None
        return _architecture_relationship_out(relationship)

    @modify(
        status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE]
    )
    def delete(self, parsed_path: Path[ArchitectureRelationshipPath]) -> None:
        try:
            architecture_relationship_service.delete(
                relationship_id=parsed_path.id, actor=self.request.user
            )
        except _RELATIONSHIP_ERRORS as exc:
            raise _relationship_error(exc) from None


# --- Tag (admin-managed color config) ----------------------------------------


def _tag_out(instance: Tag) -> TagOut:
    return TagOut(id=instance.id, name=instance.name, color=instance.color)


def _get_tag(pk: int) -> Tag:
    try:
        return Tag.objects.get(pk=pk)
    except Tag.DoesNotExist:
        raise APIError(
            format_error("Tag not found", error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


class TagListController(AtlasController):
    auth = (SessionAuth(),)

    def get(self) -> list[TagOut]:
        return [_tag_out(instance) for instance in Tag.objects.all()]


class TagDetailController(AtlasController):
    auth = (SessionAuth(),)

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self, parsed_path: Path[TagPath], parsed_body: Body[TagPatch]
    ) -> TagOut:
        TagWritePermission.check_write(self.request)
        instance = _get_tag(parsed_path.id)
        instance.color = parsed_body.color
        instance.save(update_fields=["color"])
        return _tag_out(instance)


# --- Catalog Home Settings (admin-editable "About this catalog") ------------


class CatalogHomeSettingsController(AtlasController):
    auth = (SessionAuth(),)

    def get(self) -> CatalogHomeSettingsOut:
        instance = CatalogHomeSettings.get_solo()
        return CatalogHomeSettingsOut(about_markdown=instance.about_markdown)

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self, parsed_body: Body[CatalogHomeSettingsPatch]
    ) -> CatalogHomeSettingsOut:
        CatalogHomeSettingsWritePermission.check_write(self.request)
        instance = CatalogHomeSettings.get_solo()
        instance.about_markdown = parsed_body.about_markdown
        instance.save(update_fields=["about_markdown"])
        return CatalogHomeSettingsOut(about_markdown=instance.about_markdown)
