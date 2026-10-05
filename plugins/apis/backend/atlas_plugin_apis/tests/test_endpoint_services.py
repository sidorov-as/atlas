"""Tests for the Service<->Endpoint dependency API
and its cross-plugin
auto-`consumesAPI` wiring (verify `recompute_relations` fires and
`GET /api/apis/{apiId}/relations/` reflects the new `apiConsumedBy`
immediately after an auto-created `consumesAPI`).

Also covers search/filter/sort/pagination on the Linked Services
list, the consumers-graph projection, and rejection of linking for
a `removed` Endpoint — the backend enforcement added alongside these tests,
since the UI-only hiding left the API itself unguarded).
"""

from types import SimpleNamespace

import pytest
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_group,
    create_system,
)

from atlas_plugin_apis.api.views import _service_summary_out
from atlas_plugin_apis.models import ApiEndpoint, ServiceEndpointUsage

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="billing-api", owner=group, system=system)


@pytest.fixture
def service(group, system):
    return create_component(name="billing-service", owner=group, system=system)


@pytest.fixture
def endpoint(api):
    return ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_GET,
        path="/v1/invoices",
    )


def _link(client, endpoint, service):
    return client.post(
        f"/api/endpoints/{endpoint.id}/services/",
        {"serviceId": str(service.id)},
    )


def _seed_link(endpoint, service):
    """Create a `ServiceEndpointUsage` directly, bypassing the create API's
    authorization — for tests below that only exercise reads (list/consumers)
    and need a link owned by a team the test's client isn't a member of."""
    return ServiceEndpointUsage.objects.create(endpoint=endpoint, service=service)


def test_link_creates_usage_and_auto_creates_consumes_api(
    owner_client,
    endpoint,
    service,
    api,
):
    response = _link(owner_client, endpoint, service)

    assert response.status_code == 201
    body = response.json()
    assert body["apiRelationCreated"] is True
    assert body["service"]["id"] == str(service.id)
    assert ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()

    relations = owner_client.get(f"/api/apis/{api.id}/relations/").json()
    assert any(
        relation["predicate"] == "apiConsumedBy"
        and relation["targetId"] == str(service.id)
        for relation in relations
    )


def test_link_does_not_duplicate_consumes_api_for_a_second_endpoint(
    owner_client,
    api,
    service,
    endpoint,
):
    second_endpoint = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_POST,
        path="/v1/invoices",
    )
    _link(owner_client, endpoint, service)

    response = _link(owner_client, second_endpoint, service)

    assert response.status_code == 201
    assert response.json()["apiRelationCreated"] is False
    consumed = service.component_details.consumes_apis.filter(pk=api.id)
    assert consumed.count() == 1


def test_linking_the_same_endpoint_twice_is_rejected(
    owner_client,
    endpoint,
    service,
):
    _link(owner_client, endpoint, service)

    response = _link(owner_client, endpoint, service)

    assert response.status_code == 409
    assert (
        ServiceEndpointUsage.objects.filter(
            endpoint=endpoint,
            service=service,
        ).count()
        == 1
    )


def test_unlink_removes_the_link_but_not_consumes_api(
    owner_client,
    endpoint,
    service,
    api,
):
    _link(owner_client, endpoint, service)

    response = owner_client.delete(
        f"/api/endpoints/{endpoint.id}/services/{service.id}/",
    )

    assert response.status_code == 204
    assert not ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()
    assert service.component_details.consumes_apis.filter(pk=api.id).exists()


def test_unauthenticated_request_is_rejected(dmr_client, endpoint, service):
    response = _link(dmr_client, endpoint, service)

    assert response.status_code in (401, 403)


def test_linking_requires_membership_in_the_services_owner_group(
    member_client, endpoint, service
):
    """A plain authenticated user who is not a member of `service`'s owner
    Group cannot link it to someone else's Endpoint (prerelease security
    audit finding: `.create` used to be unrestricted-if-authenticated,
    letting any user link any Service to any Endpoint)."""
    response = _link(member_client, endpoint, service)

    assert response.status_code == 403
    assert not ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()


def test_unlinking_requires_membership_in_the_services_owner_group(
    member_client, endpoint, service
):
    _seed_link(endpoint, service)

    response = member_client.delete(
        f"/api/endpoints/{endpoint.id}/services/{service.id}/",
    )

    assert response.status_code == 403
    assert ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()


