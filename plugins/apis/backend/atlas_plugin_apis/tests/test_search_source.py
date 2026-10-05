"""API endpoints and operations as searchable documents (`search-api-source` spec)."""

import pytest
from atlas_plugin_api import STATUS_REMOVED, get_catalog_entity_model
from django.db.models.signals import post_save
from server.apps.catalog.tests.factories import create_api, create_system

from atlas_plugin_apis import asyncapi_import, openapi_import
from atlas_plugin_apis.models import ApiDetails, ApiEndpoint, ApiOperation
from atlas_plugin_apis.plugin import ENDPOINT_READ_PERMISSION, OPERATION_READ_PERMISSION
from atlas_plugin_apis.search_source import api_search_source

pytestmark = pytest.mark.django_db


@pytest.fixture
def api(group):
    system = create_system(name="booking", owner=group)
    return create_api(
        name="orders-api",
        title="Orders API",
        owner=group,
        system=system,
    )


@pytest.fixture
def endpoint(api):
    return ApiEndpoint.objects.create(
        api=api,
        method="GET",
        path="/zebracorn/{id}",
        operation_id="getZebracorn",
        summary="Fetch a zebracorn",
        description="Long prose that is not indexed: pangolinwhisper",
    )


@pytest.fixture
def operation(api):
    return ApiOperation.objects.create(
        api=api,
        channel_address="orders.quokkaforge.created",
        direction="send",
        operation_key="sendOrderCreated",
        operation_id="sendOrderCreated",
        summary="Announce a new order",
    )


@pytest.fixture
def actor(owner_user):
    return owner_user.actor_details.account


# --- documents ---------------------------------------------------------------


def test_endpoint_document_has_method_and_path_title_and_summary_and_id_body(endpoint):
    [document] = api_search_source.documents([f"endpoint:{endpoint.pk}"])

    assert document.id == f"endpoint:{endpoint.pk}"
    assert document.kind == "endpoint"
    assert document.title == "GET /zebracorn/{id}"
    assert "Fetch a zebracorn" in document.body
    assert "getZebracorn" in document.body
    assert "zebracorn id" in document.body
    assert "pangolinwhisper" not in document.body


def test_operation_document_has_direction_and_channel_title(operation):
    [document] = api_search_source.documents([f"operation:{operation.pk}"])

    assert document.id == f"operation:{operation.pk}"
    assert document.kind == "operation"
    assert document.title == "send orders.quokkaforge.created"
    assert "Announce a new order" in document.body
    assert "sendOrderCreated" in document.body
    assert "orders quokkaforge created" in document.body


@pytest.mark.parametrize(
    ("address", "words"),
    [("/pets/{petId}", "pets petId"), ("orders.created_v2", "orders created v2")],
)
def test_address_is_split_into_words_for_the_body(api, address, words):
    endpoint = ApiEndpoint.objects.create(api=api, method="GET", path=address)

    [document] = api_search_source.documents([f"endpoint:{endpoint.pk}"])

    assert document.body == words
    assert document.title == f"GET {address}"


def test_all_documents_streams_endpoints_and_operations(endpoint, operation):
    ids = {d.id for d in api_search_source.all_documents()}

    assert ids == {f"endpoint:{endpoint.pk}", f"operation:{operation.pk}"}


def test_ids_of_the_wrong_kind_or_unknown_are_omitted(endpoint):
    ids = [f"operation:{endpoint.pk}", "endpoint:not-a-uuid", "note:1", "endpoint"]

    assert list(api_search_source.documents(ids)) == []


def test_removed_rows_have_no_document_and_restored_rows_do(endpoint, operation):
    ids = [f"endpoint:{endpoint.pk}", f"operation:{operation.pk}"]
    ApiEndpoint.objects.filter(pk=endpoint.pk).update(status="removed")
    ApiOperation.objects.filter(pk=operation.pk).update(status="removed")

    assert list(api_search_source.documents(ids)) == []
    assert list(api_search_source.all_documents()) == []

    ApiEndpoint.objects.filter(pk=endpoint.pk).update(status="active")
    ApiOperation.objects.filter(pk=operation.pk).update(status="active")

    assert {d.id for d in api_search_source.documents(ids)} == set(ids)


def test_raw_specification_is_not_indexed(api, endpoint):
    ApiDetails.objects.filter(entity=api).update(
        spec_content="openapi: 3.0.0 # rawspectoken"
    )

    assert "rawspectoken" not in " ".join(
        d.body + d.title for d in api_search_source.all_documents()
    )
    assert ApiDetails._meta.label not in api_search_source.watched_models


