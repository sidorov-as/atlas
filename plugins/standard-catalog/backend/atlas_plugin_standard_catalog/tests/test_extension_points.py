"""Tests for `add_consumed_api`: a repeated/idempotent call — standing in for two
near-simultaneous links from the same Service to different Endpoints of the
same API racing on the M2M `.add()` — must not create a duplicate
`consumesAPI` relation or raise.
"""

import pytest
from atlas_plugin_api import entity_relations
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_system,
)

from atlas_plugin_standard_catalog.extension_points import add_consumed_api

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="billing-api", owner=group, system=system)


@pytest.fixture
def component(group, system):
    return create_component(name="billing-service", owner=group, system=system)


def _consumed_api_ids(component):
    consumes_apis = component.component_details.consumes_apis
    return list(consumes_apis.values_list("pk", flat=True))


def test_add_consumed_api_creates_the_relation_on_first_call(component, api):
    created = add_consumed_api(component, api)

    assert created is True
    assert _consumed_api_ids(component) == [api.pk]
    forward = ("consumesAPI", api.ref, api.kind, api.id)
    reverse = ("apiConsumedBy", component.ref, component.kind, component.id)
    assert forward in entity_relations(component)
    assert reverse in entity_relations(api)


def test_add_consumed_api_is_idempotent_on_repeated_calls(component, api):
    first = add_consumed_api(component, api)
    second = add_consumed_api(component, api)
    third = add_consumed_api(component, api)

    assert (first, second, third) == (True, False, False)
    assert _consumed_api_ids(component) == [api.pk]
    relation = ("consumesAPI", api.ref, api.kind, api.id)
    assert entity_relations(component).count(relation) == 1


def test_add_consumed_api_returns_false_when_already_present_via_another_path(
    component,
    api,
):
    component.component_details.consumes_apis.add(api)

    created = add_consumed_api(component, api)

    assert created is False
    assert _consumed_api_ids(component) == [api.pk]
