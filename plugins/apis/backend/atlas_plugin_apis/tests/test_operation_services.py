"""Tests for the Service<->Operation dependency API
including duplicate-link
rejection, multiple-services-same-role, self-link-of-document-owner
rejection, search/filter/sort/pagination, the channel-scoped
consumers aggregation across API documents, and per-role unlink.
"""

import pytest
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_group,
    create_system,
)

from atlas_plugin_apis.models import ApiOperation, ServiceOperationUsage

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="booking-api", owner=group, system=system, type="asyncapi")


@pytest.fixture
def service(group, system):
    return create_component(name="reporting-service", owner=group, system=system)


@pytest.fixture
def operation(api):
    return ApiOperation.objects.create(
        api=api,
        channel_address="booking.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCreated",
    )


def _link(client, operation, service, role="subscriber"):
    return client.post(
        f"/api/operations/{operation.id}/services/",
        {"serviceId": str(service.id), "role": role},
    )


def _seed_link(operation, service, role="subscriber"):
    """Create a `ServiceOperationUsage` directly, bypassing the create API's
    authorization — for tests below that only exercise reads (list/consumers)
    and need a link owned by a team the test's client isn't a member of."""
    return ServiceOperationUsage.objects.create(
        operation=operation, service=service, role=role
    )


# --- Link / unlink CRUD ------------------------------


def test_link_creates_a_service_operation_usage(owner_client, operation, service):
    response = _link(owner_client, operation, service, role="subscriber")

    assert response.status_code == 201
    body = response.json()
    assert body["service"]["id"] == str(service.id)
    assert body["role"] == "subscriber"
    assert ServiceOperationUsage.objects.filter(
        operation=operation,
        service=service,
        role="subscriber",
    ).exists()


def test_linking_the_same_operation_service_and_role_twice_is_rejected(
    owner_client, operation, service
):
    _link(owner_client, operation, service, role="subscriber")

    response = _link(owner_client, operation, service, role="subscriber")

    assert response.status_code == 409
    assert (
        ServiceOperationUsage.objects.filter(
            operation=operation,
            service=service,
            role="subscriber",
        ).count()
        == 1
    )


def test_multiple_services_can_hold_the_same_role(
    owner_client, operation, service, group, system
):
    other_service = create_component(
        name="analytics-service", owner=group, system=system
    )
    _link(owner_client, operation, service, role="subscriber")

    response = _link(owner_client, operation, other_service, role="subscriber")

    assert response.status_code == 201
    assert (
        ServiceOperationUsage.objects.filter(
            operation=operation, role="subscriber"
        ).count()
        == 2
    )


def test_a_service_can_hold_both_roles_on_one_operation(
    owner_client, operation, service
):
    _link(owner_client, operation, service, role="publisher")

    response = _link(owner_client, operation, service, role="subscriber")

    assert response.status_code == 201
    assert (
        ServiceOperationUsage.objects.filter(
            operation=operation, service=service
        ).count()
        == 2
    )


def test_linking_the_operations_own_document_owner_is_rejected(
    owner_client, operation, group, system, api
):
    provider = create_component(
        name="booking-service", owner=group, system=system, provides_apis=[api]
    )

    response = _link(owner_client, operation, provider, role="publisher")

    assert response.status_code == 409
    assert not ServiceOperationUsage.objects.filter(
        operation=operation, service=provider
    ).exists()


def test_unlink_removes_only_the_targeted_role(owner_client, operation, service):
    _link(owner_client, operation, service, role="publisher")
    _link(owner_client, operation, service, role="subscriber")

    response = owner_client.delete(
        f"/api/operations/{operation.id}/services/{service.id}/?role=publisher",
    )

    assert response.status_code == 204
    assert not ServiceOperationUsage.objects.filter(
        operation=operation,
        service=service,
        role="publisher",
    ).exists()
    assert ServiceOperationUsage.objects.filter(
        operation=operation,
        service=service,
        role="subscriber",
    ).exists()


