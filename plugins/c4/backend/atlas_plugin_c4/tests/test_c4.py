import pytest
from atlas_plugin_api import KIND_GROUP, get_architecture_relationship_model
from server.apps.catalog.tests.factories import (
    create_actor,
    create_api,
    create_component,
    create_resource,
    create_system,
)

from atlas_plugin_c4.c4 import (
    DEFAULT_DIAGRAM_RENDERING_SETTINGS,
    DiagramRenderingSettings,
    alias,
    build_component_diagram,
    build_system_architecture,
    build_system_context,
    build_system_landscape,
    diagram_payload,
    element,
    is_external,
    relationship,
    render_options_payload,
)

pytestmark = pytest.mark.django_db

ArchitectureRelationship = get_architecture_relationship_model()


def test_c4_payload_uses_stable_aliases_and_strict_json_shape():
    payload = diagram_payload(
        diagram_type="SystemContextDiagram",
        title="Atlas",
        elements=[element(type="System", kind="system", pk=1, label="Atlas")],
        relationships=[
            relationship(
                source_kind="system",
                source_id=1,
                target_kind="system",
                target_id=2,
                label="Uses",
                technology="HTTPS",
            )
        ],
    )

    assert alias("system", 1) == "system_1"
    assert payload["backend"] == "plantuml"
    assert payload["elements"][0]["alias"] == "system_1"
    assert payload["relationships"][0]["from"] == "system_1"
    assert payload["render_options"]["layout"] == "LAYOUT_TOP_DOWN"
    assert payload["render_options"]["show_legend"] == {}
    assert payload["render_options"]["legend_title"] == "Atlas C4 diagram semantics"
    assert {tag["tag_stereo"] for tag in payload["render_options"]["tags"]} == {
        "AtlasSelectedSystem",
        "AtlasSelectedComponent",
        "AtlasComponent",
        "AtlasDatabase",
        "AtlasQueue",
        "AtlasEndpoint",
        "AtlasExternalEndpoint",
        "AtlasPerson",
        "AtlasSynchronous",
        "AtlasAsynchronous",
        "AtlasDataAccess",
        "AtlasManual",
        "AtlasDerived",
    }
    element_tags = [
        tag for tag in payload["render_options"]["tags"] if tag["type"] == "ElementTag"
    ]
    assert all(tag["shape"] == "RoundedBoxShape" for tag in element_tags)
    assert all(tag["font_color"] and tag["border_style"] for tag in element_tags)
    relationship_tags = [
        tag for tag in payload["render_options"]["tags"] if tag["type"] == "RelTag"
    ]
    assert all(tag["line_color"] and tag["line_thickness"] for tag in relationship_tags)


def test_rendering_settings_map_to_constrained_plantuml_options():
    assert render_options_payload(DEFAULT_DIAGRAM_RENDERING_SETTINGS) == {
        "layout": "LAYOUT_TOP_DOWN",
        "show_legend": {},
        "legend_title": "Atlas C4 diagram semantics",
        "hide_stereotype": False,
        "hide_person_sprite": False,
    }

    assert render_options_payload(
        DiagramRenderingSettings(
            layout="LAYOUT_LEFT_RIGHT",
            show_legend=False,
            show_person_sprite=False,
            show_stereotypes=False,
        )
    ) == {
        "layout": "LAYOUT_LEFT_RIGHT",
        "hide_stereotype": True,
        "hide_person_sprite": True,
    }


def test_external_tag_is_case_insensitive():
    assert is_external(["external"])
    assert is_external(["External"])
    assert not is_external(["internal"])


def test_system_landscape_includes_all_systems_and_explicit_actors_only(group, system):
    other = create_system(name="payments", owner=group)
    actor = create_actor(name="customer", display_name="Customer")
    component = create_component(name="checkout", owner=group, system=other)
    ArchitectureRelationship.objects.create(
        source=actor, target=component, label="Uses"
    )

    payload = build_system_landscape()

    assert {item["alias"] for item in payload["elements"]} == {
        alias("system", system.id),
        alias("system", other.id),
        alias("user", actor.id),
    }
    assert payload["relationships"] == [
        relationship(
            source_kind="user",
            source_id=actor.id,
            target_kind="system",
            target_id=other.id,
            label="Uses",
            tags=("AtlasManual",),
        )
    ]


