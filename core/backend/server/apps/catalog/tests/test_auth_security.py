from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from django.test import Client, RequestFactory, override_settings

from server.apps.catalog.auth_middleware import (
    IDENTITY_LINK_GENERATION_KEY,
    IDENTITY_LINK_KEY,
    POLICY_GENERATION_KEY,
    PRINCIPAL_GENERATION_KEY,
    PROVIDER_KEY,
    SOURCE_GENERATION_KEY,
    SOURCE_KEY,
)
from server.apps.catalog.auth_security import (
    REDACTED,
    authentication_budget_allowed,
    current_policy_generation,
    redact_authentication_data,
    redact_authentication_event,
    revoke_principal_sessions,
    trusted_client_address,
    validate_outbound_url,
)
from server.apps.catalog.models import (
    AuthenticationRateLimit,
    AuthenticationSourceBinding,
    ExternalIdentityLink,
)
from server.settings.selected_plugins import AUTHENTICATION

pytestmark = pytest.mark.django_db


def test_redaction_is_recursive_and_allowlist_shaped():
    value = {
        "providerId": "atlas.auth.oidc",
        "clientSecret": "secret-value",
        "nested": {"access_token": "token-value", "status": "ok"},
        "body": b"raw-body",
    }

    assert redact_authentication_event(None, None, value) == (
        redact_authentication_data(value)
    )

    assert redact_authentication_data(value) == {
        "providerId": "atlas.auth.oidc",
        "clientSecret": REDACTED,
        "nested": {"access_token": REDACTED, "status": "ok"},
        "body": REDACTED,
    }


def test_outbound_policy_rejects_unlisted_and_metadata_destinations():
    assert (
        validate_outbound_url(
            "https://id.example.com/token",
            allowed_origins=("https://id.example.com",),
        )
        == "https://id.example.com/token"
    )
    with pytest.raises(ValueError, match="allowlisted"):
        validate_outbound_url(
            "http://169.254.169.254/latest/meta-data",
            allowed_origins=("https://id.example.com",),
        )


def test_forwarded_client_address_is_ignored_without_trusted_proxy():
    request = RequestFactory().get(
        "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.9"
    )
    assert trusted_client_address(request) == "10.0.0.1"


def test_database_rate_limit_is_shared_by_identical_budget_keys():
    request = RequestFactory().post("/auth/browser/v1/signup")
    request.META["REMOTE_ADDR"] = "192.0.2.10"
    for _ in range(8):
        allowed, _ = authentication_budget_allowed(
            request, provider_id="atlas.auth.local", account="same-user"
        )
        assert allowed
    allowed, retry_after = authentication_budget_allowed(
        request, provider_id="atlas.auth.local", account="same-user"
    )
    assert not allowed
    assert retry_after > 0
    assert AuthenticationRateLimit.objects.filter(scope="account").count() == 1


def test_policy_change_and_revoke_all_invalidate_existing_session(
    owner_account,
):
    client = Client()
    client.force_login(owner_account)
    session = client.session
    session["atlas_auth_provider"] = "atlas.auth.local"
    session["atlas_authenticated_at"] = datetime.now(UTC).timestamp()
    session[POLICY_GENERATION_KEY] = current_policy_generation()
    session[PRINCIPAL_GENERATION_KEY] = 0
    session.save()

    revoke_principal_sessions(owner_account)
    assert client.get("/api/me/").status_code == 401

    changed = deepcopy(AUTHENTICATION)
    changed["sessionMaxAgeSeconds"] = 3600
    with override_settings(ATLAS_AUTHENTICATION=changed):
        assert current_policy_generation() > session[POLICY_GENERATION_KEY]


def test_inactive_principal_is_rejected_on_the_next_session_request(
    owner_account,
):
    client = Client()
    client.force_login(owner_account)

    owner_account.is_active = False
    owner_account.save(update_fields=("is_active",))

    assert client.get("/api/me/").status_code == 401


def test_source_and_link_generations_invalidate_external_session(owner_account):
    policy = deepcopy(AUTHENTICATION)
    policy["providers"] = (
        {
            "id": "example.auth.external",
            "flowKind": "redirect",
            "presentation": {"displayName": "Example"},
            "sourceBinding": {
                "sourceId": "https://id.example",
                "configurationFingerprint": "sha256:example",
            },
        },
    )
    policy["default"] = "example.auth.external"
    binding = AuthenticationSourceBinding.objects.create(
        provider_id="example.auth.external",
        source_id="https://id.example",
        configuration_fingerprint="sha256:example",
    )
    link = ExternalIdentityLink.objects.create(
        user=owner_account,
        provider_id="example.auth.external",
        source_id="https://id.example",
        external_subject="subject-1",
    )
    client = Client()
    client.force_login(owner_account)
    with override_settings(ATLAS_AUTHENTICATION=policy):
        session = client.session
        session[PROVIDER_KEY] = "example.auth.external"
        session[SOURCE_KEY] = binding.source_id
        session[SOURCE_GENERATION_KEY] = binding.generation
        session[IDENTITY_LINK_KEY] = link.pk
        session[IDENTITY_LINK_GENERATION_KEY] = link.revocation_generation
        session[POLICY_GENERATION_KEY] = current_policy_generation()
        session.save()
        assert client.get("/api/me/").status_code == 200

        binding.generation += 1
        binding.save(update_fields=("generation",))
        assert client.get("/api/me/").status_code == 401


def test_auth_health_is_allowlisted_and_secret_free(dmr_client):
    response = dmr_client.get("/healthz/auth/providers/")
    body = response.content.decode()

    assert response.status_code == 200
    assert response.json()["providers"][0]["providerId"] == "atlas.auth.local"
    assert "callbackUrl" in response.json()["providers"][0]
    assert "secret" not in body.casefold()
    assert "token" not in body.casefold()
