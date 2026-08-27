"""Atlas-owned authentication gateway API and compatibility boundaries."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from atlas_plugin_api import (
    AuthenticationFailure,
    AuthenticationFailureCategory,
    AuthenticationFlowKind,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    CredentialFieldKind,
    CredentialFieldPresentation,
    ExternalGroupSnapshot,
    RedirectChallenge,
    VerifiedIdentity,
)
from atlas_plugin_auth_oidc.config import OIDCConfig
from atlas_plugin_auth_oidc.plugin import PROVIDER_ID as OIDC_PROVIDER_ID
from atlas_plugin_auth_oidc.provider import OIDCProvider
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from server.apps.catalog import auth_gateway
from server.apps.catalog.models import (
    AccountAccess,
    AuthenticationAttempt,
    ExternalIdentityLink,
)
from server.settings.selected_plugins import AUTHENTICATION

pytestmark = pytest.mark.django_db

PROVIDER_ID = "example.auth.fixture"
SOURCE_ID = "urn:atlas:test-provider"


def _policy(*, flow_kind: str, provider_id: str = PROVIDER_ID):
    policy = deepcopy(AUTHENTICATION)
    policy["providers"] = (
        {
            "id": provider_id,
            "contractVersion": "atlas.auth.providers.v1",
            "flowKind": flow_kind,
            "remoteLogout": "unsupported",
            "presentation": {"displayName": "Fixture provider"},
            "sourceBinding": {
                "sourceId": SOURCE_ID,
                "configurationFingerprint": "sha256:fixture",
            },
        },
    )
    policy["default"] = provider_id
    policy["publicOrigin"] = "https://atlas.example"
    return policy


def _identity() -> VerifiedIdentity:
    return VerifiedIdentity(
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        subject="person-42",
        groups=ExternalGroupSnapshot.unsupported(),
    )


class _CredentialProvider:
    descriptor = AuthenticationProviderDescriptor(
        id=PROVIDER_ID,
        flow_kind=AuthenticationFlowKind.CREDENTIALS,
        presentation=AuthenticationProviderPresentation(
            display_name="Fixture credentials",
            credential_fields=(
                CredentialFieldPresentation(
                    id="password",
                    label="Password",
                    kind=CredentialFieldKind.SECRET,
                ),
            ),
        ),
    )

    def __init__(self, result=None):
        self.calls = 0
        self.result = result or _identity()

    def authenticate(self, context, credentials):
        self.calls += 1
        assert context.source_id == SOURCE_ID
        assert credentials.values["password"] == "correct"
        return self.result


class _RedirectProvider:
    descriptor = AuthenticationProviderDescriptor(
        id=PROVIDER_ID,
        flow_kind=AuthenticationFlowKind.REDIRECT,
        presentation=AuthenticationProviderPresentation(
            display_name="Fixture SSO"
        ),
    )

    def __init__(self, result=None):
        self.begin_calls = 0
        self.complete_calls = 0
        self.callback_url = None
        self.result = result or _identity()

    def begin(self, context):
        self.begin_calls += 1
        self.callback_url = context.callback_url
        return RedirectChallenge(
            f"https://idp.example/authorize?state=state-{context.attempt_id}"
        )

    def complete(self, context):
        self.complete_calls += 1
        assert context.callback_parameters["state"].startswith("state-")
        return self.result


def _install_runtime(monkeypatch, provider):
    lookup = SimpleNamespace(
        get=lambda provider_id: provider if provider_id == PROVIDER_ID else None
    )
    monkeypatch.setattr(
        auth_gateway, "get_authentication_provider_lookup", lambda: lookup
    )


def _link(owner_account):
    return ExternalIdentityLink.objects.create(
        user=owner_account,
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        external_subject="person-42",
    )


def test_config_is_generated_selection_only_and_primes_csrf(dmr_client):
    response = dmr_client.get("/auth/browser/v1/config")

    assert response.status_code == 200
    assert response.json() == {
        "providers": [
            {
                "id": "atlas.auth.local",
                "contractVersion": "atlas.auth.providers.v1",
                "flowKind": "credentials",
                "presentation": {
                    "displayName": "Username and password",
                    "credentialFields": [
                        {
                            "id": "username",
                            "label": "Username",
                            "kind": "text",
                            "autocomplete": "username",
                        },
                        {
                            "id": "password",
                            "label": "Password",
                            "kind": "secret",
                            "autocomplete": "current-password",
                        },
                    ],
                },
                "remoteLogout": "unsupported",
                "isDefault": True,
                "signupOpen": False,
            }
        ],
        "defaultProviderId": "atlas.auth.local",
        "providerChoiceUrl": "/login?choose-provider=1",
    }
    assert "csrftoken" in response.cookies
    assert "no-cache" in response.headers["Cache-Control"]


def test_core_session_read_and_delete_keep_django_session_semantics(
    dmr_client,
    owner_account,
):
    dmr_client.force_login(owner_account)
    current = dmr_client.get("/auth/browser/v1/session")
    deleted = dmr_client.delete("/auth/browser/v1/session")
    after = dmr_client.get("/auth/browser/v1/session")

    assert current.json()["meta"]["is_authenticated"] is True
    assert current.json()["data"]["user"]["username"] == "owner"
    assert deleted.status_code == 204
    assert after.json()["meta"]["is_authenticated"] is False


def test_local_gateway_login_rotates_session_and_establishes_core_session(
    dmr_client,
    owner_account,
):
    session = dmr_client.session
    session["attacker-known"] = True
    session.save()
    old_key = session.session_key

    response = dmr_client.post(
        "/auth/browser/v1/providers/atlas.auth.local/credentials",
        {"username": owner_account.username, "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["is_authenticated"] is True
    assert dmr_client.session.session_key != old_key
    assert dmr_client.session["atlas_auth_provider"] == "atlas.auth.local"


def test_selected_credential_provider_is_invoked_and_core_logs_user_in(
    dmr_client,
    owner_account,
    monkeypatch,
):
    provider = _CredentialProvider()
    _install_runtime(monkeypatch, provider)
    _link(owner_account)

    with override_settings(
        ATLAS_AUTHENTICATION=_policy(flow_kind="credentials")
    ):
        response = dmr_client.post(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/credentials",
            {"username": "person", "password": "correct"},
        )

    assert response.status_code == 200
    assert provider.calls == 1
    assert dmr_client.session["_auth_user_id"] == str(owner_account.pk)
    assert dmr_client.session["atlas_auth_source"] == SOURCE_ID


def test_external_session_observes_live_read_only_flag_changes(
    dmr_client,
    owner_account,
    system,
    monkeypatch,
):
    provider = _CredentialProvider()
    _install_runtime(monkeypatch, provider)
    _link(owner_account)
    owner_account.is_superuser = True
    owner_account.save(update_fields=("is_superuser",))

    with override_settings(
        ATLAS_AUTHENTICATION=_policy(flow_kind="credentials")
    ):
        login_response = dmr_client.post(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/credentials",
            {"username": "person", "password": "correct"},
        )
        before = dmr_client.patch(
            f"/api/systems/{system.id}/",
            data=json.dumps({"metadata": {"title": "Before"}}),
            content_type="application/json",
        )
        access = AccountAccess.objects.create(
            account=owner_account, read_only=True
        )
        denied = dmr_client.patch(
            f"/api/systems/{system.id}/",
            data=json.dumps({"metadata": {"title": "Blocked"}}),
            content_type="application/json",
        )
        current = dmr_client.get("/api/me/")
        access.read_only = False
        access.save(update_fields=("read_only", "updated_at"))
        after = dmr_client.patch(
            f"/api/systems/{system.id}/",
            data=json.dumps({"metadata": {"title": "After"}}),
            content_type="application/json",
        )

    assert login_response.status_code == 200
    assert before.status_code == 200
    assert denied.status_code == 403
    assert current.json()["isReadOnly"] is True
    assert after.status_code == 200
    system.refresh_from_db()
    assert system.title == "After"


def test_preprovisioned_read_only_identity_is_denied_until_exact_link(
    dmr_client,
    owner_account,
    system,
    monkeypatch,
):
    provider = _CredentialProvider()
    _install_runtime(monkeypatch, provider)
    access = AccountAccess.objects.create(account=owner_account, read_only=True)
    policy = _policy(flow_kind="credentials")
    policy["providers"][0].update(
        {
            "principalProvisioning": "preprovisioned",
            "actorProvisioning": "manual",
            "groupSync": {"mode": "none"},
        }
    )

    with override_settings(ATLAS_AUTHENTICATION=policy):
        missing = dmr_client.post(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/credentials",
            {"username": "person", "password": "correct"},
        )
        call_command(
            "manage_auth_identity",
            "link",
            "--provider",
            PROVIDER_ID,
            "--source",
            SOURCE_ID,
            "--subject",
            "person-42",
            "--principal-id",
            str(owner_account.pk),
            "--reason",
            "preprovisioned read-only access",
            "--apply",
        )
        login_response = dmr_client.post(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/credentials",
            {"username": "person", "password": "correct"},
        )
        read = dmr_client.get(f"/api/systems/{system.id}/")
        write = dmr_client.patch(
            f"/api/systems/{system.id}/",
            data=json.dumps({"metadata": {"title": "Blocked"}}),
            content_type="application/json",
        )

    access.refresh_from_db()
    assert missing.status_code == 403
    assert login_response.status_code == 200
    assert read.status_code == 200
    assert write.status_code == 403
    assert access.read_only is True
    system.refresh_from_db()
    assert system.title == ""


def test_safe_credential_failure_has_category_and_correlation_id(
    dmr_client,
    monkeypatch,
):
    provider = _CredentialProvider(
        AuthenticationFailure(AuthenticationFailureCategory.INVALID_CREDENTIALS)
    )
    _install_runtime(monkeypatch, provider)

    with override_settings(
        ATLAS_AUTHENTICATION=_policy(flow_kind="credentials")
    ):
        response = dmr_client.post(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/credentials",
            {"username": "person", "password": "correct"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["category"] == "invalid_credentials"
    assert response.json()["error"]["stage"] == "credentials"
    assert response.json()["error"]["correlationId"]


@pytest.mark.parametrize(
    ("provider_id", "configured_flow"),
    [("unselected.auth", "credentials"), (PROVIDER_ID, "redirect")],
)
def test_unselected_and_wrong_flow_credentials_never_invoke_provider(
    dmr_client,
    monkeypatch,
    provider_id,
    configured_flow,
):
    provider = _CredentialProvider()
    _install_runtime(monkeypatch, provider)

    with override_settings(
        ATLAS_AUTHENTICATION=_policy(flow_kind=configured_flow)
    ):
        response = dmr_client.post(
            f"/auth/browser/v1/providers/{provider_id}/credentials",
            {"username": "person", "password": "correct"},
        )

    assert response.status_code == 404
    assert provider.calls == 0


def _start_redirect(client, *, return_url="/systems"):
    response = client.post(
        f"/auth/browser/v1/providers/{PROVIDER_ID}/start",
        {"returnUrl": return_url},
    )
    state = None
    if response.status_code == 200:
        query = urlsplit(response.json()["redirectUrl"]).query
        state = parse_qs(query)["state"][0]
    return response, state


def test_redirect_start_callback_and_replay_are_core_correlated(
    dmr_client,
    owner_account,
    monkeypatch,
):
    provider = _RedirectProvider()
    _install_runtime(monkeypatch, provider)
    _link(owner_account)

    with override_settings(ATLAS_AUTHENTICATION=_policy(flow_kind="redirect")):
        started, state = _start_redirect(dmr_client)
        completed = dmr_client.get(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/callback",
            {"state": state, "code": "one-use"},
        )
        replay = dmr_client.get(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/callback",
            {"state": state, "code": "one-use"},
        )

    assert started.status_code == 200
    assert completed.status_code == 302
    assert completed.headers["Location"] == "/systems"
    assert replay.status_code == 400
    assert replay.json()["error"]["category"] == "invalid_state"
    assert provider.begin_calls == provider.complete_calls == 1
    assert provider.callback_url == (
        "https://atlas.example/auth/browser/v1/providers/"
        f"{PROVIDER_ID}/callback"
    )


def test_first_party_oidc_runs_through_gateway_provisioning_and_session(
    dmr_client,
    monkeypatch,
):
    issuer = "https://idp.example"
    discovery = f"{issuer}/.well-known/openid-configuration"

    class FakeOIDCTransport:
        def get_json(self, url, *, bearer_token=None):
            if url == discovery:
                return {
                    "issuer": issuer,
                    "authorization_endpoint": f"{issuer}/authorize",
                    "token_endpoint": f"{issuer}/token",
                    "userinfo_endpoint": f"{issuer}/userinfo",
                    "jwks_uri": f"{issuer}/jwks",
                    "code_challenge_methods_supported": ["S256"],
                }
            assert url == f"{issuer}/userinfo"
            assert bearer_token == "access-token"
            return {
                "sub": "subject-42",
                "preferred_username": "oidc-person",
                "name": "OIDC Person",
                "email": "person@example.com",
                "email_verified": True,
            }

        def post_form(self, url, data):
            assert url == f"{issuer}/token"
            assert data["redirect_uri"] == (
                "https://atlas.example/auth/browser/v1/providers/"
                f"{OIDC_PROVIDER_ID}/callback"
            )
            assert data["code_verifier"]
            return {
                "id_token": "deterministic-id-token",
                "access_token": "access-token",
            }

    token_claims = {
        "iss": issuer,
        "sub": "subject-42",
        "aud": "atlas",
        "nonce": "set-after-start",
    }
    provider = OIDCProvider(
        OIDCConfig.model_validate(
            {
                "discoveryUrl": discovery,
                "expectedIssuer": issuer,
                "clientId": "atlas",
                "clientSecret": "integration-test-secret-material",
                "groupsClaim": None,
            }
        ),
        transport=FakeOIDCTransport(),
        token_verifier=lambda *_args: token_claims,
    )
    lookup = SimpleNamespace(
        get=lambda provider_id: (
            provider if provider_id == OIDC_PROVIDER_ID else None
        )
    )
    monkeypatch.setattr(
        auth_gateway, "get_authentication_provider_lookup", lambda: lookup
    )
    policy = _policy(flow_kind="redirect", provider_id=OIDC_PROVIDER_ID)
    configured = dict(policy["providers"][0])
    configured.update(
        {
            "principalProvisioning": "automatic",
            "actorProvisioning": "manual",
            "profileFields": ("username", "displayName", "email"),
            "groupSync": {
                "mode": "none",
                "snapshotRequirement": "unsupported",
                "maxAgeSeconds": 28_800,
                "mappings": {},
            },
            "sourceBinding": {
                "sourceId": issuer,
                "configurationFingerprint": "sha256:oidc-integration",
            },
        }
    )
    policy["providers"] = (configured,)
    policy["default"] = OIDC_PROVIDER_ID

    with override_settings(ATLAS_AUTHENTICATION=policy):
        started = dmr_client.post(
            f"/auth/browser/v1/providers/{OIDC_PROVIDER_ID}/start",
            {"returnUrl": "/systems"},
        )
        authorization = parse_qs(urlsplit(started.json()["redirectUrl"]).query)
        token_claims["nonce"] = authorization["nonce"][0]
        completed = dmr_client.get(
            f"/auth/browser/v1/providers/{OIDC_PROVIDER_ID}/callback",
            {"state": authorization["state"][0], "code": "one-use"},
        )
        session = dmr_client.get("/auth/browser/v1/session")
        logged_out = dmr_client.delete("/auth/browser/v1/session")
        after_logout = dmr_client.get("/auth/browser/v1/session")

    link = ExternalIdentityLink.objects.get(
        provider_id=OIDC_PROVIDER_ID,
        source_id=issuer,
        external_subject="subject-42",
    )
    assert started.status_code == 200
    assert authorization["code_challenge_method"] == ["S256"]
    assert completed.status_code == 302
    assert completed.headers["Location"] == "/systems"
    assert session.json()["meta"]["is_authenticated"] is True
    assert session.json()["data"]["user"]["id"] == link.user_id
    assert logged_out.status_code == 204
    assert after_logout.json()["meta"]["is_authenticated"] is False


def test_redirect_state_is_browser_bound_and_expires(
    dmr_client,
    monkeypatch,
):
    provider = _RedirectProvider()
    _install_runtime(monkeypatch, provider)
    other_browser = Client()

    with override_settings(ATLAS_AUTHENTICATION=_policy(flow_kind="redirect")):
        _, state = _start_redirect(dmr_client)
        mismatched = other_browser.get(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/callback",
            {"state": state},
        )
        AuthenticationAttempt.objects.update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        expired = dmr_client.get(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/callback",
            {"state": state},
        )

    assert mismatched.status_code == expired.status_code == 400
    assert provider.complete_calls == 0


def test_browser_redirect_failure_returns_to_sanitized_provider_choice(
    dmr_client,
    monkeypatch,
):
    provider = _RedirectProvider(
        AuthenticationFailure(
            AuthenticationFailureCategory.UNAVAILABLE,
            retryable=True,
        )
    )
    _install_runtime(monkeypatch, provider)

    with override_settings(ATLAS_AUTHENTICATION=_policy(flow_kind="redirect")):
        _, state = _start_redirect(dmr_client, return_url="/systems")
        response = dmr_client.get(
            f"/auth/browser/v1/providers/{PROVIDER_ID}/callback",
            {"state": state, "code": "safe-code"},
            HTTP_ACCEPT="text/html,application/xhtml+xml",
        )

    assert response.status_code == 302
    location = urlsplit(response.headers["Location"])
    query = parse_qs(location.query)
    assert location.path == "/login"
    assert query["choose-provider"] == ["1"]
    assert query["auth-error"] == ["provider_unavailable"]
    assert query["correlation-id"]
    assert query["return-url"] == ["/systems"]
    assert "safe-code" not in response.headers["Location"]
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.parametrize(
    "return_url",
    [
        "https://evil.example/phish",
        "//evil.example/phish",
        "/%252fevil.example/phish",
        "https://user:password@atlas.example/",
    ],
)
def test_redirect_start_rejects_unsafe_return_urls(
    dmr_client,
    monkeypatch,
    return_url,
):
    provider = _RedirectProvider()
    _install_runtime(monkeypatch, provider)
    with override_settings(ATLAS_AUTHENTICATION=_policy(flow_kind="redirect")):
        response, _ = _start_redirect(dmr_client, return_url=return_url)

    assert response.status_code == 400
    assert response.json()["error"]["category"] == "unsafe_return_url"
    assert provider.begin_calls == 0


def test_csrf_and_origin_are_required_for_state_changing_gateway_requests(
    owner_account,
):
    client = Client(enforce_csrf_checks=True)
    config = client.get("/auth/browser/v1/config")
    token = config.cookies["csrftoken"].value

    missing = client.post(
        "/auth/browser/v1/providers/atlas.auth.local/credentials",
        {"username": owner_account.username, "password": "password123"},
    )
    foreign = client.post(
        "/auth/browser/v1/providers/atlas.auth.local/credentials",
        {"username": owner_account.username, "password": "password123"},
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="https://evil.example",
    )
    accepted = client.post(
        "/auth/browser/v1/providers/atlas.auth.local/credentials",
        {"username": owner_account.username, "password": "password123"},
        HTTP_X_CSRFTOKEN=token,
    )

    assert missing.status_code == foreign.status_code == 403
    assert accepted.status_code == 200


def test_csrf_is_required_for_start_signup_and_logout(owner_account):
    client = Client(enforce_csrf_checks=True)
    client.force_login(owner_account)

    start = client.post(
        f"/auth/browser/v1/providers/{PROVIDER_ID}/start",
        {"returnUrl": "/"},
    )
    signup = client.post(
        "/auth/browser/v1/signup",
        {"username": "new-user", "password": "long-enough-password-47"},
    )
    logout = client.delete("/auth/browser/v1/session")

    assert start.status_code == signup.status_code == logout.status_code == 403
    assert (
        client.get("/auth/browser/v1/session").json()["meta"][
            "is_authenticated"
        ]
        is True
    )


def test_compatibility_config_filters_to_selected_redirect_providers(
    dmr_client,
):
    with override_settings(ATLAS_AUTHENTICATION=_policy(flow_kind="redirect")):
        response = dmr_client.get("/_allauth/browser/v1/config")

    assert response.json() == {
        "data": {
            "socialaccount": {
                "providers": [
                    {
                        "id": PROVIDER_ID,
                        "name": "Fixture provider",
                    }
                ]
            }
        }
    }


def test_unselected_allauth_redirect_and_internal_callback_are_blocked(
    dmr_client,
):
    redirect = dmr_client.post(
        "/_allauth/browser/v1/auth/provider/redirect",
        {"provider": "atlas.auth.oidc", "process": "login"},
    )
    callback = dmr_client.get(
        "/accounts/oidc/atlas.auth.oidc/login/callback/",
        {"state": "unknown", "code": "secret"},
    )

    assert redirect.status_code == callback.status_code == 404


def test_transitional_oidc_login_and_callback_names_are_mounted():
    assert (
        reverse(
            "openid_connect_login", kwargs={"provider_id": "atlas.auth.oidc"}
        )
        == "/accounts/oidc/atlas.auth.oidc/login/"
    )
    assert (
        reverse(
            "openid_connect_callback",
            kwargs={"provider_id": "atlas.auth.oidc"},
        )
        == "/accounts/oidc/atlas.auth.oidc/login/callback/"
    )
    assert reverse("gitea_login") == "/accounts/gitea/login/"
    assert reverse("gitea_callback") == "/accounts/gitea/login/callback/"


@pytest.mark.parametrize(
    "path",
    [
        "/_allauth/browser/v1/account/providers",
        "/_allauth/browser/v1/auth/provider/signup",
        "/_allauth/browser/v1/auth/provider/token",
    ],
)
def test_unaudited_allauth_linking_and_token_routes_are_closed(
    dmr_client,
    path,
):
    assert dmr_client.post(path, {}).status_code == 404
