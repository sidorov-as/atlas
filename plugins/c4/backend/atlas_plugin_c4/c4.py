"""Small, local-only C4 rendering adapter for catalog diagrams.

The public functions in this module deliberately accept JSON-compatible
payloads.  ``c4-diagrams`` validates those payloads before rendering, keeping
PlantUML-specific syntax and aliases out of controllers and catalog models.
"""

import logging
from collections.abc import Iterable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from atlas_plugin_api import (
    ARCHITECTURE_ACTOR_V1,
    KIND_ACTOR,
    KIND_API,
    KIND_COMPONENT,
    KIND_RESOURCE,
    KIND_SYSTEM,
    Ok,
    get_architecture_relationship_model,
    get_catalog_entity_model,
    get_plugin_config,
    get_relation_model,
    resolve_capability,
)
from c4.converters.exceptions import (
    ConversionError,
    DiagramJSONSchemaValidationError,
)
from c4.converters.json.converter import diagram_from_dict
from c4.exceptions import PlantUMLError, PlantUMLRemoteRenderingError
from c4.renderers.plantuml import (
    LocalPlantUMLBackend,
    PlantUMLRenderer,
    RemotePlantUMLBackend,
)
from c4.renderers.plantuml.backends import DiagramFormat
from django.db.models import Q

from .config import C4PluginConfig

logger = logging.getLogger(__name__)

ImageFormat = Literal["svg", "png"]
DiagramLayout = Literal[
    "LAYOUT_TOP_DOWN",
    "LAYOUT_LEFT_RIGHT",
    "LAYOUT_LANDSCAPE",
]

DIAGRAM_LAYOUTS: tuple[DiagramLayout, ...] = (
    "LAYOUT_TOP_DOWN",
    "LAYOUT_LEFT_RIGHT",
    "LAYOUT_LANDSCAPE",
)


@dataclass(frozen=True)
class DiagramRenderingSettings:
    """Presentation settings supported by the catalog C4 renderer."""

    layout: DiagramLayout = "LAYOUT_TOP_DOWN"
    show_title: bool = True
    show_legend: bool = True
    show_selected_label: bool = True
    show_person_sprite: bool = True
    show_stereotypes: bool = True


DEFAULT_DIAGRAM_RENDERING_SETTINGS = DiagramRenderingSettings()


def _is_actor_kind(kind: str) -> bool:
    """Whether `kind` renders as a C4 Person.

    Driven entirely by the `architecture.actor.v1` capability declaration
    `group` and `actor` declare it — rather
    than a hard-coded kind list.

    Uses the typed `resolve_capability`
    rather than `capabilities_for`: an Unavailable Entity's kind (no
    handler currently registered) renders as a non-actor here, same as a
    registered kind that simply doesn't declare the capability — the two
    only need to be distinguished by callers that must react differently
    to "unavailable", which this one doesn't.
    """
    match resolve_capability(kind, ARCHITECTURE_ACTOR_V1):
        case Ok(has_capability):
            return has_capability
        case _:
            return False


_FORWARD_CROSS_SYSTEM_PREDICATES = frozenset(
    {"consumesAPI", "providesAPI", "dependsOn"},
)

_ELEMENT_TAGS = {
    "selected_system": "AtlasSelectedSystem",
    "selected_component": "AtlasSelectedComponent",
    "component": "AtlasComponent",
    "database": "AtlasDatabase",
    "queue": "AtlasQueue",
    "endpoint": "AtlasEndpoint",
    "external_endpoint": "AtlasExternalEndpoint",
    "person": "AtlasPerson",
}
_INTERACTION_TAGS = {
    "synchronous": "AtlasSynchronous",
    "asynchronous": "AtlasAsynchronous",
    "data-access": "AtlasDataAccess",
    "manual": "AtlasManual",
}
_DERIVED_RELATIONSHIP_TAG = "AtlasDerived"

