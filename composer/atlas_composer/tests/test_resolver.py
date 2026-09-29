"""Manifest -> lock resolution tests (`deployment-manifest-and-lock` spec)."""

from pathlib import Path

import pytest
from atlas_plugin_api import (
    AuthenticationFlowKind,
    AuthenticationProviderContribution,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    PluginDescriptor,
)

from atlas_composer.manifest import Manifest
from atlas_composer.resolver import (
    UnknownPackageError,
    UnsupportedSourceError,
    VersionMismatchError,
    resolve_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _auth_descriptor(provider_id: str) -> PluginDescriptor:
    return PluginDescriptor(
        id="atlas.standard-catalog",
        version="0.1.0",
        compatibility={"atlasCore": ">=0.1 <4"},
        django_apps=(),
        entry_point="example.plugin:PLUGIN",
        authentication_providers=(
            AuthenticationProviderContribution(
                descriptor=AuthenticationProviderDescriptor(
                    id=provider_id,
                    flow_kind=AuthenticationFlowKind.REDIRECT,
                    presentation=AuthenticationProviderPresentation(
                        display_name="Example SSO",
                    ),
                ),
            ),
        ),
    )


def _manifest(**plugin_overrides) -> Manifest:
    plugin = {
        "id": "atlas.standard-catalog",
        "version": "0.1.0",
        "backend": {
            "package": "atlas-plugin-standard-catalog",
            "source": "workspace",
        },
        "frontend": {
            "package": "@atlas/plugin-standard-catalog",
            "source": "workspace",
        },
    }
    plugin.update(plugin_overrides)
    return Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "3.2.0"},
            "plugins": [plugin],
        }
    )


def test_resolve_manifest_names_the_lock_by_distribution_and_core():
    lock = resolve_manifest(_manifest(), repo_root=REPO_ROOT)

    assert lock.distribution == "company.atlas@2026.08"
    assert lock.core == "3.2.0"


def test_resolve_manifest_records_exact_backend_and_frontend_artifacts():
    lock = resolve_manifest(_manifest(), repo_root=REPO_ROOT)

    locked = lock.plugins["atlas.standard-catalog@0.1.0"]
    assert locked.backend.package == "atlas-plugin-standard-catalog"
    assert locked.backend.version == "0.1.0"
    assert locked.backend.hash.startswith("sha256:")
    assert locked.frontend.package == "@atlas/plugin-standard-catalog"
    assert locked.frontend.version == "0.1.0"
    assert locked.frontend.integrity.startswith("sha512-")


def test_resolve_manifest_preserves_unresolved_namespaced_plugin_config():
    manifest = _manifest(
        config={
            "fixturePassword": {"fromEnv": "ATLAS_FIXTURE_PASSWORD"},
        }
    )

    lock = resolve_manifest(manifest, repo_root=REPO_ROOT)

    assert lock.plugins["atlas.standard-catalog@0.1.0"].config == {
        "fixturePassword": {"fromEnv": "ATLAS_FIXTURE_PASSWORD"},
    }


def test_resolve_manifest_is_reproducible():
    first = resolve_manifest(_manifest(), repo_root=REPO_ROOT)
    second = resolve_manifest(_manifest(), repo_root=REPO_ROOT)

    assert first == second


def test_resolve_manifest_rejects_a_version_the_native_lock_disagrees_with():
    manifest = _manifest(version="9.9.9")

    with pytest.raises(VersionMismatchError):
        resolve_manifest(manifest, repo_root=REPO_ROOT)


def test_resolve_manifest_rejects_an_unknown_package():
    manifest = _manifest(
        backend={
            "package": "atlas-plugin-does-not-exist",
            "source": "workspace",
        }
    )

    with pytest.raises(UnknownPackageError):
        resolve_manifest(manifest, repo_root=REPO_ROOT)


def test_resolve_manifest_rejects_an_unsupported_source():
    manifest = _manifest(
        backend={
            "package": "atlas-plugin-standard-catalog",
            "source": "python-private",
        }
    )

    with pytest.raises(UnsupportedSourceError):
        resolve_manifest(manifest, repo_root=REPO_ROOT)


def test_resolve_manifest_propagates_disabled_into_the_lock():
    manifest = _manifest(disabled=True)

    lock = resolve_manifest(manifest, repo_root=REPO_ROOT)

    locked = lock.plugins["atlas.standard-catalog@0.1.0"]
    assert locked.disabled is True


def test_resolve_manifest_defaults_disabled_to_false_in_the_lock():
    lock = resolve_manifest(_manifest(), repo_root=REPO_ROOT)

    locked = lock.plugins["atlas.standard-catalog@0.1.0"]
    assert locked.disabled is False


def test_resolve_manifest_supports_a_backend_only_plugin():
    manifest = _manifest(
        id="atlas.ingestion",
        version="0.1.0",
        backend={"package": "atlas-plugin-ingestion", "source": "workspace"},
        frontend=None,
    )

    lock = resolve_manifest(manifest, repo_root=REPO_ROOT)

    locked = lock.plugins["atlas.ingestion@0.1.0"]
    assert locked.backend is not None
    assert locked.frontend is None


@pytest.mark.parametrize(
    "provider_id",
    [
        "atlas.auth.oidc",
        "example.auth.custom",
    ],
)
def test_resolve_manifest_locks_auth_policy_and_public_provider_metadata(
    provider_id,
):
    manifest = _manifest(
        config={
            "clientSecret": {"fromEnv": "ATLAS_TEST_SECRET"},
        }
    )
    manifest_data = manifest.model_dump()
    manifest_data["auth"] = {
        "providers": [
            {
                "id": provider_id,
                "principalProvisioning": "automatic",
                "actorProvisioning": "manual",
                "sourceBinding": {
                    "sourceId": "https://id.example.com",
                    "configurationFingerprint": "sha256:public-fingerprint",
                },
            }
        ],
        "default": provider_id,
        "publicOrigin": "https://atlas.example.com",
    }
    manifest = Manifest.model_validate(manifest_data)
    descriptor = _auth_descriptor(provider_id)

    lock = resolve_manifest(
        manifest,
        repo_root=REPO_ROOT,
        descriptors={"atlas.standard-catalog": descriptor},
    )

    assert [provider.id for provider in lock.auth.providers] == [
        provider_id,
    ]
    assert lock.auth.providers[0].flow_kind == "redirect"
    assert lock.auth.providers[0].presentation.display_name == "Example SSO"
    assert lock.auth.default == provider_id
    assert "ATLAS_TEST_SECRET" not in repr(lock)


def test_resolve_manifest_preserves_multi_provider_order():
    manifest = _manifest()
    manifest_data = manifest.model_dump()
    manifest_data["auth"] = {
        "providers": [
            {"id": "example.auth.custom"},
            {"id": "atlas.auth.local"},
        ],
        "default": "example.auth.custom",
    }
    manifest = Manifest.model_validate(manifest_data)

    lock = resolve_manifest(
        manifest,
        repo_root=REPO_ROOT,
        descriptors={
            "atlas.standard-catalog": _auth_descriptor("example.auth.custom"),
        },
    )

    assert [provider.id for provider in lock.auth.providers] == [
        "example.auth.custom",
        "atlas.auth.local",
    ]
