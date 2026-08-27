"""Derived relation tests.

Covers derivation for all six spec-reference pairs, one API both provided
and consumed by different Components, both-direction listing via the
relations endpoint, and targeted recompute on write.
"""

import pytest

from server.apps.catalog.relations import entity_relations
from server.apps.catalog.tests.factories import (
    create_component,
    create_resource,
)

pytestmark = pytest.mark.django_db


def test_owner_produces_owned_by_and_owner_of(owner_client, group, system):
    assert ("ownedBy", "group:platform", "group", group.id) in entity_relations(
        system
    )
    assert (
        "ownerOf",
        "system:user-management",
        "system",
        system.id,
    ) in entity_relations(group)

    response = owner_client.get(f"/api/systems/{system.id}/relations/")
    assert response.status_code == 200
    assert {
        "predicate": "ownedBy",
        "target": "group:platform",
        "targetKind": "group",
        "targetId": str(group.id),
        "status": "active",
        "deprecated": False,
    } in response.json()

    group_response = owner_client.get(f"/api/groups/{group.id}/relations/")
    assert {
        "predicate": "ownerOf",
        "target": "system:user-management",
        "targetKind": "system",
        "targetId": str(system.id),
        "status": "active",
        "deprecated": False,
    } in group_response.json()


def test_system_produces_part_of_and_has_part(
    group, system, component, resource, api
):
    resource.resource_details.system = system
    resource.resource_details.save()

    assert (
        "partOf",
        "system:user-management",
        "system",
        system.id,
    ) in entity_relations(component)
    assert (
        "partOf",
        "system:user-management",
        "system",
        system.id,
    ) in entity_relations(resource)
    assert (
        "partOf",
        "system:user-management",
        "system",
        system.id,
    ) in entity_relations(api)

    system_relations = entity_relations(system)
    assert (
        "hasPart",
        component.ref,
        "component",
        component.id,
    ) in system_relations
    assert (
        "hasPart",
        resource.ref,
        "resource",
        resource.id,
    ) in system_relations
    assert ("hasPart", api.ref, "api", api.id) in system_relations


def test_depends_on_produces_reverse_dependency_of(
    owner_client, component, resource
):
    component.component_details.depends_on.set([resource])

    resource_response = owner_client.get(
        f"/api/resources/{resource.id}/relations/"
    )
    assert {
        "predicate": "dependencyOf",
        "target": component.ref,
        "targetKind": "component",
        "targetId": str(component.id),
        "status": "active",
        "deprecated": False,
    } in resource_response.json()

    component_response = owner_client.get(
        f"/api/components/{component.id}/relations/"
    )
    assert {
        "predicate": "dependsOn",
        "target": resource.ref,
        "targetKind": "resource",
        "targetId": str(resource.id),
        "status": "active",
        "deprecated": False,
    } in component_response.json()


def test_provides_and_consumes_apis_produce_reverse_relations(
    group, system, api
):
    provider = create_component(
        name="provider-service", owner=group, system=system
    )
    consumer = create_component(
        name="consumer-service", owner=group, system=system
    )
    provider.component_details.provides_apis.set([api])
    consumer.component_details.consumes_apis.set([api])

    api_relations = entity_relations(api)
    assert (
        "apiProvidedBy",
        provider.ref,
        "component",
        provider.id,
    ) in api_relations
    assert (
        "apiConsumedBy",
        consumer.ref,
        "component",
        consumer.id,
    ) in api_relations


def test_one_api_both_provided_and_consumed_by_different_components(
    group, system, api
):
    component_a = create_component(
        name="component-a", owner=group, system=system
    )
    component_b = create_component(
        name="component-b", owner=group, system=system
    )
    component_a.component_details.provides_apis.set([api])
    component_b.component_details.consumes_apis.set([api])

    api_relations = entity_relations(api)
    assert (
        "apiProvidedBy",
        component_a.ref,
        "component",
        component_a.id,
    ) in api_relations
    assert (
        "apiConsumedBy",
        component_b.ref,
        "component",
        component_b.id,
    ) in api_relations


def test_relations_endpoint_surfaces_removed_target_status(
    owner_client, component, resource
):
    component.component_details.depends_on.set([resource])
    resource.status = "removed"
    resource.save(update_fields=["status"])

    response = owner_client.get(f"/api/components/{component.id}/relations/")

    assert response.status_code == 200
    [entry] = [
        row for row in response.json() if row["predicate"] == "dependsOn"
    ]
    assert entry["status"] == "removed"
    assert entry["deprecated"] is False


def test_relations_endpoint_surfaces_deprecated_target_flag(
    owner_client, component, system
):
    component.component_details.lifecycle = "deprecated"
    component.component_details.save(update_fields=["lifecycle"])

    response = owner_client.get(f"/api/systems/{system.id}/relations/")

    assert response.status_code == 200
    [has_part] = [
        row for row in response.json() if row["targetId"] == str(component.id)
    ]
    assert has_part["predicate"] == "hasPart"
    assert has_part["deprecated"] is True
    assert has_part["status"] == "active"


def test_member_of_has_member_is_a_single_relationship(group, other_user):
    group.group_details.members.add(other_user)

    assert (
        "hasMember",
        other_user.ref,
        "user",
        other_user.id,
    ) in entity_relations(group)
    assert ("memberOf", group.ref, "group", group.id) in entity_relations(
        other_user
    )


def test_editing_depends_on_updates_only_that_components_edges(group, system):
    resource_a = create_resource(name="resource-a", owner=group)
    resource_b = create_resource(name="resource-b", owner=group)
    component_x = create_component(
        name="component-x", owner=group, system=system
    )
    component_y = create_component(
        name="component-y", owner=group, system=system
    )
    component_x.component_details.depends_on.set([resource_a])
    component_y.component_details.depends_on.set([resource_a])

    component_x.component_details.depends_on.set([resource_b])

    assert (
        "dependsOn",
        resource_b.ref,
        "resource",
        resource_b.id,
    ) in entity_relations(component_x)
    assert (
        "dependsOn",
        resource_a.ref,
        "resource",
        resource_a.id,
    ) not in entity_relations(component_x)
    # component_y's own edges are untouched by component_x's write.
    assert (
        "dependsOn",
        resource_a.ref,
        "resource",
        resource_a.id,
    ) in entity_relations(component_y)
    # resource_a still shows component_y as a dependent, but no longer
    # component_x.
    resource_a_relations = entity_relations(resource_a)
    assert (
        "dependencyOf",
        component_y.ref,
        "component",
        component_y.id,
    ) in resource_a_relations
    assert (
        "dependencyOf",
        component_x.ref,
        "component",
        component_x.id,
    ) not in resource_a_relations