_ATLAS_PLANTUML_TAGS = (
    (
        "ElementTag",
        _ELEMENT_TAGS["selected_system"],
        "#e3f2fd",
        "#0d47a1",
        "#42a5f5",
        "BoldLine",
        "2",
        True,
        "Selected System",
    ),
    (
        "ElementTag",
        _ELEMENT_TAGS["selected_component"],
        "#e3f2fd",
        "#0d47a1",
        "#42a5f5",
        "BoldLine",
        "2",
        True,
        "Selected Component",
    ),
    (
        "ElementTag",
        _ELEMENT_TAGS["component"],
        "#e8f5e9",
        "#1b5e20",
        "#66bb6a",
        "SolidLine",
        "2",
        True,
        "Internal Component",
    ),
    (
        "ElementTag",
        _ELEMENT_TAGS["database"],
        "#fff8e1",
        "#5d4037",
        "#ffb300",
        "SolidLine",
        "1",
        False,
        "Database",
    ),
    (
        "ElementTag",
        _ELEMENT_TAGS["queue"],
        "#f3e5f5",
        "#6a1b9a",
        "#ab47bc",
        "SolidLine",
        "1",
        False,
        "Queue",
    ),
    (
        "ElementTag",
        _ELEMENT_TAGS["endpoint"],
        "#e3f2fd",
        "#0d47a1",
        "#42a5f5",
        "SolidLine",
        "2",
        True,
        "API or Resource",
    ),
    (
        "ElementTag",
        _ELEMENT_TAGS["external_endpoint"],
        "#f5f5f5",
        "#424242",
        "#9e9e9e",
        "DashedLine",
        "1",
        False,
        "External Endpoint",
    ),
    (
        "ElementTag",
        _ELEMENT_TAGS["person"],
        "#fff3e0",
        "#e65100",
        "#fb8c00",
        "SolidLine",
        "2",
        True,
        "Person or Group",
    ),
)
_ATLAS_PLANTUML_RELATIONSHIP_TAGS = (
    (
        _INTERACTION_TAGS["synchronous"],
        "#1565c0",
        "#1e88e5",
        "SolidLine",
        "1",
        "Synchronous Interaction",
    ),
    (
        _INTERACTION_TAGS["asynchronous"],
        "#6a1b9a",
        "#8e24aa",
        "DottedLine",
        "2",
        "Asynchronous Interaction",
    ),
    (
        _INTERACTION_TAGS["data-access"],
        "#6d4c41",
        "#8d6e63",
        "DashedLine",
        "1",
        "Data Access",
    ),
    (
        _INTERACTION_TAGS["manual"],
        "#455a64",
        "#78909c",
        "DashedLine",
        "1",
        "Manual Interaction",
    ),
    (
        _DERIVED_RELATIONSHIP_TAG,
        "#455a64",
        "#78909c",
        "DashedLine",
        "1",
        "Derived Catalog Relation",
    ),
)


class DiagramRenderError(RuntimeError):
    """A controlled failure suitable for conversion to a generic API error."""


def alias(kind: str, pk: UUID | int) -> str:
    """Return a deterministic, PlantUML-safe catalog element alias.

    `pk` is a `CatalogEntity.id` (UUID) — `.hex` strips the dashes PlantUML
    aliases can't contain.
    """
    suffix = pk.hex if isinstance(pk, UUID) else str(pk)
    return f"{kind}_{suffix}"


def is_external(tags: Iterable[str]) -> bool:
    """Whether catalog tags explicitly identify an external endpoint."""
    return any(tag.casefold() == "external" for tag in tags)


def element(
    *,
    type: str,
    kind: str,
    pk: UUID | int,
    label: str,
    description: str = "",
    technology: str = "",
    tags: Iterable[str] = (),
) -> dict[str, str]:
    """Build one strict JSON element understood by ``c4-diagrams``."""
    value = {"type": type, "alias": alias(kind, pk), "label": label}
    if description:
        value["description"] = description
    if technology:
        value["technology"] = technology
    if tags:
        value["tags"] = list(tags)
    return value


def relationship(
    *,
    source_kind: str,
    source_id: UUID | int,
    target_kind: str,
    target_id: UUID | int,
    label: str,
    technology: str = "",
    tags: Iterable[str] = (),
) -> dict[str, str]:
    """Build one directed C4 ``REL`` payload using stable aliases."""
    value = {
        "type": "REL",
        "from": alias(source_kind, source_id),
        "to": alias(target_kind, target_id),
        "label": label,
    }
    if technology:
        value["technology"] = technology
    if tags:
        value["tags"] = list(tags)
    return value