def test_system_landscape_prefers_declared_edges_and_orders_output(group, system):
    other = create_system(name="payments", owner=group)
    api = create_api(name="payments-api", owner=group, system=other)
    component = create_component(name="checkout", owner=group, system=system)
    component.component_details.consumes_apis.add(api)
    ArchitectureRelationship.objects.create(
        source=component,
        target=api,
        label="Calls",
        technology="HTTPS",
        interaction_kind="synchronous",
    )

    payload = build_system_landscape()

    assert [item["alias"] for item in payload["elements"]] == sorted(
        item["alias"] for item in payload["elements"]
    )
    assert payload["relationships"] == [
        relationship(
            source_kind="system",
            source_id=system.id,
            target_kind="system",
            target_id=other.id,
            label="Calls",
            technology="HTTPS",
            tags=("AtlasSynchronous",),
        )
    ]


def test_system_context_aggregates_cross_system_api_use(group, system):
    other_system = create_system(name="payments", owner=group, tags=["External"])
    api = create_api(name="payments-api", owner=group, system=other_system)
    component = create_component(name="checkout", owner=group, system=system)
    component.component_details.consumes_apis.add(api)

    payload = build_system_context(system)

    assert {item["alias"] for item in payload["elements"]} == {
        alias("system", system.id),
        alias("system", other_system.id),
    }
    other_system_element = next(
        item
        for item in payload["elements"]
        if item["alias"] == alias("system", other_system.id)
    )
    assert other_system_element["type"] == "SystemExt"
    assert payload["relationships"] == [
        relationship(
            source_kind="system",
            source_id=system.id,
            target_kind="system",
            target_id=other_system.id,
            label="Uses",
            tags=("AtlasDerived",),
        )
    ]


def test_system_context_includes_explicit_actors_but_not_owners(group, system):
    actor = create_actor(name="customer", display_name="Customer")
    ArchitectureRelationship.objects.create(
        source=actor,
        target=system,
        label="Uses",
        technology="Browser",
    )
    # The owning Group is not an actor unless it is named in a declared edge.
    assert group.kind == KIND_GROUP

    payload = build_system_context(system)

    assert {item["alias"] for item in payload["elements"]} == {
        alias("system", system.id),
        alias("user", actor.id),
    }
    actor_element = next(
        item for item in payload["elements"] if item["alias"] == alias("user", actor.id)
    )
    assert actor_element["type"] == "PersonExt"
    assert payload["relationships"] == [
        relationship(
            source_kind="user",
            source_id=actor.id,
            target_kind="system",
            target_id=system.id,
            label="Uses",
            technology="Browser",
            tags=("AtlasManual",),
        )
    ]


def test_component_diagram_includes_system_components_and_direct_resources(
    group,
    system,
    component,
):
    sibling = create_component(name="worker", type="worker", owner=group, system=system)
    database = create_resource(name="orders", owner=group, system=system)
    component.component_details.depends_on.add(database)

    payload = build_component_diagram(component)

    assert {item["alias"] for item in payload["elements"]} == {
        alias("component", component.id),
        alias("component", sibling.id),
        alias("resource", database.id),
    }
    assert (
        next(
            item
            for item in payload["elements"]
            if item["alias"] == alias("resource", database.id)
        )["type"]
        == "ComponentDb"
    )


def test_component_settings_hide_selected_label_without_hiding_selected_tag(
    component,
):
    payload = build_component_diagram(
        component,
        DiagramRenderingSettings(show_selected_label=False),
    )

    selected = next(
        item
        for item in payload["elements"]
        if item["alias"] == alias("component", component.id)
    )
    assert selected["label"] == component.name
    assert selected["tags"] == ["AtlasSelectedComponent"]


