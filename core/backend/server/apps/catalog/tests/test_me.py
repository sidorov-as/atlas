"""Admin-status and read-only-status endpoint tests.
"""

import pytest

from server.apps.catalog.models import AccountAccess

pytestmark = pytest.mark.django_db


def test_me_requires_authentication(dmr_client):
    response = dmr_client.get("/api/me/")

    assert response.status_code == 401


def test_me_reports_non_admin_for_a_regular_user(owner_client):
    response = owner_client.get("/api/me/")

    assert response.status_code == 200
    assert response.json() == {"isAdmin": False, "isReadOnly": False}


def test_me_reports_admin_for_a_superuser(superuser_client):
    response = superuser_client.get("/api/me/")

    assert response.status_code == 200
    assert response.json() == {"isAdmin": True, "isReadOnly": False}


def test_me_reports_current_read_only_state(owner_client, owner_account):
    access = AccountAccess.objects.create(
        account=owner_account,
        read_only=True,
    )

    assert owner_client.get("/api/me/").json()["isReadOnly"] is True

    access.read_only = False
    access.save(update_fields=["read_only", "updated_at"])
    assert owner_client.get("/api/me/").json()["isReadOnly"] is False