def render_options_payload(
    settings: DiagramRenderingSettings,
) -> dict[str, Any]:
    """Map supported settings to the constrained PlantUML payload options."""
    options: dict[str, Any] = {
        "layout": settings.layout,
        "hide_stereotype": not settings.show_stereotypes,
        "hide_person_sprite": not settings.show_person_sprite,
    }
    if settings.show_legend:
        options["show_legend"] = {}
        options["legend_title"] = "Atlas C4 diagram semantics"
    return options


def diagram_payload(
    *,
    diagram_type: Literal["SystemContextDiagram", "ComponentDiagram"],
    title: str,
    elements: Iterable[Mapping[str, Any]],
    relationships: Iterable[Mapping[str, Any]],
    settings: DiagramRenderingSettings = DEFAULT_DIAGRAM_RENDERING_SETTINGS,
) -> dict[str, Any]:
    """Build the complete validated PlantUML diagram payload.

    The values are intentionally conservative and stable so diagrams do not
    inherit arbitrary visual configuration from catalog tags.
    """
    return {
        "backend": "plantuml",
        "type": diagram_type,
        "title": title if settings.show_title else None,
        "elements": [dict(item) for item in elements],
        "relationships": [dict(item) for item in relationships],
        "render_options": render_options_payload(settings)
        | {
            "tags": [
                {
                    "type": tag_type,
                    "tag_stereo": tag_stereo,
                    "bg_color": background,
                    "font_color": font,
                    "border_color": border,
                    "border_style": border_style,
                    "border_thickness": border_thickness,
                    "shadowing": shadowing,
                    "shape": "RoundedBoxShape",
                    "legend_text": legend,
                }
                for (
                    tag_type,
                    tag_stereo,
                    background,
                    font,
                    border,
                    border_style,
                    border_thickness,
                    shadowing,
                    legend,
                ) in _ATLAS_PLANTUML_TAGS
            ]
            + [
                {
                    "type": "RelTag",
                    "tag_stereo": tag_stereo,
                    "text_color": text_color,
                    "line_color": line_color,
                    "line_style": line_style,
                    "line_thickness": line_thickness,
                    "legend_text": legend,
                }
                for (
                    tag_stereo,
                    text_color,
                    line_color,
                    line_style,
                    line_thickness,
                    legend,
                ) in _ATLAS_PLANTUML_RELATIONSHIP_TAGS
            ],
        },
    }


def build_system_context(
    system,
    settings: DiagramRenderingSettings = DEFAULT_DIAGRAM_RENDERING_SETTINGS,
) -> dict[str, Any]:
    """Build a deterministic C4 System Context payload for ``system``.

    Structural catalog relationships are reduced to system-to-system ``Uses``
    edges.  Declared architecture relationships retain their label and
    technology, but Component/API/Resource endpoints are similarly represented
    by their containing System.  Users and Groups deliberately have no
    ownership-derived path here: they appear only as explicit endpoints.
    """
    ArchitectureRelationship = get_architecture_relationship_model()
    Relation = get_relation_model()

    visible: dict[tuple[str, Any], Any] = {(system.kind, system.id): system}
    explicit_edges: dict[tuple[str, str], dict[str, str]] = {}
    derived_edges: dict[tuple[str, str], dict[str, str]] = {}

    for declared in ArchitectureRelationship.objects.select_related(
        "source", "target"
    ).order_by("pk"):
        source = _context_endpoint(declared.source)
        target = _context_endpoint(declared.target)
        if source is None or target is None or source == target:
            continue
        if system not in (source, target):
            continue
        visible[source.kind, source.id] = source
        visible[target.kind, target.id] = target
        edge = relationship(
            source_kind=source.kind,
            source_id=source.id,
            target_kind=target.kind,
            target_id=target.id,
            label=declared.label,
            technology=declared.technology,
            tags=(_interaction_tag(declared.interaction_kind),),
        )
        explicit_edges[_endpoint_key(edge)] = edge

    derived_relations = (
        Relation.objects.filter(
            predicate__in=_FORWARD_CROSS_SYSTEM_PREDICATES,
        )
        .select_related("subject_entity", "object_entity")
        .order_by(
            "subject_entity",
            "predicate",
            "object_entity",
        )
    )
    for derived in derived_relations:
        source = _context_endpoint(derived.subject_entity)
        target = _context_endpoint(derived.object_entity)
        if source is None or target is None or source == target or source != system:
            continue
        visible[target.kind, target.id] = target
        edge = relationship(
            source_kind=source.kind,
            source_id=source.id,
            target_kind=target.kind,
            target_id=target.id,
            label="Uses",
            tags=(_DERIVED_RELATIONSHIP_TAG,),
        )
        derived_edges.setdefault(_endpoint_key(edge), edge)

    elements = [
        _context_element(entity, selected=entity == system)
        for entity in visible.values()
    ]
    elements.sort(key=lambda value: value["alias"])
    return diagram_payload(
        diagram_type="SystemContextDiagram",
        title=f"{_display_name(system)} — System Context",
        elements=elements,
        relationships=_merge_edges(explicit_edges, derived_edges),
        settings=settings,
    )


