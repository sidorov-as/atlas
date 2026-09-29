"""The detail payload tells the UI what the requesting user may do, so it can
hide actions the write endpoints would answer with 403."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from server.apps.catalog.models import KIND_SYSTEM, CatalogEntity

pytestmark = pytest.mark.django_db


def test_owner_gets_edit_permission_on_their_entity(owner_client, system):
    body = owner_client.get(f"/api/systems/{system.id}/").json()

    assert body["permissions"] == {"canEdit": True, "canPurge": False}


def test_non_member_is_denied_edit_on_someone_elses_entity(
    other_client,
    system,
):
    body = other_client.get(f"/api/systems/{system.id}/").json()

    assert body["permissions"] == {"canEdit": False, "canPurge": False}


def test_superuser_may_edit_and_purge(superuser_client, system):
    body = superuser_client.get(f"/api/systems/{system.id}/").json()

    assert body["permissions"] == {"canEdit": True, "canPurge": True}


def test_seeded_guest_edits_only_the_guest_system(dmr_client):
    call_command("seed_booking_demo", "--yes")
    guest = get_user_model().objects.get(username="guest")
    assert not (guest.is_staff or guest.is_superuser)
    dmr_client.force_login(guest)

    guest_system = CatalogEntity.objects.get(kind=KIND_SYSTEM, name="guest")
    other_system = CatalogEntity.objects.get(
        kind=KIND_SYSTEM, name="search-discovery"
    )

    own = dmr_client.get(f"/api/systems/{guest_system.id}/").json()
    other = dmr_client.get(f"/api/systems/{other_system.id}/").json()
    assert own["permissions"]["canEdit"] is True
    assert other["permissions"]["canEdit"] is False
