"""Deployment manifest schema tests (`deployment-manifest-and-lock` spec)."""

import pytest
from pydantic import ValidationError

from atlas_composer.manifest import Manifest, load_manifest

EXAMPLE_MANIFEST_YAML = """
distribution:
  id: company.atlas
  version: "2026.08"

core:
  version: 3.2.0

plugins:
  - id: atlas.standard-catalog
    version: 2.3.1
    backend:
      package: atlas-plugin-standard-catalog
      source: python-private
    frontend:
      package: "@atlas/plugin-standard-catalog"
      source: npm-private

auth:
  providers:
    - id: atlas.auth.local
      signup: disabled
      principalProvisioning: preprovisioned
      actorProvisioning: manual
    - id: atlas.auth.oidc
      principalProvisioning: automatic
      actorProvisioning: automatic
      profileFields: [username, displayName, email]
      sourceBinding:
        sourceId: https://id.example.com
        configurationFingerprint: sha256:example
  default: atlas.auth.local

ui:
  disable: [atlas.ingestion]
  order: [atlas.standard-catalog, atlas.apis]
"""


def test_load_manifest_parses_the_documented_example(tmp_path):
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(EXAMPLE_MANIFEST_YAML)

    manifest = load_manifest(manifest_path)

    assert manifest.distribution.id == "company.atlas"
    assert manifest.distribution.version == "2026.08"
    assert manifest.core.version == "3.2.0"
    assert len(manifest.plugins) == 1
    entry = manifest.plugins[0]
    assert entry.id == "atlas.standard-catalog"
    assert entry.version == "2.3.1"
    assert entry.backend.package == "atlas-plugin-standard-catalog"
    assert entry.backend.source == "python-private"
    assert entry.frontend.package == "@atlas/plugin-standard-catalog"
    assert tuple(provider.id for provider in manifest.auth.providers) == (
        "atlas.auth.local",
        "atlas.auth.oidc",
    )
    assert manifest.auth.default == "atlas.auth.local"
    assert manifest.ui.disable == ("atlas.ingestion",)
    assert manifest.ui.order == ("atlas.standard-catalog", "atlas.apis")


def test_manifest_defaults_auth_and_ui_when_omitted():
    manifest = Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "3.2.0"},
        }
    )

    assert manifest.plugins == ()
    assert manifest.auth.providers == ()
    assert manifest.auth.default is None
    assert manifest.ui.disable == ()
    assert manifest.ui.order == ()


def test_manifest_rejects_legacy_string_only_auth_selection():
    with pytest.raises(ValidationError, match="legacy auth.providers string"):
        Manifest.model_validate(
            {
                "distribution": {"id": "company.atlas", "version": "2026.08"},
                "core": {"version": "3.2.0"},
                "auth": {
                    "providers": ["atlas.auth.local"],
                    "default": "atlas.auth.local",
                },
            }
        )


@pytest.mark.parametrize("value", [0, -1])
def test_manifest_rejects_non_positive_session_lifetime(value):
    with pytest.raises(ValidationError, match="greater than 0"):
        Manifest.model_validate(
            {
                "distribution": {"id": "company.atlas", "version": "2026.08"},
                "core": {"version": "3.2.0"},
                "auth": {"sessionMaxAgeSeconds": value},
            }
        )


def test_manifest_requires_break_glass_allowlist():
    with pytest.raises(ValidationError, match="requires principalIds"):
        Manifest.model_validate(
            {
                "distribution": {"id": "company.atlas", "version": "2026.08"},
                "core": {"version": "3.2.0"},
                "auth": {"adminPassword": {"mode": "break-glass"}},
            }
        )


def test_manifest_rejects_production_plaintext_origins():
    with pytest.raises(ValidationError, match="must use HTTPS"):
        Manifest.model_validate(
            {
                "distribution": {"id": "company.atlas", "version": "2026.08"},
                "core": {"version": "3.2.0"},
                "auth": {"publicOrigin": "http://atlas.example"},
            }
        )


def test_exact_group_sync_records_complete_snapshot_and_finite_freshness():
    manifest = Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "3.2.0"},
            "auth": {
                "providers": [
                    {
                        "id": "example.auth.oidc",
                        "groupSync": {"mode": "exact", "maxAgeSeconds": 600},
                    }
                ],
                "default": "example.auth.oidc",
            },
        }
    )

    group_sync = manifest.auth.providers[0].group_sync
    assert group_sync.snapshot_requirement == "required"
    assert group_sync.max_age_seconds == 600