def build_system_landscape(
    settings: DiagramRenderingSettings = DEFAULT_DIAGRAM_RENDERING_SETTINGS,
) -> dict[str, Any]:
    """Build the catalog-wide, deterministic System Landscape payload.

    Systems are always present. Users and Groups are deliberately included only
    when an authored Architecture Relationship explicitly names them; ownership
    is never used to infer actors. System-bound endpoints collapse to their
    owning System and declared edges override derived edges with the same
    directed visible endpoints.
    """
    ArchitectureRelationship = get_architecture_relationship_model()
    Relation = get_relation_model()

    visible: dict[tuple[str, Any], Any] = {
        (system.kind, system.id): system
        for system in get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM)
        .order_by("name", "pk")
    }
    explicit_edges: dict[tuple[str, str], dict[str, str]] = {}
    derived_edges: dict[tuple[str, str], dict[str, str]] = {}

    for declared in ArchitectureRelationship.objects.select_related(
        "source", "target"
    ).order_by("pk"):
        source = _context_endpoint(declared.source)
        target = _context_endpoint(declared.target)
        if source is None or target is None or source == target:
            continue
        visible[source.kind, source.id] = source
        visible[target.kind, target.id] = target
        edge = relationship(
            source_kind=source.kind,
            source_id=source.id,
            target_kind=target.kind,
            target_id=target.id,
            label=declared.label,
            technology=declared.technology,
            tags=(_interaction_tag(declared.interaction_kind),),
        )
        explicit_edges[_endpoint_key(edge)] = edge

    for derived in (
        Relation.objects.filter(
            predicate__in=_FORWARD_CROSS_SYSTEM_PREDICATES,
        )
        .select_related("subject_entity", "object_entity")
        .order_by(
            "subject_entity",
            "predicate",
            "object_entity",
        )
    ):
        source = _context_endpoint(derived.subject_entity)
        target = _context_endpoint(derived.object_entity)
        if source is None or target is None or source == target:
            continue
        edge = relationship(
            source_kind=source.kind,
            source_id=source.id,
            target_kind=target.kind,
            target_id=target.id,
            label="Uses",
            tags=(_DERIVED_RELATIONSHIP_TAG,),
        )
        derived_edges.setdefault(_endpoint_key(edge), edge)

    elements = [_context_element(entity, selected=False) for entity in visible.values()]
    elements.sort(key=lambda value: value["alias"])
    return diagram_payload(
        diagram_type="SystemContextDiagram",
        title="Atlas — System Landscape",
        elements=elements,
        relationships=_merge_edges(explicit_edges, derived_edges),
        settings=settings,
    )


