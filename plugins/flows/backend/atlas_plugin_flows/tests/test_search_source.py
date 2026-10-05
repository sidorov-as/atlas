"""Flows as searchable documents (`search-flow-source` spec)."""

import pytest
from atlas_plugin_api import STATUS_REMOVED, get_catalog_entity_model
from server.apps.catalog.tests.factories import create_system

from atlas_plugin_flows.models import Flow
from atlas_plugin_flows.search_source import flatten_step_text, flow_search_source

pytestmark = pytest.mark.django_db


# --- step text flattening ------------------------------------------------


def test_flatten_includes_title_summary_and_external_label():
    steps = [
        {"id": "a", "title": "Place order", "summary": "Customer checks out"},
        {"id": "b", "external_label": "Payment provider"},
    ]

    assert flatten_step_text(steps) == (
        "Place order\nCustomer checks out\nPayment provider"
    )


def test_flatten_ignores_keys_that_are_not_visible_text():
    steps = [{"id": "a", "link_url": "https://example.com", "entity_ref": "x:y"}]

    assert flatten_step_text(steps) == ""


@pytest.mark.parametrize(
    "steps",
    [
        [],
        None,
        "not a list",
        {"id": "a", "title": "dict, not list"},
        [None, 3, "text", ["nested"]],
        [{"id": "a", "title": None, "summary": 7, "external_label": "   "}],
        [{}],
    ],
)
def test_flatten_tolerates_empty_and_malformed_steps(steps):
    assert flatten_step_text(steps) == ""


def test_flatten_keeps_valid_text_next_to_malformed_steps():
    steps = [None, {"id": "a", "title": "Kept", "summary": 7}, "junk"]

    assert flatten_step_text(steps) == "Kept"


# --- documents -------------------------------------------------------------


@pytest.fixture
def flow(system):
    return Flow.objects.create(
        system=system,
        name="checkout-saga",
        description="Place order and ship",
        documentation="Refunds follow the zebracorn policy",
        steps=[
            {"id": "a", "title": "Reserve stock", "next_step": {"id": "b"}},
            {"id": "b", "external_label": "Quokkaforge gateway"},
        ],
    )


def test_document_maps_flow_fields(flow):
    [document] = flow_search_source.documents([f"flow:{flow.pk}"])

    assert document.id == f"flow:{flow.pk}"
    assert document.kind == "flow"
    assert document.title == "checkout-saga"
    assert document.summary == "Place order and ship"
    for text in (
        "Place order and ship",
        "zebracorn",
        "Reserve stock",
        "Quokkaforge gateway",
    ):
        assert text in document.body


def test_flow_without_steps_is_indexed_from_its_own_fields(system):
    flow = Flow.objects.create(
        system=system, name="bare", description="Just text", steps=[]
    )

    [document] = flow_search_source.documents([f"flow:{flow.pk}"])

    assert document.title == "bare"
    assert document.body == "Just text"


def test_all_documents_streams_every_flow(flow):
    assert [d.id for d in flow_search_source.all_documents()] == [f"flow:{flow.pk}"]


def test_unknown_ids_are_omitted():
    assert (
        list(flow_search_source.documents(["flow:999999", "system:abc", "flow:x"]))
        == []
    )


def test_changed_flow_maps_to_its_document(flow):
    assert list(flow_search_source.document_ids_for_instance(flow)) == [
        f"flow:{flow.pk}"
    ]


def test_changed_system_maps_to_its_flows(flow, system, group):
    other = create_system(name="other", owner=group)
    Flow.objects.create(system=other, name="elsewhere")

    assert list(flow_search_source.document_ids_for_instance(system)) == [
        f"flow:{flow.pk}"
    ]


def test_non_system_entity_maps_to_nothing(component):
    assert list(flow_search_source.document_ids_for_instance(component)) == []


def test_watches_flows_and_catalog_entities():
    assert set(flow_search_source.watched_models) == {
        "catalog.Flow",
        "catalog.CatalogEntity",
    }


# --- resolve ---------------------------------------------------------------


def test_resolve_returns_a_link_to_the_whole_flow(flow, owner_user):
    [hit] = flow_search_source.resolve(
        [f"flow:{flow.pk}"], owner_user.actor_details.account
    )

    assert hit.link == f"/flows/{flow.pk}"
    assert hit.title == "checkout-saga — user-management"
    assert "Quokkaforge gateway" in hit.text


def test_resolve_omits_flows_for_anonymous_actors(flow):
    from django.contrib.auth.models import AnonymousUser

    assert flow_search_source.resolve([f"flow:{flow.pk}"], AnonymousUser()) == []


def test_resolve_omits_flows_of_a_removed_system(flow, system, owner_user):
    get_catalog_entity_model().objects.filter(pk=system.pk).update(
        status=STATUS_REMOVED
    )

    assert (
        flow_search_source.resolve(
            [f"flow:{flow.pk}"], owner_user.actor_details.account
        )
        == []
    )


def test_resolve_omits_deleted_flows(flow, owner_user):
    flow_id = f"flow:{flow.pk}"
    flow.delete()

    assert flow_search_source.resolve([flow_id], owner_user.actor_details.account) == []
