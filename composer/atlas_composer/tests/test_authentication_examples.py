from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from atlas_composer.lock import load_lock
from atlas_composer.manifest import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_EXAMPLE = REPO_ROOT / "examples" / "authentication" / "local"
KEYCLOAK_EXAMPLE = REPO_ROOT / "examples" / "authentication" / "oidc-keycloak"
GITEA_EXAMPLE = REPO_ROOT / "examples" / "authentication" / "oauth2-gitea"
CUSTOM_EXAMPLE = REPO_ROOT / "examples" / "authentication" / "custom-credentials"
DEFAULT_DISTRIBUTION = REPO_ROOT / "distributions" / "default"


def test_local_authentication_example_is_local_only_and_closed() -> None:
    manifest = load_manifest(LOCAL_EXAMPLE / "manifest.yaml")
    lock = load_lock(LOCAL_EXAMPLE / "lock.yaml")

    assert [provider.id for provider in manifest.auth.providers] == ["atlas.auth.local"]
    assert manifest.auth.default == "atlas.auth.local"
    assert manifest.auth.providers[0].signup == "disabled"
    assert manifest.auth.public_origin == "http://localhost:18080"
    assert [provider.id for provider in lock.auth.providers] == ["atlas.auth.local"]
    assert lock.auth.default == "atlas.auth.local"


def test_official_distribution_keeps_explicit_conservative_local_auth() -> None:
    manifest = load_manifest(DEFAULT_DISTRIBUTION / "manifest.yaml")
    lock = load_lock(DEFAULT_DISTRIBUTION / "lock.yaml")

    assert [provider.id for provider in manifest.auth.providers] == ["atlas.auth.local"]
    provider = manifest.auth.providers[0]
    assert manifest.auth.default == "atlas.auth.local"
    assert provider.signup == "disabled"
    assert provider.principal_provisioning == "preprovisioned"
    assert provider.actor_provisioning == "manual"
    assert [provider.id for provider in lock.auth.providers] == ["atlas.auth.local"]
    assert lock.auth.default == "atlas.auth.local"


def test_local_authentication_compose_has_isolated_bootstrap() -> None:
    compose = yaml.safe_load((LOCAL_EXAMPLE / "compose.yaml").read_text())

    assert compose["name"] == "atlas-auth-local"
    assert set(compose["services"]) == {
        "postgres",
        "initializer",
        "backend",
        "frontend",
    }
    assert "seed_admin" in " ".join(compose["services"]["initializer"]["command"])
    assert compose["services"]["postgres"]["volumes"] == [
        "local-postgres-data:/var/lib/postgresql/data"
    ]
    assert compose["networks"]["database"]["internal"] is True


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is unavailable")
def test_local_authentication_compose_renders() -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            ".env.example",
            "-f",
            "compose.yaml",
            "config",
            "--quiet",
        ],
        cwd=LOCAL_EXAMPLE,
        check=True,
        capture_output=True,
        text=True,
    )


def test_keycloak_example_is_oidc_only_with_exact_group_sync() -> None:
    manifest = load_manifest(KEYCLOAK_EXAMPLE / "manifest.yaml")
    lock = load_lock(KEYCLOAK_EXAMPLE / "lock.yaml")

    assert [provider.id for provider in manifest.auth.providers] == ["atlas.auth.oidc"]
    provider = manifest.auth.providers[0]
    assert manifest.auth.default == "atlas.auth.oidc"
    assert provider.principal_provisioning == "automatic"
    assert provider.actor_provisioning == "automatic"
    assert provider.group_sync.mode == "exact"
    assert provider.group_sync.mappings == {
        "atlas-platform": "oidc-platform",
        "atlas-readers": "oidc-readers",
    }
    assert provider.source_binding is not None
    assert [provider.id for provider in lock.auth.providers] == ["atlas.auth.oidc"]
    assert lock.auth.default == "atlas.auth.oidc"
    assert "oidc-client-only" not in (KEYCLOAK_EXAMPLE / "lock.yaml").read_text()


def test_keycloak_realm_has_exact_client_and_complete_groups_mapper() -> None:
    import json

    realm = json.loads((KEYCLOAK_EXAMPLE / "keycloak" / "realm.json").read_text())
    client = next(
        item for item in realm["clients"] if item["clientId"] == "atlas-example"
    )
    groups_scope = next(
        item for item in realm["clientScopes"] if item["name"] == "groups"
    )

    assert client["redirectUris"] == [
        "http://localhost:18080/auth/browser/v1/providers/atlas.auth.oidc/callback"
    ]
    assert client["webOrigins"] == ["http://localhost:18080"]
    assert client["secret"] == "${ATLAS_OIDC_CLIENT_SECRET}"
    assert "groups" in client["defaultClientScopes"]
    assert groups_scope["protocolMappers"][0]["config"] == {
        "claim.name": "groups",
        "full.path": "false",
        "id.token.claim": "true",
        "access.token.claim": "true",
        "userinfo.token.claim": "true",
    }
    assert {item["username"] for item in realm["users"]} == {
        "oidc-alice",
        "oidc-bob",
    }
    assert {item["name"] for item in realm["groups"]} >= {
        "atlas-platform",
        "atlas-readers",
        "unmapped-upstream",
    }