def build_component_diagram(
    component,
    settings: DiagramRenderingSettings = DEFAULT_DIAGRAM_RENDERING_SETTINGS,
) -> dict[str, Any]:
    """Build the System-scoped Component Diagram for ``component``."""
    ArchitectureRelationship = get_architecture_relationship_model()
    Relation = get_relation_model()

    system_entity = component.component_details.system
    visible = {
        (item.kind, item.id): item
        for item in get_catalog_entity_model().objects.filter(
            kind=KIND_COMPONENT,
            component_details__system=system_entity,
        )
    }
    visible[component.kind, component.id] = component

    direct_entities: dict[tuple[str, Any], Any] = {}
    details = component.component_details
    for item in details.provides_apis.all():
        direct_entities[item.kind, item.id] = item
    for item in details.consumes_apis.all():
        direct_entities[item.kind, item.id] = item
    for item in details.depends_on.all():
        direct_entities[item.kind, item.id] = item

    declared = list(
        ArchitectureRelationship.objects.select_related("source", "target").order_by(
            "pk"
        ),
    )
    for item in declared:
        if item.source_id == component.id:
            direct_entities[item.target.kind, item.target.id] = item.target
        if item.target_id == component.id:
            direct_entities[item.source.kind, item.source.id] = item.source
    for key, entity in direct_entities.items():
        visible.setdefault(key, entity)

    explicit_edges: dict[tuple[str, str], dict[str, str]] = {}
    derived_edges: dict[tuple[str, str], dict[str, str]] = {}
    for item in declared:
        key = (item.source.kind, item.source.id)
        target_key = (item.target.kind, item.target.id)
        if key not in visible or target_key not in visible:
            continue
        edge = relationship(
            source_kind=item.source.kind,
            source_id=item.source.id,
            target_kind=item.target.kind,
            target_id=item.target.id,
            label=item.label,
            technology=item.technology,
            tags=(_interaction_tag(item.interaction_kind),),
        )
        explicit_edges[_endpoint_key(edge)] = edge
    for item in (
        Relation.objects.filter(
            predicate__in=_FORWARD_CROSS_SYSTEM_PREDICATES,
        )
        .select_related("subject_entity", "object_entity")
        .order_by(
            "subject_entity",
            "predicate",
            "object_entity",
        )
    ):
        key = (item.subject_entity.kind, item.subject_entity.id)
        target_key = (item.object_entity.kind, item.object_entity.id)
        if key not in visible or target_key not in visible:
            continue
        edge = relationship(
            source_kind=item.subject_entity.kind,
            source_id=item.subject_entity.id,
            target_kind=item.object_entity.kind,
            target_id=item.object_entity.id,
            label="Uses",
            tags=(_DERIVED_RELATIONSHIP_TAG,),
        )
        derived_edges.setdefault(_endpoint_key(edge), edge)

    elements = [
        _component_element(
            item,
            selected=item == component,
            show_selected_label=settings.show_selected_label,
            system=system_entity,
        )
        for item in visible.values()
    ]
    elements.sort(key=lambda value: value["alias"])
    return diagram_payload(
        diagram_type="ComponentDiagram",
        title=f"{_display_name(component)} — Component Diagram",
        elements=elements,
        relationships=_merge_edges(explicit_edges, derived_edges),
        settings=settings,
    )


def build_system_architecture(
    system,
    settings: DiagramRenderingSettings = DEFAULT_DIAGRAM_RENDERING_SETTINGS,
) -> dict[str, Any]:
    """Build the internal Component Diagram scope for ``system``.

    All Components, APIs, and Resources owned by the selected System are
    visible.  Entities outside that scope appear only when a declared
    architecture relationship or supported derived catalog relation directly
    connects them to an internal endpoint.  Declared edges take precedence
    over generic derived edges with the same directed visible endpoints.
    """
    ArchitectureRelationship = get_architecture_relationship_model()
    Relation = get_relation_model()

    visible = {
        (item.kind, item.id): item
        for item in get_catalog_entity_model().objects.filter(
            Q(kind=KIND_COMPONENT, component_details__system=system)
            | Q(kind=KIND_API, api_details__system=system)
            | Q(kind=KIND_RESOURCE, resource_details__system=system),
        )
    }
    internal_keys = frozenset(visible)
    declared = list(
        ArchitectureRelationship.objects.select_related("source", "target").order_by(
            "pk"
        )
    )
    derived_relations = list(
        Relation.objects.filter(
            predicate__in=_FORWARD_CROSS_SYSTEM_PREDICATES,
        )
        .select_related("subject_entity", "object_entity")
        .order_by(
            "subject_entity",
            "predicate",
            "object_entity",
        ),
    )

    def include_direct_endpoint(source_entity, target_entity) -> None:
        source_key = (source_entity.kind, source_entity.id)
        target_key = (target_entity.kind, target_entity.id)
        if source_key in internal_keys and target_key not in internal_keys:
            visible[target_key] = target_entity
        elif target_key in internal_keys and source_key not in internal_keys:
            visible[source_key] = source_entity

    for item in declared:
        include_direct_endpoint(item.source, item.target)
    for item in derived_relations:
        include_direct_endpoint(item.subject_entity, item.object_entity)

    explicit_edges: dict[tuple[str, str], dict[str, str]] = {}
    for item in declared:
        source_key = (item.source.kind, item.source.id)
        target_key = (item.target.kind, item.target.id)
        if (
            source_key not in visible
            or target_key not in visible
            or not ({source_key, target_key} & internal_keys)
        ):
            continue
        edge = relationship(
            source_kind=item.source.kind,
            source_id=item.source.id,
            target_kind=item.target.kind,
            target_id=item.target.id,
            label=item.label,
            technology=item.technology,
            tags=(_interaction_tag(item.interaction_kind),),
        )
        explicit_edges[_endpoint_key(edge)] = edge

    derived_edges: dict[tuple[str, str], dict[str, str]] = {}
    for item in derived_relations:
        source_key = (item.subject_entity.kind, item.subject_entity.id)
        target_key = (item.object_entity.kind, item.object_entity.id)
        if (
            source_key not in visible
            or target_key not in visible
            or not ({source_key, target_key} & internal_keys)
        ):
            continue
        edge = relationship(
            source_kind=item.subject_entity.kind,
            source_id=item.subject_entity.id,
            target_kind=item.object_entity.kind,
            target_id=item.object_entity.id,
            label="Uses",
            tags=(_DERIVED_RELATIONSHIP_TAG,),
        )
        derived_edges.setdefault(_endpoint_key(edge), edge)

    elements = [
        _component_element(
            item,
            selected=False,
            system=system,
            show_selected_label=settings.show_selected_label,
        )
        for item in visible.values()
    ]
    elements.sort(key=lambda value: value["alias"])
    return diagram_payload(
        diagram_type="ComponentDiagram",
        title=f"{_display_name(system)} — System Architecture",
        elements=elements,
        relationships=_merge_edges(explicit_edges, derived_edges),
        settings=settings,
    )