def test_maps_changed_rows_to_their_documents(endpoint, operation, api):
    assert list(api_search_source.document_ids_for_instance(endpoint)) == [
        f"endpoint:{endpoint.pk}"
    ]
    assert list(api_search_source.document_ids_for_instance(operation)) == [
        f"operation:{operation.pk}"
    ]
    assert list(api_search_source.document_ids_for_instance(api)) == []


def test_watches_endpoints_and_operations():
    assert set(api_search_source.watched_models) == {
        "apis_plugin.ApiEndpoint",
        "apis_plugin.ApiOperation",
    }


# --- stale removal must reach the index ---------------------------------------


def _saved_during(call):
    saved = []

    def receiver(sender, instance, **kwargs):
        saved.append(instance)

    post_save.connect(receiver, weak=False)
    try:
        call()
    finally:
        post_save.disconnect(receiver)
    return saved


def test_openapi_stale_removal_sends_post_save(api, endpoint):
    saved = _saved_during(lambda: openapi_import._upsert_operations(api, []))

    assert endpoint.pk in {row.pk for row in saved if isinstance(row, ApiEndpoint)}
    endpoint.refresh_from_db()
    assert endpoint.status == ApiEndpoint.STATUS_REMOVED


def test_asyncapi_stale_removal_sends_post_save(api, operation):
    saved = _saved_during(lambda: asyncapi_import._upsert_operations(api, []))

    assert operation.pk in {row.pk for row in saved if isinstance(row, ApiOperation)}
    operation.refresh_from_db()
    assert operation.status == ApiOperation.STATUS_REMOVED


# --- resolve -------------------------------------------------------------------


def test_resolve_links_into_the_api_and_names_the_live_api(
    endpoint, operation, api, actor
):
    hits = {
        hit.id: hit
        for hit in api_search_source.resolve(
            [f"endpoint:{endpoint.pk}", f"operation:{operation.pk}"], actor
        )
    }

    endpoint_hit = hits[f"endpoint:{endpoint.pk}"]
    assert endpoint_hit.link == f"/apis/{api.pk}/endpoints/{endpoint.pk}"
    assert endpoint_hit.title == "GET /zebracorn/{id} — Orders API"
    assert endpoint_hit.summary == "Fetch a zebracorn"
    operation_hit = hits[f"operation:{operation.pk}"]
    assert operation_hit.link == f"/apis/{api.pk}/operations/{operation.pk}"
    assert operation_hit.title == "send orders.quokkaforge.created — Orders API"
    assert operation_hit.summary == "Announce a new order"


def test_resolve_shows_a_renamed_api_without_reindexing(endpoint, api, actor):
    get_catalog_entity_model().objects.filter(pk=api.pk).update(title="Renamed API")

    [hit] = api_search_source.resolve([f"endpoint:{endpoint.pk}"], actor)

    assert hit.title.endswith(" — Renamed API")


def test_resolve_uses_the_name_when_the_api_has_no_title(group, actor):
    system = create_system(name="other", owner=group)
    untitled = create_api(name="plain-api", owner=group, system=system)
    endpoint = ApiEndpoint.objects.create(api=untitled, method="GET", path="/x")

    [hit] = api_search_source.resolve([f"endpoint:{endpoint.pk}"], actor)

    assert hit.title == "GET /x — plain-api"


def test_resolve_omits_removed_rows_and_removed_apis(endpoint, operation, api, actor):
    ids = [f"endpoint:{endpoint.pk}", f"operation:{operation.pk}"]
    ApiEndpoint.objects.filter(pk=endpoint.pk).update(status="removed")

    assert [h.id for h in api_search_source.resolve(ids, actor)] == [
        f"operation:{operation.pk}"
    ]

    get_catalog_entity_model().objects.filter(pk=api.pk).update(status=STATUS_REMOVED)

    assert api_search_source.resolve(ids, actor) == []


def test_resolve_omits_everything_for_anonymous_actors(endpoint):
    from django.contrib.auth.models import AnonymousUser

    assert api_search_source.resolve([f"endpoint:{endpoint.pk}"], AnonymousUser()) == []


@pytest.mark.parametrize(
    ("denied", "survivor_kind"),
    [(ENDPOINT_READ_PERMISSION, "operation"), (OPERATION_READ_PERMISSION, "endpoint")],
)
def test_resolve_applies_each_read_permission(
    monkeypatch, endpoint, operation, actor, denied, survivor_kind
):
    class Evaluator:
        def check(self, user, permission, resource=None):
            return permission != denied

    monkeypatch.setattr(
        "atlas_plugin_apis.search_source.get_policy_evaluator", lambda: Evaluator()
    )

    hits = api_search_source.resolve(
        [f"endpoint:{endpoint.pk}", f"operation:{operation.pk}"], actor
    )

    assert [hit.kind for hit in hits] == [survivor_kind]