def test_linking_a_removed_endpoint_is_rejected(owner_client, endpoint, service):
    endpoint.status = ApiEndpoint.STATUS_REMOVED
    endpoint.save(update_fields=["status"])

    response = _link(owner_client, endpoint, service)

    assert response.status_code == 409
    assert not ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()


# --- Linked Services list: search/filter/sort/pagination -


@pytest.fixture
def other_team(group):
    return create_group(name="payments-team")


@pytest.fixture
def other_service(other_team, system):
    return create_component(name="payments-service", owner=other_team, system=system)


def _list(client, endpoint, **params):
    return client.get(f"/api/endpoints/{endpoint.id}/services/", params)


def test_list_search_matches_service_name_or_title(
    member_client, endpoint, service, other_service
):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint, search="billing")

    body = response.json()
    assert body["page"]["objectList"][0]["service"]["id"] == str(service.id)
    assert len(body["page"]["objectList"]) == 1


def test_list_filters_by_team(
    member_client, endpoint, service, other_service, group, other_team
):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint, team_id=str(other_team.id))

    ids = {item["service"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(other_service.id)}


def test_list_default_sort_is_service_display_name_ascending(
    member_client, endpoint, service, other_service
):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint)

    names = [item["service"]["name"] for item in response.json()["page"]["objectList"]]
    assert names == sorted(names)


def test_list_sort_desc_reverses_order(member_client, endpoint, service, other_service):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint, order="desc")

    names = [item["service"]["name"] for item in response.json()["page"]["objectList"]]
    assert names == sorted(names, reverse=True)


def test_list_is_paginated(member_client, endpoint, service, other_service):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint, page=1, page_size=1)

    body = response.json()
    assert body["count"] == 2
    assert body["numPages"] == 2
    assert len(body["page"]["objectList"]) == 1


# --- Compact consumers graph data -------------------------


def test_consumers_returns_endpoint_summary_and_linked_services(
    member_client,
    endpoint,
    service,
    other_service,
):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = member_client.get(f"/api/endpoints/{endpoint.id}/consumers/")

    assert response.status_code == 200
    body = response.json()
    assert body["endpoint"]["id"] == str(endpoint.id)
    assert body["endpoint"]["status"] == "active"
    ids = {item["id"] for item in body["services"]}
    assert ids == {str(service.id), str(other_service.id)}


def test_consumers_reflects_a_removed_endpoint_status(member_client, endpoint):
    endpoint.status = ApiEndpoint.STATUS_REMOVED
    endpoint.save(update_fields=["status"])

    response = member_client.get(f"/api/endpoints/{endpoint.id}/consumers/")

    assert response.json()["endpoint"]["status"] == "removed"


def _seed_many_links(endpoint, system, group, count, prefix="svc"):
    for index in range(count):
        service = create_component(
            name=f"{prefix}-{index:03d}", owner=group, system=system
        )
        _seed_link(endpoint, service)


def test_consumers_default_request_is_capped_at_50(
    member_client, endpoint, system, group
):
    _seed_many_links(endpoint, system, group, 60)

    body = member_client.get(f"/api/endpoints/{endpoint.id}/consumers/").json()

    assert len(body["services"]) == 50
    assert body["count"] == 60


def test_consumers_later_page_continues_in_order(
    member_client, endpoint, system, group
):
    _seed_many_links(endpoint, system, group, 60)

    body = member_client.get(
        f"/api/endpoints/{endpoint.id}/consumers/?page=2&page_size=50"
    ).json()

    assert [item["name"] for item in body["services"]] == [
        f"svc-{index:03d}" for index in range(50, 60)
    ]
    assert body["count"] == 60


def test_consumers_search_narrows_page_and_count(
    member_client, endpoint, system, group
):
    _seed_many_links(endpoint, system, group, 5, prefix="pay")
    _seed_many_links(endpoint, system, group, 7, prefix="other")

    body = member_client.get(
        f"/api/endpoints/{endpoint.id}/consumers/?search=PAY"
    ).json()

    assert len(body["services"]) == 5
    assert body["count"] == 5


def test_consumers_unknown_endpoint_is_not_found(member_client):
    response = member_client.get(
        "/api/endpoints/00000000-0000-0000-0000-000000000000/consumers/"
    )

    assert response.status_code == 404


# --- System on the Service summary ---------------------------------


