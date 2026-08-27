"""Session auth tests."""

import pytest

pytestmark = pytest.mark.django_db


def test_login_establishes_a_session(dmr_client, owner_account):
    login_response = dmr_client.post(
        "/_allauth/browser/v1/auth/login",
        {"username": owner_account.username, "password": "password123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["meta"]["is_authenticated"] is True

    protected_response = dmr_client.get("/api/systems/")
    assert protected_response.status_code == 200


def test_unauthenticated_request_to_protected_endpoint_is_rejected(dmr_client):
    response = dmr_client.get("/api/systems/")
    assert response.status_code == 401


def test_local_login_still_works_when_oidc_is_also_configured(
    dmr_client,
    owner_account,
    settings,
):
    """Local and OIDC selected together — a
    deployment that also configures `atlas.auth.oidc` keeps `atlas.auth.local`
    usable as break-glass access, unaffected by OIDC being configured or made
    the default (`atlas.auth.local` is never
    disabled by the presence of another provider)."""
    settings.SOCIALACCOUNT_PROVIDERS = {
        "openid_connect": {"APPS": [{"provider_id": "atlas.auth.oidc"}]},
    }

    login_response = dmr_client.post(
        "/_allauth/browser/v1/auth/login",
        {"username": owner_account.username, "password": "password123"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["meta"]["is_authenticated"] is True