def test_unlink_unknown_role_returns_404(owner_client, operation, service):
    _link(owner_client, operation, service, role="publisher")

    response = owner_client.delete(
        f"/api/operations/{operation.id}/services/{service.id}/?role=subscriber",
    )

    assert response.status_code == 404
    assert ServiceOperationUsage.objects.filter(
        operation=operation,
        service=service,
        role="publisher",
    ).exists()


def test_unauthenticated_request_is_rejected(dmr_client, operation, service):
    response = _link(dmr_client, operation, service)

    assert response.status_code in (401, 403)


def test_linking_requires_membership_in_the_services_owner_group(
    member_client, operation, service
):
    """A plain authenticated user who is not a member of `service`'s owner
    Group cannot link it to someone else's Operation (prerelease security
    audit finding: `.create` used to be unrestricted-if-authenticated,
    letting any user link any Service to any Operation)."""
    response = _link(member_client, operation, service)

    assert response.status_code == 403
    assert not ServiceOperationUsage.objects.filter(
        operation=operation, service=service
    ).exists()


def test_unlinking_requires_membership_in_the_services_owner_group(
    member_client, operation, service
):
    _seed_link(operation, service, role="publisher")

    response = member_client.delete(
        f"/api/operations/{operation.id}/services/{service.id}/?role=publisher",
    )

    assert response.status_code == 403
    assert ServiceOperationUsage.objects.filter(
        operation=operation, service=service, role="publisher"
    ).exists()


# --- Linked Services list: search/filter/sort/pagination --


@pytest.fixture
def other_team(group):
    return create_group(name="payments-team")


@pytest.fixture
def other_service(other_team, system):
    return create_component(name="analytics-service", owner=other_team, system=system)


def _list(client, operation, **params):
    return client.get(f"/api/operations/{operation.id}/services/", params)


def test_list_search_matches_service_name_or_title(
    member_client, operation, service, other_service
):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, search="reporting")

    body = response.json()
    assert body["page"]["objectList"][0]["service"]["id"] == str(service.id)
    assert len(body["page"]["objectList"]) == 1


def test_list_filters_by_team(
    member_client, operation, service, other_service, other_team
):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, team_id=str(other_team.id))

    ids = {item["service"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(other_service.id)}


def test_list_filters_by_role(member_client, operation, service, other_service):
    _seed_link(operation, service, role="publisher")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, role="publisher")

    ids = {item["service"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(service.id)}


def test_list_default_sort_is_service_display_name_ascending(
    member_client, operation, service, other_service
):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation)

    names = [item["service"]["name"] for item in response.json()["page"]["objectList"]]
    assert names == sorted(names)


def test_list_sort_desc_reverses_order(
    member_client, operation, service, other_service
):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, order="desc")

    names = [item["service"]["name"] for item in response.json()["page"]["objectList"]]
    assert names == sorted(names, reverse=True)


def test_list_is_paginated(member_client, operation, service, other_service):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, page=1, page_size=1)

    body = response.json()
    assert body["count"] == 2
    assert body["numPages"] == 2
    assert len(body["page"]["objectList"]) == 1


# --- Channel-scoped consumers aggregation ----------------


@pytest.fixture
def other_api(group, system):
    return create_api(name="billing-api", owner=group, system=system, type="asyncapi")


def test_consumers_aggregates_across_operations_sharing_the_channel_on_a_different_api(
    member_client,
    operation,
    other_api,
    service,
):
    other_operation = ApiOperation.objects.create(
        api=other_api,
        channel_address=operation.channel_address,
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onBookingCreatedReceive",
    )
    _seed_link(other_operation, service, role="subscriber")

    response = member_client.get(f"/api/operations/{operation.id}/consumers/")

    assert response.status_code == 200
    body = response.json()
    assert body["operation"]["id"] == str(operation.id)
    assert body["operation"]["channelAddress"] == operation.channel_address
    ids = {
        (participant["service"]["id"], participant["role"])
        for participant in body["participants"]
    }
    assert (str(service.id), "subscriber") in ids