def test_component_diagram_renders_explicit_actor_as_person(group, system, component):
    actor = create_actor(name="guest", display_name="Guest")
    ArchitectureRelationship.objects.create(
        source=actor,
        target=component,
        label="Books via",
        interaction_kind="manual",
    )

    payload = build_component_diagram(component)

    actor_element = next(
        item for item in payload["elements"] if item["alias"] == alias("user", actor.id)
    )
    assert actor_element["type"] == "PersonExt"
    assert actor_element["tags"] == ["AtlasPerson"]


def test_system_architecture_renders_explicit_actor_as_person(group, system):
    component = create_component(name="checkout", owner=group, system=system)
    actor = create_actor(name="guest", display_name="Guest")
    ArchitectureRelationship.objects.create(
        source=actor,
        target=component,
        label="Books via",
        interaction_kind="manual",
    )

    payload = build_system_architecture(system)

    actor_element = next(
        item for item in payload["elements"] if item["alias"] == alias("user", actor.id)
    )
    assert actor_element["type"] == "PersonExt"
    assert actor_element["tags"] == ["AtlasPerson"]


def test_declared_system_edge_replaces_generic_derived_edge(group, system):
    other = create_system(name="other", owner=group)
    api = create_api(name="other-api", owner=group, system=other)
    component = create_component(name="caller", owner=group, system=system)
    component.component_details.consumes_apis.add(api)
    ArchitectureRelationship.objects.create(
        source=component,
        target=api,
        label="Calls",
        technology="HTTPS",
    )

    payload = build_system_context(system)

    assert payload["relationships"] == [
        relationship(
            source_kind="system",
            source_id=system.id,
            target_kind="system",
            target_id=other.id,
            label="Calls",
            technology="HTTPS",
            tags=("AtlasManual",),
        )
    ]


def test_system_architecture_scopes_internal_elements_and_external_edges(group, system):
    component = create_component(
        name="checkout",
        owner=group,
        system=system,
        tags=["untrusted-catalog-tag"],
    )
    worker = create_component(name="worker", type="worker", owner=group, system=system)
    api = create_api(name="booking-api", owner=group, system=system)
    database = create_resource(name="bookings", owner=group, system=system)
    queue = create_resource(
        name="booking-events", type="queue", owner=group, system=system
    )
    external_system = create_system(name="payments", owner=group)
    external_api = create_api(name="payments-api", owner=group, system=external_system)
    component.component_details.consumes_apis.add(external_api)
    for target, label, interaction_kind in (
        (api, "Submit booking", "synchronous"),
        (database, "Store booking", "data-access"),
        (worker, "Review booking", "manual"),
        (external_api, "Charge payment", "asynchronous"),
    ):
        ArchitectureRelationship.objects.create(
            source=component,
            target=target,
            label=label,
            interaction_kind=interaction_kind,
        )

    payload = build_system_architecture(system)

    assert {item["alias"] for item in payload["elements"]} == {
        alias("component", component.id),
        alias("component", worker.id),
        alias("api", api.id),
        alias("resource", database.id),
        alias("resource", queue.id),
        alias("api", external_api.id),
    }
    tags_by_alias = {item["alias"]: item["tags"] for item in payload["elements"]}
    assert tags_by_alias[alias("component", component.id)] == ["AtlasComponent"]
    assert (
        "untrusted-catalog-tag" not in tags_by_alias[alias("component", component.id)]
    )
    assert tags_by_alias[alias("api", api.id)] == ["AtlasEndpoint"]
    assert tags_by_alias[alias("resource", database.id)] == ["AtlasDatabase"]
    assert tags_by_alias[alias("resource", queue.id)] == ["AtlasQueue"]
    assert tags_by_alias[alias("api", external_api.id)] == ["AtlasExternalEndpoint"]

    assert {edge["tags"][0] for edge in payload["relationships"]} == {
        "AtlasSynchronous",
        "AtlasDataAccess",
        "AtlasManual",
        "AtlasAsynchronous",
    }
    payment_edge = next(
        edge
        for edge in payload["relationships"]
        if edge["to"] == alias("api", external_api.id)
    )
    assert payment_edge["label"] == "Charge payment"
    assert payment_edge["tags"] == ["AtlasAsynchronous"]