def test_plaintext_fixture_destination_requires_explicit_development_opt_in():
    with pytest.raises(ValidationError, match="allowDevelopmentHttp=true"):
        Manifest.model_validate(
            {
                "distribution": {"id": "company.atlas", "version": "2026.08"},
                "core": {"version": "3.2.0"},
                "auth": {
                    "outboundTrust": {
                        "allowedDestinations": ["http://localhost:8080"],
                    }
                },
            }
        )


def test_plugin_entry_requires_a_backend_or_frontend_artifact():
    with pytest.raises(
        ValidationError,
        match="neither a backend nor a frontend",
    ):
        Manifest.model_validate(
            {
                "distribution": {"id": "company.atlas", "version": "2026.08"},
                "core": {"version": "3.2.0"},
                "plugins": [{"id": "atlas.apis", "version": "1.0.0"}],
            }
        )


def test_plugin_entry_may_be_backend_only():
    manifest = Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "3.2.0"},
            "plugins": [
                {
                    "id": "atlas.ingestion",
                    "version": "1.0.0",
                    "backend": {
                        "package": "atlas-plugin-ingestion",
                        "source": "workspace",
                    },
                }
            ],
        }
    )

    assert manifest.plugins[0].frontend is None


def test_manifest_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        Manifest.model_validate(
            {
                "distribution": {"id": "company.atlas", "version": "2026.08"},
                "core": {"version": "3.2.0"},
                "unknownField": True,
            }
        )


def test_plugin_entry_defaults_config_to_empty():
    manifest = Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "3.2.0"},
            "plugins": [
                {
                    "id": "atlas.ingestion",
                    "version": "1.0.0",
                    "backend": {
                        "package": "atlas-plugin-ingestion",
                        "source": "workspace",
                    },
                }
            ],
        }
    )

    assert manifest.plugins[0].config == {}


def test_outbound_trust_accepts_localhost_subdomain_fixture():
    manifest = Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "3.2.0"},
            "auth": {
                "outboundTrust": {
                    "allowedDestinations": ["http://keycloak.localhost:18081"],
                    "allowDevelopmentHttp": True,
                },
            },
        }
    )

    assert manifest.auth.outbound_trust.allowed_destinations == (
        "http://keycloak.localhost:18081",
    )


def test_plugin_entry_carries_a_raw_config_block():
    manifest = Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "3.2.0"},
            "plugins": [
                {
                    "id": "atlas.auth.oidc",
                    "version": "1.0.0",
                    "backend": {
                        "package": "atlas-plugin-auth-oidc",
                        "source": "workspace",
                    },
                    "config": {
                        "issuer": "https://id.example.com",
                        "clientId": "atlas",
                        "clientSecret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
                    },
                }
            ],
        }
    )

    assert manifest.plugins[0].config == {
        "issuer": "https://id.example.com",
        "clientId": "atlas",
        "clientSecret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
    }


def test_plugin_entry_defaults_disabled_to_false():
    manifest = Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "3.2.0"},
            "plugins": [
                {
                    "id": "atlas.ingestion",
                    "version": "1.0.0",
                    "backend": {
                        "package": "atlas-plugin-ingestion",
                        "source": "workspace",
                    },
                }
            ],
        }
    )

    assert manifest.plugins[0].disabled is False


def test_plugin_entry_may_be_marked_disabled():
    manifest = Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "3.2.0"},
            "plugins": [
                {
                    "id": "atlas.ingestion",
                    "version": "1.0.0",
                    "backend": {
                        "package": "atlas-plugin-ingestion",
                        "source": "workspace",
                    },
                    "disabled": True,
                }
            ],
        }
    )

    assert manifest.plugins[0].disabled is True


def test_plugin_artifact_rejects_unknown_source():
    with pytest.raises(ValidationError):
        Manifest.model_validate(
            {
                "distribution": {"id": "company.atlas", "version": "2026.08"},
                "core": {"version": "3.2.0"},
                "plugins": [
                    {
                        "id": "atlas.ingestion",
                        "version": "1.0.0",
                        "backend": {
                            "package": "atlas-plugin-ingestion",
                            "source": "ftp",
                        },
                    }
                ],
            }
        )