def test_consumers_includes_each_operations_document_owner_implied_role(
    member_client,
    operation,
    other_api,
    group,
    system,
):
    provider = create_component(
        name="booking-service",
        owner=group,
        system=system,
        provides_apis=[operation.api],
    )
    other_provider = create_component(
        name="billing-service",
        owner=group,
        system=system,
        provides_apis=[other_api],
    )
    ApiOperation.objects.create(
        api=other_api,
        channel_address=operation.channel_address,
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onBookingCreatedReceive",
    )

    response = member_client.get(f"/api/operations/{operation.id}/consumers/")

    body = response.json()
    participants = {(p["service"]["id"], p["role"]) for p in body["participants"]}
    assert (str(provider.id), "publisher") in participants
    assert (str(other_provider.id), "subscriber") in participants


def test_consumers_does_not_aggregate_operations_on_an_unrelated_channel(
    member_client,
    operation,
    api,
    service,
):
    unrelated = ApiOperation.objects.create(
        api=api,
        channel_address="payment.settled",
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onPaymentSettled",
    )
    _seed_link(unrelated, service, role="subscriber")

    response = member_client.get(f"/api/operations/{operation.id}/consumers/")

    ids = {
        participant["service"]["id"] for participant in response.json()["participants"]
    }
    assert str(service.id) not in ids


def test_consumers_reflects_a_removed_operations_status(member_client, operation):
    operation.status = ApiOperation.STATUS_REMOVED
    operation.save(update_fields=["status"])

    response = member_client.get(f"/api/operations/{operation.id}/consumers/")

    assert response.json()["operation"]["status"] == "removed"


def _participants(client, operation):
    body = client.get(f"/api/operations/{operation.id}/consumers/").json()
    return {(p["service"]["id"], p["role"]) for p in body["participants"]}


def test_three_apis_on_one_event_key_give_one_publisher_and_two_subscribers(
    member_client, operation, other_api, group, system
):
    third_api = create_api(
        name="audit-api", owner=group, system=system, type="asyncapi"
    )
    publisher = create_component(
        name="booking-service",
        owner=group,
        system=system,
        provides_apis=[operation.api],
    )
    subscribers = [
        create_component(
            name=f"{api.name}-service",
            owner=group,
            system=system,
            provides_apis=[api],
        )
        for api in (other_api, third_api)
    ]
    for api, key in ((other_api, "q-billing"), (third_api, "q-audit")):
        ApiOperation.objects.create(
            api=api,
            channel_address=operation.channel_address,
            direction=ApiOperation.DIRECTION_RECEIVE,
            operation_key=key,
        )

    for viewed in ApiOperation.objects.all():
        assert _participants(member_client, viewed) == {
            (str(publisher.id), "publisher"),
            *((str(s.id), "subscriber") for s in subscribers),
        }


def test_removed_operation_is_excluded_from_the_graph_and_returns_when_revived(
    member_client, operation, other_api, group, system, service
):
    provider = create_component(
        name="billing-service",
        owner=group,
        system=system,
        provides_apis=[other_api],
    )
    other_operation = ApiOperation.objects.create(
        api=other_api,
        channel_address=operation.channel_address,
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onBookingCreatedReceive",
    )
    _seed_link(other_operation, service, role="subscriber")
    expected = {(str(provider.id), "subscriber"), (str(service.id), "subscriber")}
    assert expected <= _participants(member_client, operation)

    other_operation.status = ApiOperation.STATUS_REMOVED
    other_operation.save(update_fields=["status"])
    assert not expected & _participants(member_client, operation)

    other_operation.status = ApiOperation.STATUS_ACTIVE
    other_operation.save(update_fields=["status"])
    assert expected <= _participants(member_client, operation)


def _seed_participants(operation, system, group, publishers, subscribers):
    for role, count in (("publisher", publishers), ("subscriber", subscribers)):
        for index in range(count):
            service = create_component(
                name=f"{role[:3]}-{index:03d}", owner=group, system=system
            )
            _seed_link(operation, service, role=role)


