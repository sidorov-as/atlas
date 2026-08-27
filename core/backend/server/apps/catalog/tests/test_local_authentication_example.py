"""Fast HTTP smoke contract for examples/authentication/local."""

import pytest
from django.contrib.auth import get_user_model

from server.apps.catalog.models import CatalogEntity

pytestmark = pytest.mark.django_db


def test_local_example_journey_has_closed_signup_and_authorized_sessions(
    dmr_client,
    other_user,
    group,
):
    before = get_user_model().objects.count()
    signup = dmr_client.post(
        "/auth/browser/v1/signup",
        {
            "username": "closed-example-signup",
            "password": "unused-local-example-password",
        },
    )
    assert signup.status_code == 403
    assert get_user_model().objects.count() == before

    login = dmr_client.post(
        "/auth/browser/v1/providers/atlas.auth.local/credentials",
        {"username": "other", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["meta"]["is_authenticated"] is True

    current = dmr_client.get("/api/me/")
    assert current.status_code == 200
    assert current.json()["isAdmin"] is False

    denied = dmr_client.post(
        "/api/systems/",
        {
            "metadata": {"name": "local-example-denied"},
            "spec": {"owner": "group:platform"},
        },
    )
    assert denied.status_code == 403
    assert not CatalogEntity.objects.filter(
        kind="system", name="local-example-denied"
    ).exists()

    logout = dmr_client.delete("/auth/browser/v1/session")
    assert logout.status_code == 204
    assert (
        dmr_client.get("/auth/browser/v1/session").json()["meta"][
            "is_authenticated"
        ]
        is False
    )