def _context_endpoint(entity):
    """Map a catalog entity to its System Context-level endpoint."""
    if entity is None:
        return None
    if entity.kind == KIND_SYSTEM or _is_actor_kind(entity.kind):
        return entity
    return entity.details.system


def _context_element(entity, *, selected: bool) -> dict[str, str]:
    if _is_actor_kind(entity.kind):
        element_type = "Person" if selected else "PersonExt"
    else:
        element_type = (
            "System" if selected or not is_external(entity.tags) else "SystemExt"
        )
    return element(
        type=element_type,
        kind=entity.kind,
        pk=entity.id,
        label=_display_name(entity),
        description=entity.description,
        tags=(
            _ELEMENT_TAGS["person"]
            if _is_actor_kind(entity.kind)
            else _ELEMENT_TAGS["selected_system"]
            if selected
            else _ELEMENT_TAGS["external_endpoint"]
            if is_external(entity.tags)
            else _ELEMENT_TAGS["endpoint"],
        ),
    )


def _component_element(
    entity,
    *,
    selected: bool,
    system,
    show_selected_label: bool = True,
) -> dict[str, str]:
    """Map catalog entities to their deterministic Component Diagram macro."""
    if _is_actor_kind(entity.kind):
        return element(
            type="Person" if selected else "PersonExt",
            kind=entity.kind,
            pk=entity.id,
            label=_display_name(entity),
            description=entity.description,
            tags=(_ELEMENT_TAGS["person"],),
        )
    details = entity.details
    external = is_external(entity.tags) or (
        hasattr(details, "system_id") and details.system_id != system.id
    )
    if entity.kind == KIND_RESOURCE:
        element_type = {
            "database": "ComponentDb",
            "queue": "ComponentQueue",
        }.get(
            details.type,
            "Component",
        )
    else:
        element_type = "Component"
    if external:
        element_type = {
            "Component": "ComponentExt",
            "ComponentDb": "ComponentDbExt",
            "ComponentQueue": "ComponentQueueExt",
        }[element_type]
    return element(
        type=element_type,
        kind=entity.kind,
        pk=entity.id,
        label=f"{_display_name(entity)} (selected)"
        if selected and show_selected_label
        else _display_name(entity),
        description=entity.description,
        technology=getattr(details, "type", ""),
        tags=(
            _component_element_tag(
                entity,
                selected=selected,
                external=external,
            ),
        ),
    )


def _display_name(entity) -> str:
    display_name = entity.details.display_name if entity.kind == KIND_ACTOR else ""
    return entity.title or display_name or entity.name


