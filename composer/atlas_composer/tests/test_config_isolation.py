"""Secret-leak regression tests: the composer never resolves a `fromEnv` secret reference itself
(`atlas_plugin_api.config.resolve_secrets` is Core's job, at deploy time,
not the composer's, at build time), so no composer-produced artifact — the
lock file or the generated frontend composition module — can carry a
resolved secret value in the first place. These tests pin that guarantee: a
manifest declaring a plugin config with a `fromEnv` secret reference (and,
as a defense-in-depth check, one with a literal secret value) never has
that value surface in the lock file's YAML or the generated frontend
composition module's source, however the composer's build pipeline is
driven end to end.
"""

import pytest

from atlas_composer.generate import (
    render_composition_module,
    render_selected_plugins_module,
)
from atlas_composer.lock import (
    Lock,
    LockedBackendArtifact,
    LockedFrontendArtifact,
    LockedPlugin,
    dump_lock,
)
from atlas_composer.manifest import Manifest

_SECRET_LITERAL = "sekret-do-not-leak-1234567890"


def _manifest_with_oidc_secret(*, literal: bool = False) -> Manifest:
    client_secret = (
        _SECRET_LITERAL if literal else {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"}
    )
    return Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "0.5.0"},
            "plugins": [
                {
                    "id": "atlas.auth.oidc",
                    "version": "0.1.0",
                    "backend": {
                        "package": "atlas-plugin-auth-oidc",
                        "source": "workspace",
                    },
                    "frontend": {
                        "package": "@atlas/plugin-auth-oidc",
                        "source": "workspace",
                    },
                    "config": {
                        "issuer": "https://id.example.com",
                        "clientId": "atlas",
                        "clientSecret": client_secret,
                    },
                }
            ],
        }
    )


def _lock_for(manifest: Manifest) -> Lock:
    """A lock the composer would produce for `manifest` — built directly
    (bypassing `resolve_manifest`'s workspace-lock-file resolution, which
    is exercised elsewhere) since what's under test is that `Lock`'s own
    schema and `generate.py`'s rendering never see a plugin's `config`
    block at all, regardless of how the lock was produced."""
    entry = manifest.plugins[0]
    return Lock(
        distribution=f"{manifest.distribution.id}@{manifest.distribution.version}",
        core=manifest.core.version,
        plugins={
            f"{entry.id}@{entry.version}": LockedPlugin(
                backend=LockedBackendArtifact(
                    package=entry.backend.package,
                    version=entry.version,
                    hash="sha256:x",
                ),
                frontend=LockedFrontendArtifact(
                    package=entry.frontend.package,
                    version=entry.version,
                    integrity="sha512-x",
                ),
            ),
        },
    )


@pytest.mark.parametrize("literal", [False, True])
def test_dumped_lock_yaml_never_contains_the_secret(tmp_path, literal):
    manifest = _manifest_with_oidc_secret(literal=literal)
    lock = _lock_for(manifest)
    lock_path = tmp_path / "lock.yaml"

    dump_lock(lock, lock_path)

    assert _SECRET_LITERAL not in lock_path.read_text()


def test_generated_frontend_composition_module_never_contains_the_secret():
    manifest = _manifest_with_oidc_secret(literal=True)
    lock = _lock_for(manifest)

    rendered = render_composition_module(lock)

    assert _SECRET_LITERAL not in rendered


def test_generated_backend_selected_plugins_module_never_contains_the_secret():
    manifest = _manifest_with_oidc_secret(literal=True)
    lock = _lock_for(manifest)

    rendered = render_selected_plugins_module(lock)

    assert _SECRET_LITERAL not in rendered


def test_locked_plugin_keeps_only_unresolved_secret_reference_out_of_repr():
    plugin = LockedPlugin.model_validate(
        {
            "backend": {
                "package": "atlas-plugin-auth-oidc",
                "version": "0.1.0",
                "hash": "sha256:x",
            },
            "config": {
                "clientSecret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
            },
        }
    )

    assert plugin.config["clientSecret"] == {
        "fromEnv": "ATLAS_OIDC_CLIENT_SECRET",
    }
    assert "clientSecret" not in repr(plugin)
    assert _SECRET_LITERAL not in repr(plugin)