def _assert_system(summary, system):
    assert summary["system"] == system.ref
    assert summary["systemId"] == str(system.id)
    assert summary["systemName"] == (system.title or system.name)


def test_linked_services_carry_the_services_system(
    member_client, endpoint, service, system
):
    _seed_link(endpoint, service)

    body = _list(member_client, endpoint).json()

    by_id = {
        item["service"]["id"]: item["service"] for item in body["page"]["objectList"]
    }
    _assert_system(by_id[str(service.id)], system)


def test_consumers_carry_the_services_system(member_client, endpoint, service, system):
    _seed_link(endpoint, service)

    body = member_client.get(f"/api/endpoints/{endpoint.id}/consumers/").json()

    by_id = {item["id"]: item for item in body["services"]}
    _assert_system(by_id[str(service.id)], system)


def test_link_response_carries_the_services_system(
    owner_client, endpoint, service, system
):
    body = _link(owner_client, endpoint, service).json()

    _assert_system(body["service"], system)


def test_summary_without_a_system_has_null_system_fields(service):
    # `ComponentDetails.system` is NOT NULL today, so no stored Service can lack
    # a system; the summary still has to degrade to nulls if that ever changes.
    stub = SimpleNamespace(
        id=service.id,
        ref=service.ref,
        name=service.name,
        title=service.title,
        owner=service.owner,
        component_details=SimpleNamespace(system=None),
    )

    summary = _service_summary_out(stub).model_dump()

    assert summary["system"] is None
    assert summary["system_id"] is None
    assert summary["system_name"] is None


def test_listing_system_does_not_add_a_query_per_service(
    member_client, endpoint, group, system, django_assert_max_num_queries
):
    _seed_many_links(endpoint, system, group, 12)

    with django_assert_max_num_queries(20):
        response = member_client.get(f"/api/endpoints/{endpoint.id}/consumers/")

    assert response.status_code == 200
    assert len(response.json()["services"]) == 12


# --- Origin / source ---------------------------------------------------


def test_rest_link_records_manual_origin_and_ui_source(owner_client, endpoint, service):
    _link(owner_client, endpoint, service)

    usage = ServiceEndpointUsage.objects.get(endpoint=endpoint, service=service)
    assert (usage.origin, usage.source) == ("manual", "ui")


def test_unlinking_a_yaml_origin_link_is_a_conflict(owner_client, endpoint, service):
    usage = _seed_link(endpoint, service)
    usage.origin = ServiceEndpointUsage.ORIGIN_YAML
    usage.save()

    response = owner_client.delete(
        f"/api/endpoints/{endpoint.id}/services/{service.id}/"
    )

    assert response.status_code == 409
    assert "ingestion" in response.json()["detail"][0]["msg"]
    assert ServiceEndpointUsage.objects.filter(pk=usage.pk).exists()


# --- Grouped consumers ------------------------------------------------


def _grouped(client, endpoint, **params):
    return client.get(f"/api/endpoints/{endpoint.id}/consumers/", params)


@pytest.fixture
def teams():
    return [create_group(name=f"team-{letter}") for letter in "abcde"]


def _link_new(endpoint, owner, system, name):
    service = create_component(name=name, owner=owner, system=system)
    _seed_link(endpoint, service)
    return service


@pytest.fixture
def eighteen_consumers(endpoint, system, teams):
    """18 Services across 5 teams: 6, 5, 4 and then two teams with one Service each."""
    for team, size in zip(teams, (6, 5, 4, 2, 1), strict=True):
        for index in range(size):
            _link_new(endpoint, team, system, f"{team.name}-svc-{index}")
    return teams


def test_consumers_without_group_by_has_no_groups_key(member_client, endpoint, service):
    _seed_link(endpoint, service)

    body = _grouped(member_client, endpoint).json()

    assert "groups" not in body
    assert "servicesCount" not in body


def test_group_by_team_lists_groups_and_folds_single_services(
    member_client, endpoint, eighteen_consumers
):
    teams = eighteen_consumers

    body = _grouped(member_client, endpoint, group_by="team").json()

    assert [(g["name"], g["count"]) for g in body["groups"]] == [
        ("team-a", 6),
        ("team-b", 5),
        ("team-c", 4),
        ("team-d", 2),
    ]
    assert body["groups"][0]["id"] == str(teams[0].id)
    assert [s["name"] for s in body["services"]] == ["team-e-svc-0"]
    assert body["count"] == 18
    assert body["servicesCount"] == 1