def test_keycloak_compose_is_isolated_pinned_and_health_gated() -> None:
    compose = yaml.safe_load((KEYCLOAK_EXAMPLE / "compose.yaml").read_text())

    assert compose["name"] == "atlas-auth-oidc-keycloak"
    assert set(compose["services"]) == {
        "postgres",
        "keycloak",
        "initializer",
        "backend",
        "frontend",
    }
    assert compose["services"]["keycloak"]["image"] == (
        "quay.io/keycloak/keycloak:26.4.5"
    )
    assert compose["services"]["keycloak"]["healthcheck"]
    assert compose["services"]["initializer"]["depends_on"]["keycloak"] == {
        "condition": "service_healthy"
    }
    assert compose["services"]["postgres"]["volumes"] == [
        "oidc-postgres-data:/var/lib/postgresql/data"
    ]
    assert compose["services"]["keycloak"]["volumes"][1] == (
        "oidc-keycloak-data:/opt/keycloak/data"
    )
    assert compose["networks"]["database"]["internal"] is True


def test_keycloak_browser_smoke_covers_required_journey() -> None:
    smoke = (KEYCLOAK_EXAMPLE / "browser_smoke.py").read_text()

    assert "/providers/{PROVIDER_ID}/start" in smoke
    assert "kc-form-login" in smoke
    assert '"principalCount": 1' in smoke
    assert '"groups": ["oidc-platform"]' in smoke
    assert '"groups": []' in smoke
    assert "present=False" in smoke
    assert "expected=403" in smoke
    assert "/auth/browser/v1/session" in smoke
    assert 'provider["flowKind"] != "credentials"' in smoke


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is unavailable")
def test_keycloak_authentication_compose_renders() -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            ".env.example",
            "-f",
            "compose.yaml",
            "config",
            "--quiet",
        ],
        cwd=KEYCLOAK_EXAMPLE,
        check=True,
        capture_output=True,
        text=True,
    )


def test_gitea_example_selects_provider_specific_oauth_without_group_sync() -> None:
    manifest = load_manifest(GITEA_EXAMPLE / "manifest.yaml")
    lock = load_lock(GITEA_EXAMPLE / "lock.yaml")

    assert [provider.id for provider in manifest.auth.providers] == ["atlas.auth.gitea"]
    provider = manifest.auth.providers[0]
    assert manifest.auth.default == "atlas.auth.gitea"
    assert provider.principal_provisioning == "automatic"
    assert provider.actor_provisioning == "automatic"
    assert provider.group_sync.mode == "none"
    assert provider.group_sync.mappings == {}
    assert provider.source_binding is not None
    assert provider.source_binding.source_id == "http://gitea.localhost:18082"
    assert [provider.id for provider in lock.auth.providers] == ["atlas.auth.gitea"]
    assert lock.auth.default == "atlas.auth.gitea"
    lock_text = (GITEA_EXAMPLE / "lock.yaml").read_text()
    assert "client_secret" not in lock_text
    assert "GITEA_CLIENT_SECRET" not in lock_text


def test_gitea_bootstrap_generates_uncommitted_runtime_oauth_secret() -> None:
    bootstrap = (GITEA_EXAMPLE / "gitea" / "bootstrap_oauth.py").read_text()
    env_example = (GITEA_EXAMPLE / ".env.example").read_text()

    assert "/api/v1/user/applications/oauth2" in bootstrap
    assert "client_secret" in bootstrap
    assert "/run/atlas-auth/gitea.env" in bootstrap
    assert "http://localhost:18080/auth/browser/v1/providers/" in bootstrap
    assert "GITEA_CLIENT_SECRET=" not in env_example


def test_gitea_compose_is_isolated_pinned_and_health_gated() -> None:
    compose = yaml.safe_load((GITEA_EXAMPLE / "compose.yaml").read_text())

    assert compose["name"] == "atlas-auth-oauth2-gitea"
    assert set(compose["services"]) == {
        "postgres",
        "gitea",
        "gitea-users",
        "oauth-bootstrap",
        "initializer",
        "backend",
        "frontend",
    }
    assert compose["services"]["gitea"]["image"] == "gitea/gitea:1.27.3"
    assert compose["services"]["gitea"]["healthcheck"]
    assert compose["services"]["gitea-users"]["depends_on"]["gitea"] == {
        "condition": "service_healthy"
    }
    assert compose["services"]["oauth-bootstrap"]["depends_on"]["gitea-users"] == {
        "condition": "service_completed_successfully"
    }
    assert compose["services"]["initializer"]["depends_on"]["oauth-bootstrap"] == {
        "condition": "service_completed_successfully"
    }
    assert compose["networks"]["database"]["internal"] is True
    assert (
        "gitea-runtime-secrets:/run/atlas-auth:ro"
        in compose["services"]["backend"]["volumes"]
    )