def _endpoint_key(value: Mapping[str, str]) -> tuple[str, str]:
    return (value["from"], value["to"])


def _interaction_tag(interaction_kind: str) -> str:
    """Return the fixed visual tag for a declared interaction kind."""
    return _INTERACTION_TAGS.get(interaction_kind, _INTERACTION_TAGS["manual"])


def _component_element_tag(entity, *, selected: bool, external: bool) -> str:
    """Return the fixed Atlas role tag without exposing catalog metadata."""
    if external:
        return _ELEMENT_TAGS["external_endpoint"]
    if selected:
        return _ELEMENT_TAGS["selected_component"]
    if entity.kind == KIND_RESOURCE:
        return {
            "database": _ELEMENT_TAGS["database"],
            "queue": _ELEMENT_TAGS["queue"],
        }.get(entity.details.type, _ELEMENT_TAGS["endpoint"])
    if entity.kind == KIND_COMPONENT:
        return _ELEMENT_TAGS["component"]
    return _ELEMENT_TAGS["endpoint"]


def _merge_edges(
    explicit: Mapping[tuple[str, str], dict[str, str]],
    derived: Mapping[tuple[str, str], dict[str, str]],
) -> list[dict[str, str]]:
    """Prefer declared edge metadata over a generic derived fallback."""
    merged = dict(derived)
    merged.update(explicit)
    return [merged[key] for key in sorted(merged)]


class _IdentifiedRemotePlantUMLBackend(RemotePlantUMLBackend):
    """`RemotePlantUMLBackend` that sends a descriptive `User-Agent`.

    The library calls `urllib` with its default `Python-urllib/3.x` agent,
    which the public PlantUML server (behind Cloudflare) rejects with
    `403 error code: 1010`, so every remote render would fail. Mirrors
    `RemotePlantUMLBackend.to_bytes` apart from the header.
    """

    USER_AGENT = "atlas-c4-renderer/0.1 (+https://github.com/sidorov-as/atlas)"

    def to_bytes(self, diagram: str, *, format: DiagramFormat) -> bytes:
        self._ensure_format_supported(format)
        encoded = self._encode_text_diagram(diagram).decode("utf-8")
        request = Request(
            f"{self._server_url}/{format}/{encoded}",
            headers={"User-Agent": self.USER_AGENT},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as resp:
                return resp.read()  # type: ignore[no-any-return]
        except HTTPError as exc:
            body = b""
            with suppress(Exception):
                body = exc.read() or b""
            preview = body[:200].decode("utf-8", errors="replace")
            raise PlantUMLRemoteRenderingError(
                f"PlantUML server render failed: HTTP {exc.code} {exc.reason}. "
                f"Body: {preview!r}"
            ) from exc
        except URLError as exc:
            raise PlantUMLRemoteRenderingError(
                f"PlantUML server render failed: {exc.reason!r}"
            ) from exc


def _plantuml_config() -> C4PluginConfig:
    """The resolved ``atlas.c4`` config, or the local-renderer defaults when
    the deployment declares none."""
    try:
        return get_plugin_config("atlas.c4", C4PluginConfig)
    except LookupError:
        return C4PluginConfig()


def _plantuml_backend(config: C4PluginConfig):
    if config.renderer == "remote":
        return _IdentifiedRemotePlantUMLBackend(
            server_url=config.server_url,
            timeout_seconds=config.timeout_seconds,
        )
    return LocalPlantUMLBackend(
        timeout_seconds=config.timeout_seconds,
        plantuml_args=["-DRELATIVE_INCLUDE=."],
    )


def render(payload: Mapping[str, Any], *, format: ImageFormat = "svg") -> bytes:
    """Render a validated diagram through the configured PlantUML backend."""
    try:
        diagram, _ = diagram_from_dict(payload)
        renderer = PlantUMLRenderer(backend=_plantuml_backend(_plantuml_config()))
        return renderer.render_bytes(diagram, format=DiagramFormat(format))
    except (
        ConversionError,
        DiagramJSONSchemaValidationError,
        PlantUMLError,
        OSError,
    ) as exc:
        # The API deliberately answers with a generic message; keep the cause
        # in the server log so a misconfigured renderer is diagnosable.
        logger.warning("Diagram rendering failed: %s: %s", type(exc).__name__, exc)
        raise DiagramRenderError("Unable to render diagram") from exc