def test_consumers_default_request_is_capped_at_50(
    member_client, operation, system, group
):
    _seed_participants(operation, system, group, publishers=40, subscribers=30)

    body = member_client.get(f"/api/operations/{operation.id}/consumers/").json()

    assert len(body["participants"]) == 50
    assert body["count"] == 70


def test_consumers_role_totals_do_not_depend_on_the_page(
    member_client, operation, system, group
):
    _seed_participants(operation, system, group, publishers=60, subscribers=10)

    body = member_client.get(
        f"/api/operations/{operation.id}/consumers/?page=2&page_size=50"
    ).json()

    assert len(body["participants"]) == 20
    assert body["publisherCount"] == 60
    assert body["subscriberCount"] == 10


def test_consumers_orders_publishers_first_then_by_name(
    member_client, operation, system, group
):
    _seed_participants(operation, system, group, publishers=2, subscribers=2)

    body = member_client.get(f"/api/operations/{operation.id}/consumers/").json()

    assert [
        (item["role"], item["service"]["name"]) for item in body["participants"]
    ] == [
        ("publisher", "pub-000"),
        ("publisher", "pub-001"),
        ("subscriber", "sub-000"),
        ("subscriber", "sub-001"),
    ]


def test_consumers_counts_document_owner_implied_publisher(
    member_client, operation, group, system
):
    provider = create_component(
        name="booking-service",
        owner=group,
        system=system,
        provides_apis=[operation.api],
    )

    body = member_client.get(f"/api/operations/{operation.id}/consumers/").json()

    assert body["publisherCount"] == 1
    assert body["participants"][0]["service"]["id"] == str(provider.id)
    assert body["participants"][0]["role"] == "publisher"


def test_consumers_search_narrows_page_and_totals(
    member_client, operation, system, group
):
    _seed_participants(operation, system, group, publishers=2, subscribers=5)

    body = member_client.get(
        f"/api/operations/{operation.id}/consumers/?search=SUB-00"
    ).json()

    assert body["count"] == 5
    assert body["publisherCount"] == 0
    assert body["subscriberCount"] == 5


def test_consumers_unknown_operation_is_not_found(member_client):
    response = member_client.get(
        "/api/operations/00000000-0000-0000-0000-000000000000/consumers/"
    )

    assert response.status_code == 404


# --- Origin / source ---------------------------------------------------


def test_rest_link_records_manual_origin_and_ui_source(
    owner_client, operation, service
):
    _link(owner_client, operation, service)

    usage = ServiceOperationUsage.objects.get(operation=operation, service=service)
    assert (usage.origin, usage.source) == ("manual", "ui")


def test_client_cannot_choose_origin_or_source(owner_client, operation, service):
    owner_client.post(
        f"/api/operations/{operation.id}/services/",
        {
            "serviceId": str(service.id),
            "role": "subscriber",
            "origin": "yaml",
            "source": "mcp",
        },
    )

    usage = ServiceOperationUsage.objects.get(operation=operation, service=service)
    assert (usage.origin, usage.source) == ("manual", "ui")


def test_unlinking_a_yaml_origin_link_is_a_conflict(owner_client, operation, service):
    usage = _seed_link(operation, service, role="publisher")
    usage.origin = ServiceOperationUsage.ORIGIN_YAML
    usage.save()

    response = owner_client.delete(
        f"/api/operations/{operation.id}/services/{service.id}/?role=publisher",
    )

    assert response.status_code == 409
    assert "ingestion" in response.json()["detail"][0]["msg"]
    assert ServiceOperationUsage.objects.filter(pk=usage.pk).exists()