def test_gitea_browser_smoke_covers_required_journey() -> None:
    smoke = (GITEA_EXAMPLE / "browser_smoke.py").read_text()

    assert "/providers/{PROVIDER_ID}/start" in smoke
    assert 'consent_values["granted"] = "true"' in smoke
    assert 'state["subject"].isdigit()' in smoke
    assert 'state["providerGrants"] == 0' in smoke
    assert 'state["isStaff"] is False' in smoke
    assert 'state["isSuperuser"] is False' in smoke
    assert "expected=403" in smoke
    assert "/auth/browser/v1/session" in smoke
    assert "assert atlas_state(env_file, username) == state" in smoke


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is unavailable")
def test_gitea_authentication_compose_renders() -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            ".env.example",
            "-f",
            "compose.yaml",
            "config",
            "--quiet",
        ],
        cwd=GITEA_EXAMPLE,
        check=True,
        capture_output=True,
        text=True,
    )


def test_custom_credential_example_selects_fixture_and_local_fallback() -> None:
    manifest = load_manifest(CUSTOM_EXAMPLE / "manifest.yaml")
    lock = load_lock(CUSTOM_EXAMPLE / "lock.yaml")

    assert [provider.id for provider in manifest.auth.providers] == [
        "example.auth.fixture",
        "atlas.auth.local",
    ]
    fixture = manifest.auth.providers[0]
    assert manifest.auth.default == "example.auth.fixture"
    assert fixture.principal_provisioning == "automatic"
    assert fixture.actor_provisioning == "automatic"
    assert fixture.group_sync.mode == "exact"
    assert fixture.group_sync.mappings == {"fixture-platform": "custom-platform"}
    assert [provider.id for provider in lock.auth.providers] == [
        "example.auth.fixture",
        "atlas.auth.local",
    ]
    locked_plugin = lock.plugins["example.auth.fixture@0.1.0"]
    assert locked_plugin.config["fixturePassword"] == {
        "fromEnv": "ATLAS_FIXTURE_PASSWORD"
    }
    lock_text = (CUSTOM_EXAMPLE / "lock.yaml").read_text()
    assert "fixture-only-9Cedar-Sky-4" not in lock_text


def test_custom_credential_compose_is_minimal_and_isolated() -> None:
    compose = yaml.safe_load((CUSTOM_EXAMPLE / "compose.yaml").read_text())

    assert compose["name"] == "atlas-auth-custom-credentials"
    assert set(compose["services"]) == {
        "postgres",
        "initializer",
        "backend",
        "frontend",
    }
    assert compose["services"]["postgres"]["volumes"] == [
        "custom-credentials-postgres-data:/var/lib/postgresql/data"
    ]
    assert compose["networks"]["database"]["internal"] is True
    assert "openldap" not in (CUSTOM_EXAMPLE / "compose.yaml").read_text().lower()


def test_custom_credential_ldap_mapping_uses_public_v1_contract_only() -> None:
    mapping = (CUSTOM_EXAMPLE / "LDAP-MAPPING.md").read_text()
    package = CUSTOM_EXAMPLE / "plugin"

    for public_type in (
        "CredentialAuthenticationProvider",
        "CredentialFlowContext",
        "CredentialInput",
        "VerifiedIdentity",
        "AssuredAttribute",
        "ExternalGroupSnapshot",
        "AuthenticationFailure",
    ):
        assert public_type in mapping
    assert "atlas_plugin_api" in mapping
    assert not any("ldap" in path.name.lower() for path in package.rglob("*"))


def test_custom_credential_smoke_covers_required_journey() -> None:
    smoke = (CUSTOM_EXAMPLE / "smoke.py").read_text()

    assert '"fixture-alice", "", expected=400' in smoke
    assert "does-not-exist" in smoke
    assert "fixture-provider-outage" in smoke
    assert "LOCAL_PROVIDER" in smoke
    assert '"groups": ["custom-platform"]' in smoke
    assert "finiteExpiry" in smoke
    assert "fixture-groups-unavailable" in smoke
    assert "expected=403" in smoke
    assert "fixture_password not in logs" in smoke
    assert "/auth/browser/v1/session" in smoke


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is unavailable")
def test_custom_credential_compose_renders() -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            ".env.example",
            "-f",
            "compose.yaml",
            "config",
            "--quiet",
        ],
        cwd=CUSTOM_EXAMPLE,
        check=True,
        capture_output=True,
        text=True,
    )
