"""Regression coverage for generated local-authentication policy."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest
from allauth.account.forms import default_token_generator
from allauth.account.models import EmailAddress
from allauth.account.signals import password_reset
from allauth.account.utils import user_pk_to_url_str
from atlas_plugin_standard_catalog.models import ActorDetails
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings

from server.apps.catalog.auth_middleware import PROVIDER_KEY
from server.apps.catalog.models import (
    AccountAccess,
    CatalogEntity,
    ExternalIdentityLink,
)
from server.settings.selected_plugins import AUTHENTICATION

pytestmark = pytest.mark.django_db

STRONG_PASSWORD = "correct-horse-battery-staple-47"


@pytest.fixture(autouse=True)
def _clear_auth_rate_limit_cache():
    cache.clear()
    yield
    cache.clear()


def _policy(**changes):
    policy = deepcopy(AUTHENTICATION)
    policy.update(changes)
    return policy


def _local_policy(*, signup: str = "disabled"):
    policy = _policy()
    policy["providers"][0]["signup"] = signup
    return policy


@pytest.mark.parametrize(
    "path",
    [
        "/_allauth/browser/v1/auth/signup",
        "/auth/browser/v1/signup",
    ],
)
def test_signup_is_closed_by_default_without_creating_state(dmr_client, path):
    before = get_user_model().objects.count()

    response = dmr_client.post(
        path,
        {"username": "new-user", "password": STRONG_PASSWORD},
    )

    assert response.status_code == 403
    assert get_user_model().objects.count() == before
    assert not ActorDetails.objects.filter(entity__name="new-user").exists()
    assert not ExternalIdentityLink.objects.exists()
    assert not dmr_client.session.get("_auth_user_id")


def test_signup_opt_in_is_reported_and_applied_to_both_routes(dmr_client):
    policy = _local_policy(signup="enabled")
    with override_settings(ATLAS_AUTHENTICATION=policy):
        config = dmr_client.get("/auth/browser/v1/config")
        response = dmr_client.post(
            "/auth/browser/v1/signup",
            {"username": "new-user", "password": STRONG_PASSWORD},
        )

    assert config.status_code == 200
    assert config.json()["providers"][0]["signupOpen"] is True
    assert response.status_code == 200
    assert get_user_model().objects.filter(username="new-user").exists()


def test_public_config_reports_closed_signup_without_backend_policy_details(
    dmr_client,
):
    response = dmr_client.get("/auth/browser/v1/config")

    assert response.status_code == 200
    assert response.json()["providers"][0]["signupOpen"] is False
    body = response.content.decode()
    assert "passwordPolicy" not in body
    assert "adminPassword" not in body
    assert "recovery" not in body


def test_direct_local_login_is_rejected_when_local_is_unselected(
    dmr_client,
    owner_account,
):
    policy = _policy(
        providers=(
            {
                "id": "atlas.auth.example",
                "flowKind": "redirect",
                "presentation": {"displayName": "Example SSO"},
            },
        ),
        default="atlas.auth.example",
    )
    with override_settings(ATLAS_AUTHENTICATION=policy):
        response = dmr_client.post(
            "/_allauth/browser/v1/auth/login",
            {"username": owner_account.username, "password": "password123"},
        )

    assert response.status_code == 400
    assert not dmr_client.session.get("_auth_user_id")


def test_admin_password_login_defaults_to_disabled(
    superuser_account,
):
    client = Client()
    response = client.post(
        "/admin/login/",
        {"username": superuser_account.username, "password": "password123"},
    )

    assert response.status_code == 200
    assert not client.session.get("_auth_user_id")


def test_allowlisted_active_staff_can_use_break_glass_and_catalog_api(
    superuser_account,
):
    client = Client()
    policy = _policy(
        adminPassword={
            "mode": "break-glass",
            "principalIds": (superuser_account.pk,),
        }
    )
    with override_settings(ATLAS_AUTHENTICATION=policy):
        response = client.post(
            "/admin/login/",
            {"username": superuser_account.username, "password": "password123"},
        )
        api_response = client.get("/api/me/")

    assert response.status_code == 302
    assert api_response.status_code == 200
    assert client.session[PROVIDER_KEY] == "atlas.auth.admin-password"


def test_read_only_break_glass_superuser_cannot_mutate_catalog_or_admin(
    superuser_account,
    group,
    system,
):
    client = Client()
    access = AccountAccess.objects.create(
        account=superuser_account, read_only=True
    )
    policy = _policy(
        adminPassword={
            "mode": "break-glass",
            "principalIds": (superuser_account.pk,),
        }
    )

    with override_settings(ATLAS_AUTHENTICATION=policy):
        login_response = client.post(
            "/admin/login/",
            {
                "username": superuser_account.username,
                "password": "password123",
            },
        )
        catalog_write = client.post(
            "/api/systems/",
            data=json.dumps(
                {
                    "metadata": {"name": "break-glass-write"},
                    "spec": {"owner": group.ref},
                }
            ),
            content_type="application/json",
        )
        own_flag_write = client.post(
            f"/admin/auth/user/{superuser_account.pk}/change/",
            {
                "username": superuser_account.username,
                "account_access-TOTAL_FORMS": "1",
                "account_access-INITIAL_FORMS": "1",
                "account_access-0-id": str(access.pk),
                "account_access-0-account": str(superuser_account.pk),
            },
        )
        current = client.get("/api/me/")

    access.refresh_from_db()
    assert login_response.status_code == 302
    assert current.status_code == 200
    assert catalog_write.status_code == 403
    assert own_flag_write.status_code == 403
    assert access.read_only is True
    assert not CatalogEntity.objects.filter(name="break-glass-write").exists()
    system.refresh_from_db()
    assert system.status == CatalogEntity.STATUS_ACTIVE


def test_break_glass_rejects_unlisted_or_inactive_staff(
    superuser_account,
):
    client = Client()
    policy = _policy(
        adminPassword={
            "mode": "break-glass",
            "principalIds": (superuser_account.pk + 1,),
        }
    )
    with override_settings(ATLAS_AUTHENTICATION=policy):
        response = client.post(
            "/admin/login/",
            {"username": superuser_account.username, "password": "password123"},
        )

    assert response.status_code == 200
    assert not client.session.get("_auth_user_id")


def test_withdrawing_break_glass_allowlist_invalidates_existing_session(
    superuser_account,
):
    client = Client()
    enabled = _policy(
        adminPassword={
            "mode": "break-glass",
            "principalIds": (superuser_account.pk,),
        }
    )
    with override_settings(ATLAS_AUTHENTICATION=enabled):
        login = client.post(
            "/admin/login/",
            {"username": superuser_account.username, "password": "password123"},
        )
    with override_settings(ATLAS_AUTHENTICATION=_policy()):
        response = client.get("/api/me/")

    assert login.status_code == 302
    assert response.status_code == 401


def test_failed_local_logins_are_indistinguishable_and_rate_limited(
    dmr_client,
    owner_account,
):
    first = dmr_client.post(
        "/_allauth/browser/v1/auth/login",
        {"username": owner_account.username, "password": "wrong-password"},
    )
    unknown = dmr_client.post(
        "/_allauth/browser/v1/auth/login",
        {"username": "missing-user", "password": "wrong-password"},
    )
    responses = [
        dmr_client.post(
            "/_allauth/browser/v1/auth/login",
            {"username": owner_account.username, "password": "wrong-password"},
        )
        for _ in range(5)
    ]

    assert first.status_code == unknown.status_code == 400
    assert first.json() == unknown.json()
    assert any(response.status_code == 429 for response in responses)


def test_shared_password_policy_accepts_long_passwords_and_rejects_bounds(
    owner_account,
):
    validate_password("x" * 64, user=owner_account)
    with pytest.raises(ValidationError):
        validate_password("short", user=owner_account)
    with pytest.raises(ValidationError):
        validate_password("x" * 129, user=owner_account)
    with pytest.raises(ValidationError):
        validate_password("password", user=owner_account)


def test_bootstrap_requires_non_logged_secret_and_is_idempotent(monkeypatch):
    monkeypatch.delenv("ATLAS_BOOTSTRAP_PASSWORD", raising=False)
    with pytest.raises(CommandError):
        call_command("seed_admin")

    monkeypatch.setenv("ATLAS_BOOTSTRAP_PASSWORD", STRONG_PASSWORD)
    call_command("seed_admin", username="bootstrap")
    call_command("seed_admin", username="bootstrap")

    account = get_user_model().objects.get(username="bootstrap")
    assert account.is_active and account.is_staff and account.is_superuser
    assert account.check_password(STRONG_PASSWORD)
    assert get_user_model().objects.filter(username="bootstrap").count() == 1


@pytest.mark.parametrize(
    "path",
    [
        "/_allauth/browser/v1/auth/password/request",
        "/_allauth/browser/v1/auth/password/reset",
        "/_allauth/browser/v1/account/password/change",
        "/_allauth/browser/v1/account/email",
    ],
)
def test_recovery_and_account_management_are_closed_by_default(
    dmr_client,
    path,
):
    response = dmr_client.post(path, {})
    assert response.status_code == 404


def test_public_recovery_is_generic_single_use_and_revokes_existing_sessions(
    dmr_client,
    owner_account,
):
    EmailAddress.objects.create(
        user=owner_account,
        email="owner@example.com",
        primary=True,
        verified=True,
    )
    active_session = Client()
    active_session.force_login(owner_account)
    policy = _policy(
        recovery={
            "mode": "public",
            "verifiedAddressesRequired": True,
            "tokenMaxAgeSeconds": 3600,
        }
    )
    with override_settings(ATLAS_AUTHENTICATION=policy):
        known = dmr_client.post(
            "/_allauth/browser/v1/auth/password/request",
            {"email": "owner@example.com"},
        )
        unknown = dmr_client.post(
            "/_allauth/browser/v1/auth/password/request",
            {"email": "missing@example.com"},
        )
        owner_account.refresh_from_db()
        key = (
            f"{user_pk_to_url_str(owner_account)}-"
            f"{default_token_generator.make_token(owner_account)}"
        )
        reset = dmr_client.post(
            "/_allauth/browser/v1/auth/password/reset",
            {"key": key, "password": "new-correct-horse-password-48"},
        )
        replay = dmr_client.post(
            "/_allauth/browser/v1/auth/password/reset",
            {"key": key, "password": "another-correct-password-49"},
        )
        old_session = active_session.get("/api/me/")

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    # Headless allauth reports the resulting unauthenticated session as 401;
    # the credential update itself succeeded and deliberately did not log in.
    assert reset.status_code == 401, reset.json()
    owner_account.refresh_from_db()
    assert owner_account.check_password("new-correct-horse-password-48")
    assert replay.status_code == 400
    assert old_session.status_code == 401


def test_public_recovery_requires_verified_address_and_is_throttled(
    dmr_client,
    owner_account,
    mailoutbox,
):
    EmailAddress.objects.create(
        user=owner_account,
        email="unverified@example.com",
        primary=True,
        verified=False,
    )
    policy = _policy(
        recovery={
            "mode": "public",
            "verifiedAddressesRequired": True,
            "tokenMaxAgeSeconds": 3600,
        }
    )
    with override_settings(ATLAS_AUTHENTICATION=policy):
        first = dmr_client.post(
            "/_allauth/browser/v1/auth/password/request",
            {"email": "unverified@example.com"},
        )
        responses = [
            dmr_client.post(
                "/_allauth/browser/v1/auth/password/request",
                {"email": "unverified@example.com"},
            )
            for _ in range(5)
        ]

    assert first.status_code == 200
    assert mailoutbox == []
    assert any(response.status_code == 429 for response in responses)


def test_password_reset_signal_revokes_every_existing_session(owner_account):
    first = Client()
    second = Client()
    first.force_login(owner_account)
    second.force_login(owner_account)

    password_reset.send(
        sender=owner_account.__class__,
        request=None,
        user=owner_account,
    )

    assert first.get("/api/me/").status_code == 401
    assert second.get("/api/me/").status_code == 401
