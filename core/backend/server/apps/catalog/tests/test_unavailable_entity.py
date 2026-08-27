"""Unavailable Entity verification.

Simulates deselecting `atlas.apis` by building an `EntityKindRegistry` with
every real handler except `api`'s — the same "one plugin's handler is gone,
every other plugin's is untouched" shape a real disable/removal produces —
rather than exercising the plugin-selection/manifest machinery itself, which
is exercised separately.
"""

import pytest

from server.apps.catalog.kinds.registry import EntityKindRegistry
from server.apps.catalog.kinds.registry import registry as default_registry
from server.apps.catalog.models import KIND_API
from server.apps.catalog.relations import entity_relations
from server.apps.catalog.services.entity_service import EntityService
from server.apps.catalog.tests.factories import create_component

pytestmark = pytest.mark.django_db


def _registry_without(kind_id: str) -> EntityKindRegistry:
    registry = EntityKindRegistry()
    for registered_id in default_registry.registered_ids():
        if registered_id == kind_id:
            continue
        registry.register(default_registry.resolve(registered_id))
    return registry


def test_deselecting_apis_leaves_api_entities_unavailable_with_relations_intact(
    group,
    system,
    api,
):
    consumer = create_component(
        name="consumer-service",
        owner=group,
        system=system,
        consumes_apis=[api],
    )

    service = EntityService(registry=_registry_without(KIND_API))
    read = service.get(api.id)

    assert read.unavailable is True
    assert read.spec is None
    assert read.entity.id == api.id
    assert read.entity.name == api.name

    api_relations = entity_relations(api)
    assert (
        "apiConsumedBy",
        consumer.ref,
        consumer.kind,
        consumer.id,
    ) in api_relations

    consumer_relations = entity_relations(consumer)
    assert ("consumesAPI", api.ref, api.kind, api.id) in consumer_relations


def test_reselecting_apis_restores_full_data(api):
    unavailable_read = EntityService(registry=_registry_without(KIND_API)).get(
        api.id
    )
    assert unavailable_read.unavailable is True
    assert unavailable_read.spec is None

    restored_read = EntityService().get(api.id)

    assert restored_read.unavailable is False
    assert restored_read.spec is not None
    assert restored_read.spec.type == api.api_details.type
    assert restored_read.spec.system == api.api_details.system.ref
