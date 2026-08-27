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

from atlas_plugin_api import entity_deprecated
from django.db.models import Q
from dmr import Body, Path, Query, modify
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from server.apps.catalog import refs
from server.apps.catalog.authorization import is_account_read_only
from server.apps.catalog.models import (
    INGESTIBLE_KINDS,
    ArchitectureRelationship,
    CatalogEntity,
    CatalogHomeSettings,
    Tag,
    ensure_tags_exist,
)

from .auth import SessionAuth
from .helpers import FORBIDDEN_RESPONSE, AtlasController
from .permissions import (
    CatalogHomeSettingsWritePermission,
    EntityWritePermission,
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


def _get_architecture_relationship(pk: int) -> ArchitectureRelationship:
    try:
        return ArchitectureRelationship.objects.select_related(
            "source", "target"
        ).get(pk=pk)
    except ArchitectureRelationship.DoesNotExist:
        raise APIError(
            format_error(
                "Architecture relationship not found",
                error_type=ErrorType.not_found,
            ),
            status_code=HTTPStatus.NOT_FOUND,
        ) from None


def _manual_relationship_source(ref: str) -> CatalogEntity:
    source = refs.resolve_ref(ref)
    if source.kind not in INGESTIBLE_KINDS:
        raise APIError(
            format_error(
                "Architecture relationship sources must be System, "
                "Component, Resource, or API entities",
                error_type=ErrorType.value_error,
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )
    return source


def _check_relationship_write(
    request, relationship: ArchitectureRelationship
) -> CatalogEntity:
    if relationship.origin == ArchitectureRelationship.Origin.YAML:
        raise APIError(
            format_error(
                "YAML-origin architecture relationships are read-only",
                error_type=ErrorType.security,
            ),
            status_code=HTTPStatus.FORBIDDEN,
        )
    source = relationship.source
    if source.kind not in INGESTIBLE_KINDS:
        raise APIError(
            format_error(
                "Architecture relationship source not found",
                error_type=ErrorType.not_found,
            ),
            status_code=HTTPStatus.NOT_FOUND,
        )
    EntityWritePermission.check_write(request.user, source)
    return source


class ArchitectureRelationshipListController(AtlasController):
    """List directed participation or create a manual relationship."""

    auth = (SessionAuth(),)

    def get(
        self, parsed_query: Query[ArchitectureRelationshipQuery]
    ) -> list[ArchitectureRelationshipOut]:
        source = refs.resolve_ref(parsed_query.source)
        relationships = (
            ArchitectureRelationship.objects.filter(
                Q(source=source) | Q(target=source),
            )
            .select_related("source", "target")
            .order_by("id")
        )
        return [
            _architecture_relationship_out(relationship)
            for relationship in relationships
        ]

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def post(
        self, parsed_body: Body[ArchitectureRelationshipIn]
    ) -> ArchitectureRelationshipOut:
        source = _manual_relationship_source(parsed_body.source)
        EntityWritePermission.check_write(self.request.user, source)
        target = refs.resolve_ref(parsed_body.target)
        relationship = ArchitectureRelationship.objects.create(
            source=source,
            target=target,
            label=parsed_body.label,
            technology=parsed_body.technology,
            interaction_kind=parsed_body.interaction_kind,
            tags=parsed_body.tags,
            origin=ArchitectureRelationship.Origin.MANUAL,
        )
        ensure_tags_exist(parsed_body.tags)
        return _architecture_relationship_out(relationship)


class ArchitectureRelationshipDetailController(AtlasController):
    auth = (SessionAuth(),)

    def get(
        self, parsed_path: Path[ArchitectureRelationshipPath]
    ) -> ArchitectureRelationshipOut:
        return _architecture_relationship_out(
            _get_architecture_relationship(parsed_path.id)
        )

    @modify(extra_responses=[FORBIDDEN_RESPONSE])
    def patch(
        self,
        parsed_path: Path[ArchitectureRelationshipPath],
        parsed_body: Body[ArchitectureRelationshipPatch],
    ) -> ArchitectureRelationshipOut:
        relationship = _get_architecture_relationship(parsed_path.id)
        _check_relationship_write(self.request, relationship)
        fields = parsed_body.model_fields_set
        if "target" in fields:
            relationship.target = refs.resolve_ref(parsed_body.target)
        for field in ("label", "technology", "interaction_kind", "tags"):
            if field in fields:
                setattr(relationship, field, getattr(parsed_body, field))
        if "tags" in fields:
            ensure_tags_exist(parsed_body.tags)
        relationship.save()
        return _architecture_relationship_out(relationship)

    @modify(
        status_code=HTTPStatus.NO_CONTENT, extra_responses=[FORBIDDEN_RESPONSE]
    )
    def delete(self, parsed_path: Path[ArchitectureRelationshipPath]) -> None:
        relationship = _get_architecture_relationship(parsed_path.id)
        _check_relationship_write(self.request, relationship)
        relationship.delete()


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
