"""Custom view builder: a C4 diagram over a user-chosen slice of the catalog.

The level graph (Systems, or Components/Resources/APIs) is built in memory from
the same sources as the other builders: declared Architecture Relationships and
the ``consumesAPI``/``providesAPI``/``dependsOn`` derived relations, with a
declared edge superseding a derived one with the same directed endpoints. A
selection mode then narrows it to the visible nodes. Removed entities never
appear. Actors (kinds declaring ``architecture.actor.v1``) appear only through
declared relationships.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from atlas_plugin_api import (
    ARCHITECTURE_ACTOR_V1,
    KIND_API,
    KIND_CHOICES,
    KIND_COMPONENT,
    KIND_RESOURCE,
    KIND_SYSTEM,
    STATUS_ACTIVE,
    get_architecture_relationship_model,
    get_catalog_entity_model,
    get_relation_model,
    registry,
)

from . import c4
from .errors import (
    incompatible_entity,
    mixed_level_selection,
    node_limit_exceeded,
    unknown_entity,
)

Level = Literal["systems", "components"]
Selection = Literal["selected", "neighborhood"]
Direction = Literal["both", "outgoing", "incoming"]
RelationshipSource = Literal["declared", "declared_and_derived"]

ACTOR = "actor"
_COMPONENT_LEVEL_KINDS = frozenset({KIND_COMPONENT, KIND_RESOURCE, KIND_API})
_NODE_TYPES: dict[Level, frozenset[str]] = {
    "systems": frozenset({KIND_SYSTEM, ACTOR}),
    "components": frozenset(_COMPONENT_LEVEL_KINDS | {ACTOR}),
}


@dataclass(frozen=True)
class CustomViewRequest:
    """A validated custom view request.

    ``depth`` is ``None`` for unlimited. ``entity_types`` names the enabled
    optional types (``component``, ``resource``, ``api``, ``actor``); ``None``
    means every type available at the level, an empty set none of them. Systems are always enabled.
    """

    level: Level
    selection: Selection
    entities: tuple[UUID, ...]
    depth: int | None = 1
    direction: Direction = "both"
    entity_types: frozenset[str] | None = None
    relationships: RelationshipSource = "declared"


@dataclass(frozen=True)
class _Edge:
    source: Any
    target: Any
    label: str
    technology: str
    tag: str
    derived: bool


@dataclass
class _LevelGraph:
    nodes: dict[UUID, Any] = field(default_factory=dict)
    edges: dict[tuple[UUID, UUID], _Edge] = field(default_factory=dict)


def actor_kind_ids() -> list[str]:
    """Registered kinds that declare the actor capability, sorted."""
    return registry.kind_ids_with_capability(ARCHITECTURE_ACTOR_V1)


def actor_kinds() -> list[dict[str, str]]:
    """Actor-capable kinds with display labels, for the entity picker."""
    labels = dict(KIND_CHOICES)
    return [
        {
            "kind": kind_id,
            "label": str(labels.get(kind_id) or kind_id.replace("-", " ").title()),
        }
        for kind_id in actor_kind_ids()
    ]


def _node_type(entity) -> str | None:
    if c4._is_actor_kind(entity.kind):
        return ACTOR
    if entity.kind == KIND_SYSTEM or entity.kind in _COMPONENT_LEVEL_KINDS:
        return entity.kind
    return None


def missing_entity_ids(entities: Iterable[UUID]) -> list[UUID]:
    """The given ids that do not resolve to an active catalog entity, in input order."""
    entities = list(entities)
    existing = set(
        get_catalog_entity_model()
        .objects.filter(pk__in=entities, status=STATUS_ACTIVE)
        .values_list("pk", flat=True)
    )
    return [pk for pk in entities if pk not in existing]


def resolve_selection(request: CustomViewRequest) -> list[Any]:
    """Load the requested entities, in request order.

    Rejects unknown or removed entities, selections mixing Systems with
    Components/Resources/APIs, and entities not selectable at the level; each
    error names the offending entity.
    """
    found = {
        entity.id: entity
        for entity in get_catalog_entity_model().objects.filter(
            pk__in=request.entities, status=STATUS_ACTIVE
        )
    }
    for pk in request.entities:
        if pk not in found:
            raise unknown_entity(pk)
    entities = [found[pk] for pk in request.entities]
    types = {pk: _node_type(found[pk]) for pk in request.entities}
    systems = [pk for pk, kind in types.items() if kind == KIND_SYSTEM]
    components = [pk for pk, kind in types.items() if kind in _COMPONENT_LEVEL_KINDS]
    if systems and components:
        raise mixed_level_selection(
            "Systems cannot be combined with Components, Resources, or APIs",
            systems + components,
        )
    for pk in request.entities:
        if types[pk] not in _NODE_TYPES[request.level]:
            raise incompatible_entity(pk, request.level)
    return entities


def _level_graph(request: CustomViewRequest) -> _LevelGraph:
    ArchitectureRelationship = get_architecture_relationship_model()
    Relation = get_relation_model()
    cache: dict[UUID, Any] = {}

    def node_for(entity):
        if entity.id in cache:
            return cache[entity.id]
        node = None
        if entity.status == STATUS_ACTIVE:
            if c4._is_actor_kind(entity.kind):
                node = entity
            elif request.level == "systems":
                if entity.kind == KIND_SYSTEM:
                    node = entity
                elif entity.kind in _COMPONENT_LEVEL_KINDS:
                    node = entity.details.system
            elif entity.kind in _COMPONENT_LEVEL_KINDS:
                node = entity
        if node is not None and node.status != STATUS_ACTIVE:
            node = None
        cache[entity.id] = node
        return node

    graph = _LevelGraph()
    declared: dict[tuple[UUID, UUID], _Edge] = {}
    for item in ArchitectureRelationship.objects.select_related(
        "source", "target"
    ).order_by("pk"):
        source, target = node_for(item.source), node_for(item.target)
        if source is None or target is None or source.id == target.id:
            continue
        declared[source.id, target.id] = _Edge(
            source,
            target,
            item.label,
            item.technology,
            c4._interaction_tag(item.interaction_kind),
            derived=False,
        )

    derived: dict[tuple[UUID, UUID], _Edge] = {}
    if request.relationships == "declared_and_derived":
        for item in (
            Relation.objects.filter(predicate__in=c4._FORWARD_CROSS_SYSTEM_PREDICATES)
            .select_related("subject_entity", "object_entity")
            .order_by("subject_entity", "predicate", "object_entity")
        ):
            source, target = node_for(item.subject_entity), node_for(item.object_entity)
            if source is None or target is None or source.id == target.id:
                continue
            if _node_type(source) == ACTOR or _node_type(target) == ACTOR:
                continue
            derived.setdefault(
                (source.id, target.id),
                _Edge(
                    source,
                    target,
                    "Uses",
                    "",
                    c4._DERIVED_RELATIONSHIP_TAG,
                    derived=True,
                ),
            )

    graph.edges = {**derived, **declared}
    for edge in graph.edges.values():
        graph.nodes[edge.source.id] = edge.source
        graph.nodes[edge.target.id] = edge.target
    return graph


def _enabled_types(request: CustomViewRequest) -> frozenset[str]:
    available = _NODE_TYPES[request.level]
    if request.entity_types is None:
        return available
    return (frozenset(request.entity_types) & available) | {KIND_SYSTEM}


def _neighborhood(
    request: CustomViewRequest, graph: _LevelGraph, roots: list[Any]
) -> set[UUID]:
    outgoing: dict[UUID, set[UUID]] = defaultdict(set)
    incoming: dict[UUID, set[UUID]] = defaultdict(set)
    for source_id, target_id in graph.edges:
        outgoing[source_id].add(target_id)
        incoming[target_id].add(source_id)

    def neighbors(pk: UUID) -> Iterable[UUID]:
        if request.direction == "outgoing":
            return outgoing[pk]
        if request.direction == "incoming":
            return incoming[pk]
        return outgoing[pk] | incoming[pk]

    enabled = _enabled_types(request)
    root_ids = {root.id for root in roots}
    reached = set(root_ids)
    frontier = [root.id for root in roots]
    hops = 0
    while frontier and (request.depth is None or hops < request.depth):
        next_frontier: list[UUID] = []
        for pk in frontier:
            for neighbor_id in sorted(neighbors(pk)):
                if neighbor_id in reached:
                    continue
                node_type = _node_type(graph.nodes[neighbor_id])
                if node_type not in enabled:
                    continue
                reached.add(neighbor_id)
                # Actors are leaves: shown, never traversed through.
                if node_type != ACTOR:
                    next_frontier.append(neighbor_id)
        frontier = next_frontier
        hops += 1
    return reached


def select_view(request: CustomViewRequest) -> tuple[list[Any], list[_Edge]]:
    """Resolve the visible nodes and edges for ``request`` (no limit applied)."""
    roots = resolve_selection(request)
    graph = _level_graph(request)
    for root in roots:
        graph.nodes.setdefault(root.id, root)
    if request.selection == "selected":
        visible_ids = {root.id for root in roots}
    else:
        visible_ids = _neighborhood(request, graph, roots)
    nodes = sorted(
        (graph.nodes[pk] for pk in visible_ids),
        key=lambda node: c4.alias(node.kind, node.id),
    )
    edges = [
        edge
        for (source_id, target_id), edge in graph.edges.items()
        if source_id in visible_ids and target_id in visible_ids
    ]
    return nodes, edges


def build_custom_view(
    request: CustomViewRequest,
    settings: c4.DiagramRenderingSettings = c4.DEFAULT_DIAGRAM_RENDERING_SETTINGS,
) -> dict[str, Any]:
    """Build the custom view payload, or raise ``CustomViewError``.

    The node limit is checked here, before any PlantUML work. Boundary frames
    do not count towards it.
    """
    nodes, edges = select_view(request)
    limit = c4.plugin_config().max_nodes
    if len(nodes) > limit:
        raise node_limit_exceeded(limit=limit, count=len(nodes))

    relationships = sorted(
        (
            c4.relationship(
                source_kind=edge.source.kind,
                source_id=edge.source.id,
                target_kind=edge.target.kind,
                target_id=edge.target.id,
                label=edge.label,
                technology=edge.technology,
                tags=(edge.tag,),
            )
            for edge in edges
        ),
        key=c4._endpoint_key,
    )
    if request.level == "systems":
        elements = [c4._context_element(node, selected=False) for node in nodes]
        elements.sort(key=lambda value: value["alias"])
        return c4.diagram_payload(
            diagram_type="SystemContextDiagram",
            title="Atlas — Custom View (Systems)",
            elements=elements,
            relationships=relationships,
            settings=settings,
        )

    top_level: list[dict[str, str]] = []
    by_system: dict[UUID, tuple[Any, list[dict[str, str]]]] = {}
    for node in nodes:
        value = c4._component_element(
            node,
            selected=False,
            system=None,
            show_selected_label=settings.show_selected_label,
        )
        system = None if _node_type(node) == ACTOR else node.details.system
        if system is None:
            top_level.append(value)
        else:
            by_system.setdefault(system.id, (system, []))[1].append(value)
    boundaries = [
        {
            "type": "SystemBoundary",
            "alias": c4.alias("boundary", system.id),
            "label": c4._display_name(system),
            "elements": sorted(members, key=lambda value: value["alias"]),
        }
        for system, members in sorted(
            by_system.values(), key=lambda pair: c4.alias("boundary", pair[0].id)
        )
    ]
    top_level.sort(key=lambda value: value["alias"])
    return c4.diagram_payload(
        diagram_type="ComponentDiagram",
        title="Atlas — Custom View (Components)",
        elements=top_level,
        relationships=relationships,
        settings=settings,
        boundaries=boundaries,
    )