def test_origin_is_per_role(owner_client, operation, service):
    yaml_link = _seed_link(operation, service, role="publisher")
    yaml_link.origin = ServiceOperationUsage.ORIGIN_YAML
    yaml_link.save()
    _link(owner_client, operation, service, role="subscriber")

    response = owner_client.delete(
        f"/api/operations/{operation.id}/services/{service.id}/?role=subscriber",
    )

    assert response.status_code == 204
    assert ServiceOperationUsage.objects.filter(pk=yaml_link.pk).exists()
    assert not ServiceOperationUsage.objects.filter(role="subscriber").exists()


# --- System on the Service summary ---------------------------------


def _assert_system(summary, system):
    assert summary["system"] == system.ref
    assert summary["systemId"] == str(system.id)
    assert summary["systemName"] == (system.title or system.name)


def test_linked_services_carry_the_services_system(
    member_client, operation, service, system
):
    _seed_link(operation, service)

    body = _list(member_client, operation).json()

    by_id = {
        item["service"]["id"]: item["service"] for item in body["page"]["objectList"]
    }
    _assert_system(by_id[str(service.id)], system)


def test_participants_carry_the_services_system(
    member_client, operation, service, system
):
    _seed_link(operation, service)

    body = member_client.get(f"/api/operations/{operation.id}/consumers/").json()

    by_id = {p["service"]["id"]: p["service"] for p in body["participants"]}
    _assert_system(by_id[str(service.id)], system)


def test_document_owner_participant_carries_its_system(
    member_client, operation, group, system
):
    provider = create_component(
        name="booking-service",
        owner=group,
        system=system,
        provides_apis=[operation.api],
    )

    body = member_client.get(f"/api/operations/{operation.id}/consumers/").json()

    by_id = {p["service"]["id"]: p["service"] for p in body["participants"]}
    _assert_system(by_id[str(provider.id)], system)


def test_link_response_carries_the_services_system(
    owner_client, operation, service, system
):
    body = _link(owner_client, operation, service).json()

    _assert_system(body["service"], system)


# --- Grouped consumers ------------------------------------------------


def _grouped(client, operation, **params):
    return client.get(f"/api/operations/{operation.id}/consumers/", params)


@pytest.fixture
def teams():
    return [create_group(name=f"team-{letter}") for letter in "abc"]


def _link_new(operation, owner, system, name, role):
    service = create_component(name=name, owner=owner, system=system)
    _seed_link(operation, service, role=role)
    return service


def test_consumers_without_group_by_has_no_group_lists(
    member_client, operation, service
):
    _seed_link(operation, service)

    body = _grouped(member_client, operation).json()

    assert "publisherGroups" not in body
    assert "subscriberGroups" not in body
    assert "participantsCount" not in body


def test_groups_are_reported_per_role(member_client, operation, system, teams):
    team_a, team_b, team_c = teams
    for index in range(3):
        _link_new(operation, team_a, system, f"a-pub-{index}", "publisher")
    for index in range(2):
        _link_new(operation, team_a, system, f"a-sub-{index}", "subscriber")
    for index in range(2):
        _link_new(operation, team_b, system, f"b-pub-{index}", "publisher")
    _link_new(operation, team_b, system, "b-sub-0", "subscriber")
    for index in range(4):
        _link_new(operation, team_c, system, f"c-sub-{index}", "subscriber")

    body = _grouped(member_client, operation, group_by="team").json()

    assert [(g["name"], g["count"]) for g in body["publisherGroups"]] == [
        ("team-a", 3),
        ("team-b", 2),
    ]
    assert [(g["name"], g["count"]) for g in body["subscriberGroups"]] == [
        ("team-a", 2),
        ("team-c", 4),
    ]
    assert [(p["service"]["name"], p["role"]) for p in body["participants"]] == [
        ("b-sub-0", "subscriber")
    ]
    assert body["count"] == 12
    assert body["participantsCount"] == 1
    assert body["publisherCount"] == 5
    assert body["subscriberCount"] == 7


