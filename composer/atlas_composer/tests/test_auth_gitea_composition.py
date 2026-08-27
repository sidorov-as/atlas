from pathlib import Path

import pytest
from atlas_plugin_auth_gitea.plugin import PLUGIN, PROVIDER_ID

from atlas_composer.composition import (
    InvalidAuthenticationSelectionError,
    check_authentication_selection,
    check_plugin_config,
)
from atlas_composer.manifest import Manifest
from atlas_composer.resolver import resolve_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _manifest(*, select_gitea: bool = True, group_mode: str = "none"):
    providers = (
        [
            {
                "id": PROVIDER_ID,
                "principalProvisioning": "automatic",
                "actorProvisioning": "automatic",
                "profileFields": ["username", "displayName", "email"],
                "groupSync": {"mode": group_mode},
                "sourceBinding": {
                    "sourceId": "https://gitea.example",
                    "configurationFingerprint": "sha256:gitea-test",
                },
            }
        ]
        if select_gitea
        else [{"id": "atlas.auth.local"}]
    )
    return Manifest.model_validate(
        {
            "distribution": {"id": "test.gitea", "version": "2026.09"},
            "core": {"version": "0.1.0"},
            "plugins": [
                {
                    "id": PROVIDER_ID,
                    "version": "0.1.0",
                    "backend": {
                        "package": "atlas-plugin-auth-gitea",
                        "source": "workspace",
                    },
                    "config": {
                        "instanceOrigin": "https://gitea.example",
                        "clientId": "atlas-client",
                        "clientSecret": {"fromEnv": "ATLAS_GITEA_CLIENT_SECRET"},
                        "scopes": ["read:user"],
                        "oauthPkceEnabled": True,
                    },
                }
            ],
            "auth": {
                "providers": providers,
                "default": PROVIDER_ID if select_gitea else "atlas.auth.local",
                "publicOrigin": "https://atlas.example",
                "outboundTrust": {"allowedDestinations": ["https://gitea.example"]},
            },
        }
    )


def test_selected_configured_gitea_is_locked_as_redirect_provider():
    manifest = _manifest()
    descriptors = {PROVIDER_ID: PLUGIN}

    check_plugin_config(manifest, descriptors)
    lock = resolve_manifest(manifest, repo_root=REPO_ROOT, descriptors=descriptors)
    check_authentication_selection(manifest, lock, descriptors)

    assert [provider.id for provider in lock.auth.providers] == [PROVIDER_ID]
    provider = lock.auth.providers[0]
    assert provider.owner == PROVIDER_ID
    assert provider.flow_kind == "redirect"
    assert provider.group_sync.mode == "none"
    assert provider.source_binding.source_id == "https://gitea.example"
    assert "ATLAS_GITEA_CLIENT_SECRET" not in repr(lock.auth)


def test_installed_but_unselected_gitea_is_absent_from_auth_lock():
    manifest = _manifest(select_gitea=False)
    descriptors = {PROVIDER_ID: PLUGIN}

    lock = resolve_manifest(manifest, repo_root=REPO_ROOT, descriptors=descriptors)

    assert [provider.id for provider in lock.auth.providers] == ["atlas.auth.local"]


@pytest.mark.parametrize("mode", ["additive", "exact"])
def test_composition_rejects_gitea_group_synchronization(mode):
    manifest = _manifest(group_mode=mode)
    descriptors = {PROVIDER_ID: PLUGIN}
    lock = resolve_manifest(manifest, repo_root=REPO_ROOT, descriptors=descriptors)

    with pytest.raises(
        InvalidAuthenticationSelectionError,
        match=r"atlas\.auth\.gitea.*does not support.*groupSync",
    ):
        check_authentication_selection(manifest, lock, descriptors)


def test_composition_rejects_gitea_source_rebinding():
    data = _manifest().model_dump(by_alias=True)
    data["auth"]["providers"][0]["sourceBinding"]["sourceId"] = (
        "https://replacement.example"
    )
    manifest = Manifest.model_validate(data)
    descriptors = {PROVIDER_ID: PLUGIN}
    lock = resolve_manifest(manifest, repo_root=REPO_ROOT, descriptors=descriptors)

    with pytest.raises(
        InvalidAuthenticationSelectionError,
        match=r"sourceBinding\.sourceId must match configured instance_origin",
    ):
        check_authentication_selection(manifest, lock, descriptors)