def test_group_members_by_group_id(member_client, endpoint, eighteen_consumers):
    team_c = eighteen_consumers[2]

    body = _grouped(
        member_client, endpoint, group_by="team", group_id=str(team_c.id)
    ).json()

    assert len(body["services"]) == 4
    assert {s["teamId"] for s in body["services"]} == {str(team_c.id)}
    assert body["count"] == 4
    assert "groups" not in body
    assert "servicesCount" not in body


def test_group_members_larger_than_a_page(member_client, endpoint, system, group):
    for index in range(70):
        _link_new(endpoint, group, system, f"svc-{index:03d}")

    body = _grouped(
        member_client, endpoint, group_by="team", group_id=str(group.id)
    ).json()

    assert len(body["services"]) == 50
    assert body["count"] == 70


def test_search_narrows_group_counts(member_client, endpoint, system, teams):
    for index in range(3):
        _link_new(endpoint, teams[0], system, f"pay-{index}")
    for index in range(2):
        _link_new(endpoint, teams[0], system, f"other-{index}")
    _link_new(endpoint, teams[1], system, "pay-solo")

    body = _grouped(member_client, endpoint, group_by="team", search="pay").json()

    assert [(g["name"], g["count"]) for g in body["groups"]] == [("team-a", 3)]
    assert [s["name"] for s in body["services"]] == ["pay-solo"]
    assert body["count"] == 4


def test_search_can_drop_a_group_to_a_single_service(
    member_client, endpoint, system, teams
):
    _link_new(endpoint, teams[0], system, "pay-1")
    _link_new(endpoint, teams[0], system, "other-1")

    body = _grouped(member_client, endpoint, group_by="team", search="pay").json()

    assert body["groups"] == []
    assert [s["name"] for s in body["services"]] == ["pay-1"]


def test_group_by_system_groups_by_the_services_system(
    member_client, endpoint, group, system
):
    other_system = create_system(name="edge", owner=group)
    for index in range(2):
        _link_new(endpoint, group, system, f"core-{index}")
    _link_new(endpoint, group, other_system, "edge-solo")

    body = _grouped(member_client, endpoint, group_by="system").json()

    assert [(g["id"], g["count"]) for g in body["groups"]] == [(str(system.id), 2)]
    assert [s["name"] for s in body["services"]] == ["edge-solo"]

    members = _grouped(
        member_client, endpoint, group_by="system", group_id=str(system.id)
    ).json()
    assert members["count"] == 2


def test_service_without_a_team_has_null_team_fields_and_stays_ungrouped(
    member_client, endpoint, system, teams
):
    _link_new(endpoint, teams[0], system, "owned-1")
    _link_new(endpoint, teams[0], system, "owned-2")
    _link_new(endpoint, None, system, "orphan-1")
    _link_new(endpoint, None, system, "orphan-2")

    body = _grouped(member_client, endpoint, group_by="team").json()

    assert [g["name"] for g in body["groups"]] == ["team-a"]
    orphans = {s["name"]: s for s in body["services"]}
    assert set(orphans) == {"orphan-1", "orphan-2"}
    assert orphans["orphan-1"]["team"] is None
    assert orphans["orphan-1"]["teamId"] is None
    assert orphans["orphan-1"]["teamName"] is None
    assert body["count"] == 4
    assert body["servicesCount"] == 2


def test_service_without_a_team_is_listed_without_grouping(
    member_client, endpoint, system
):
    _link_new(endpoint, None, system, "orphan")

    consumers = _grouped(member_client, endpoint).json()
    linked = _list(member_client, endpoint).json()

    assert consumers["services"][0]["teamId"] is None
    assert linked["page"]["objectList"][0]["service"]["teamName"] is None


def test_unsupported_group_by_is_rejected(member_client, endpoint):
    assert _grouped(member_client, endpoint, group_by="tag").status_code in (400, 422)


def test_group_id_without_group_by_is_rejected(member_client, endpoint, group):
    response = _grouped(member_client, endpoint, group_id=str(group.id))

    assert response.status_code in (400, 422)


def test_unknown_group_id_returns_an_empty_page(member_client, endpoint, service):
    _seed_link(endpoint, service)

    body = _grouped(
        member_client,
        endpoint,
        group_by="team",
        group_id="00000000-0000-0000-0000-000000000000",
    ).json()

    assert body["services"] == []
    assert body["count"] == 0