def test_group_members_by_group_id_and_role(member_client, operation, system, teams):
    team_a = teams[0]
    for index in range(3):
        _link_new(operation, team_a, system, f"a-pub-{index}", "publisher")
    for index in range(2):
        _link_new(operation, team_a, system, f"a-sub-{index}", "subscriber")

    body = _grouped(
        member_client,
        operation,
        group_by="team",
        group_id=str(team_a.id),
        role="subscriber",
    ).json()

    assert {p["service"]["name"] for p in body["participants"]} == {
        "a-sub-0",
        "a-sub-1",
    }
    assert {p["role"] for p in body["participants"]} == {"subscriber"}
    assert body["count"] == 2
    assert "publisherGroups" not in body
    assert "participantsCount" not in body


def test_group_larger_than_a_page(member_client, operation, system, group):
    for index in range(70):
        _link_new(operation, group, system, f"sub-{index:03d}", "subscriber")

    body = _grouped(
        member_client,
        operation,
        group_by="team",
        group_id=str(group.id),
        role="subscriber",
    ).json()

    assert len(body["participants"]) == 50
    assert body["count"] == 70


def test_search_drops_a_group_below_two_matches(
    member_client, operation, system, teams
):
    for name in ("notify-1", "mail-1", "mail-2"):
        _link_new(operation, teams[0], system, name, "subscriber")

    body = _grouped(member_client, operation, group_by="team", search="notif").json()

    assert body["subscriberGroups"] == []
    assert [p["service"]["name"] for p in body["participants"]] == ["notify-1"]


def test_document_owner_implied_publisher_is_grouped(
    member_client, operation, system, group
):
    create_component(
        name="booking-service",
        owner=group,
        system=system,
        provides_apis=[operation.api],
    )
    _link_new(operation, group, system, "other-pub", "publisher")

    body = _grouped(member_client, operation, group_by="team").json()

    assert [(g["id"], g["count"]) for g in body["publisherGroups"]] == [
        (str(group.id), 2)
    ]


def test_group_by_system(member_client, operation, group, system):
    other_system = create_system(name="edge", owner=group)
    for index in range(2):
        _link_new(operation, group, system, f"core-{index}", "subscriber")
    _link_new(operation, group, other_system, "edge-solo", "subscriber")

    body = _grouped(member_client, operation, group_by="system").json()

    assert [(g["id"], g["count"]) for g in body["subscriberGroups"]] == [
        (str(system.id), 2)
    ]
    assert [p["service"]["name"] for p in body["participants"]] == ["edge-solo"]


def test_group_id_without_role_is_rejected(member_client, operation, group):
    response = _grouped(
        member_client, operation, group_by="team", group_id=str(group.id)
    )

    assert response.status_code in (400, 422)


def test_group_id_without_group_by_is_rejected(member_client, operation, group):
    response = _grouped(
        member_client, operation, group_id=str(group.id), role="subscriber"
    )

    assert response.status_code in (400, 422)


def test_unsupported_group_by_is_rejected(member_client, operation):
    assert _grouped(member_client, operation, group_by="tag").status_code in (400, 422)


def test_grouped_consumers_of_an_unknown_operation_is_not_found(member_client):
    response = member_client.get(
        "/api/operations/00000000-0000-0000-0000-000000000000/consumers/",
        {"group_by": "team"},
    )

    assert response.status_code == 404


def test_participant_without_a_team_has_null_team_fields_and_stays_ungrouped(
    member_client, operation, system, teams
):
    _link_new(operation, teams[0], system, "owned-1", "subscriber")
    _link_new(operation, teams[0], system, "owned-2", "subscriber")
    _link_new(operation, None, system, "orphan-1", "subscriber")
    _link_new(operation, None, system, "orphan-2", "subscriber")

    body = _grouped(member_client, operation, group_by="team").json()

    assert [g["name"] for g in body["subscriberGroups"]] == ["team-a"]
    orphans = {p["service"]["name"]: p["service"] for p in body["participants"]}
    assert set(orphans) == {"orphan-1", "orphan-2"}
    assert orphans["orphan-1"]["teamId"] is None
    assert orphans["orphan-1"]["teamName"] is None
    assert body["participantsCount"] == 2
