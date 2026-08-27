"""Coverage for the booking demo seed's actor interaction and its C4 rendering,
plus the AsyncAPI-importer-produced Operation catalog: `_lookup_operations`'
read of the rows
`atlas_plugin_apis.asyncapi_import.sync_operations_from_spec` already wrote
via `ApiDetails.post_save`, replacing the old hand-authored
`OPERATIONS` fixture.
"""

import pytest
from atlas_plugin_apis.models import ApiOperation, ServiceOperationUsage
from atlas_plugin_c4.c4 import build_system_context
from django.core.management import call_command

from server.apps.catalog.models import (
    KIND_ACTOR,
    KIND_API,
    KIND_COMPONENT,
    KIND_SYSTEM,
    ArchitectureRelationship,
    CatalogEntity,
)

pytestmark = pytest.mark.django_db


def test_seed_creates_manual_actor_relationship():
    call_command("seed_booking_demo", "--yes")

    guest = CatalogEntity.objects.get(kind=KIND_ACTOR, name="guest-persona")
    booking_web = CatalogEntity.objects.get(
        kind=KIND_COMPONENT, name="booking-web"
    )
    relationship = ArchitectureRelationship.objects.get(
        source=guest, target=booking_web
    )
    assert relationship.interaction_kind == "manual"
    assert (
        CatalogEntity.objects.filter(
            kind=KIND_ACTOR, name="guest-persona"
        ).count()
        == 1
    )


def test_seed_covers_every_interaction_kind_and_an_external_dependency():
    call_command("seed_booking_demo", "--yes")

    kinds = set(
        ArchitectureRelationship.objects.values_list(
            "interaction_kind", flat=True
        )
    )
    assert kinds == {"synchronous", "asynchronous", "data-access", "manual"}

    external_api_ids = set(
        CatalogEntity.objects.filter(
            kind=KIND_API, tags__contains=["External"]
        ).values_list("id", flat=True),
    )
    assert external_api_ids
    assert ArchitectureRelationship.objects.filter(
        target_id__in=external_api_ids
    ).exists()


def test_seed_actor_renders_as_a_person_without_ownership_derived_actors():
    call_command("seed_booking_demo", "--yes")

    system = CatalogEntity.objects.get(
        kind=KIND_SYSTEM, name="booking-reservations"
    )
    payload = build_system_context(system)

    guest = CatalogEntity.objects.get(kind=KIND_ACTOR, name="guest-persona")
    people = [
        item
        for item in payload["elements"]
        if item["type"] in {"Person", "PersonExt"}
    ]
    assert people == [
        {
            "type": "PersonExt",
            "alias": f"user_{guest.id.hex}",
            "label": "Guest",
            "tags": ["AtlasPerson"],
        },
    ]


def test_seed_produces_importer_written_operations_with_no_duplicates():
    call_command("seed_booking_demo", "--yes")

    notifications_api = CatalogEntity.objects.get(
        kind=KIND_API, name="notifications-api"
    )
    booking_events_api = CatalogEntity.objects.get(
        kind=KIND_API, name="booking-events-api"
    )

    operation_keys = set(
        ApiOperation.objects.filter(
            api__in=[notifications_api, booking_events_api]
        ).values_list("operation_key", flat=True),
    )
    # `OPERATION_USAGES` (seed_booking_demo.py) depends on exactly these keys
    # existing.
    assert operation_keys == {
        "booking.confirmed-receive",
        "payout.completed-receive",
        "refund.issued-receive",
        "notification.delivery-status-send",
        "booking.confirmed-send",
        "booking.cancelled-send",
    }
    assert ApiOperation.objects.filter(api=notifications_api).count() == 4
    assert ApiOperation.objects.filter(api=booking_events_api).count() == 2


def test_seed_operation_usages_link_to_the_importer_produced_rows():
    call_command("seed_booking_demo", "--yes")

    notifications_api = CatalogEntity.objects.get(
        kind=KIND_API, name="notifications-api"
    )
    payout_completed = ApiOperation.objects.get(
        api=notifications_api, operation_key="payout.completed-receive"
    )
    delivery_status = ApiOperation.objects.get(
        api=notifications_api, operation_key="notification.delivery-status-send"
    )

    assert (
        ServiceOperationUsage.objects.filter(operation=payout_completed).count()
        == 1
    )
    assert (
        ServiceOperationUsage.objects.filter(operation=delivery_status).count()
        == 2
    )
