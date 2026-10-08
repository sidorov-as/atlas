"""Static composition-validation tests (`composition-validation` spec) —
one synthetic-fixture test per failure mode, independent of any real
plugin package."""

import pytest
from atlas_plugin_api import PluginConfigSchema, PluginDescriptor, SecretRef

from atlas_composer.composition import (
    ArtifactVersionMismatchError,
    DependencyCycleError,
    DuplicatePluginIdError,
    IncompatibleCoreRangeError,
    InvalidAuthenticationSelectionError,
    InvalidPluginConfigError,
    InvalidSearchEngineSelectionError,
    MissingDependencyError,
    check_authentication_selection,
    check_backend_frontend_versions_match,
    check_core_compatibility,
    check_dependencies,
    check_no_dependency_cycle,
    check_no_duplicate_plugin_ids,
    check_plugin_config,
    check_search_engine_selection,
    validate_composition,
)
from atlas_composer.lock import (
    Lock,
    LockedBackendArtifact,
    LockedFrontendArtifact,
    LockedPlugin,
)
from atlas_composer.manifest import Manifest


def _manifest(*plugins: dict, core_version: str = "0.5.0") -> Manifest:
    return Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": core_version},
            "plugins": list(plugins),
            "auth": {
                "providers": [{"id": "atlas.auth.local"}],
                "default": "atlas.auth.local",
            },
        }
    )


def _plugin_entry(
    plugin_id: str,
    version: str = "0.1.0",
    *,
    config: dict | None = None,
) -> dict:
    suffix = plugin_id.split(".")[-1]
    entry = {
        "id": plugin_id,
        "version": version,
        "backend": {
            "package": f"atlas-plugin-{suffix}",
            "source": "workspace",
        },
    }
    if config is not None:
        entry["config"] = config
    return entry


def _descriptor(
    plugin_id: str,
    *,
    compatibility: dict[str, str] | None = None,
    requires_plugins: dict[str, str] | None = None,
    config_schema: type[PluginConfigSchema] | None = None,
) -> PluginDescriptor:
    return PluginDescriptor(
        id=plugin_id,
        version="0.1.0",
        compatibility=compatibility or {},
        django_apps=(),
        entry_point=f"{plugin_id}.plugin:PLUGIN",
        requires_plugins=requires_plugins or {},
        config_schema=config_schema,
    )


def _empty_lock() -> Lock:
    return Lock.model_validate(
        {
            "distribution": "company.atlas@2026.08",
            "core": "0.5.0",
            "plugins": {},
            "auth": {
                "providers": [
                    {
                        "id": "atlas.auth.local",
                        "owner": "atlas.catalog",
                        "contractVersion": "atlas.auth.providers.v1",
                        "flowKind": "credentials",
                        "remoteLogout": "unsupported",
                        "presentation": {
                            "displayName": "Username and password",
                            "credentialFields": [
                                {"id": "username", "label": "Username", "kind": "text"},
                                {
                                    "id": "password",
                                    "label": "Password",
                                    "kind": "secret",
                                },
                            ],
                        },
                        "principalProvisioning": "preprovisioned",
                        "actorProvisioning": "manual",
                        "profileFields": [],
                        "groupSync": {"mode": "none"},
                    }
                ],
                "default": "atlas.auth.local",
            },
        }
    )


def _locked_plugin(backend_version: str, frontend_version: str) -> LockedPlugin:
    return LockedPlugin(
        backend=LockedBackendArtifact(
            package="atlas-plugin-apis",
            version=backend_version,
        ),
        frontend=LockedFrontendArtifact(
            package="@atlas/plugin-apis",
            version=frontend_version,
        ),
    )


def test_check_no_duplicate_plugin_ids_passes_for_distinct_ids():
    manifest = _manifest(_plugin_entry("atlas.apis"), _plugin_entry("atlas.c4"))

    check_no_duplicate_plugin_ids(manifest)  # must not raise


def test_check_no_duplicate_plugin_ids_rejects_a_repeated_id():
    manifest = _manifest(
        _plugin_entry("atlas.apis"),
        _plugin_entry("atlas.apis"),
    )

    with pytest.raises(DuplicatePluginIdError) as exc_info:
        check_no_duplicate_plugin_ids(manifest)

    assert exc_info.value.plugin_id == "atlas.apis"


def test_check_backend_frontend_versions_match_passes_when_equal():
    lock = Lock(
        distribution="company.atlas@2026.08",
        core="0.5.0",
        plugins={
            "atlas.apis@0.1.0": _locked_plugin("0.1.0", "0.1.0"),
        },
    )

    check_backend_frontend_versions_match(lock)  # must not raise


def test_check_backend_frontend_versions_match_rejects_a_mismatch():
    lock = Lock(
        distribution="company.atlas@2026.08",
        core="0.5.0",
        plugins={
            "atlas.apis@0.1.0": _locked_plugin("0.1.0", "0.2.0"),
        },
    )

    with pytest.raises(ArtifactVersionMismatchError) as exc_info:
        check_backend_frontend_versions_match(lock)

    assert exc_info.value.key == "atlas.apis@0.1.0"


def test_check_core_compatibility_passes_when_in_range():
    manifest = _manifest(_plugin_entry("atlas.c4"))
    descriptors = {
        "atlas.c4": _descriptor(
            "atlas.c4",
            compatibility={"atlasCore": ">=0.1 <1"},
        )
    }

    check_core_compatibility(manifest, descriptors)  # must not raise


def test_check_core_compatibility_rejects_a_range_the_core_version_fails():
    manifest = _manifest(_plugin_entry("atlas.c4"), core_version="2.0.0")
    descriptors = {
        "atlas.c4": _descriptor(
            "atlas.c4",
            compatibility={"atlasCore": ">=0.1 <1"},
        )
    }

    with pytest.raises(IncompatibleCoreRangeError) as exc_info:
        check_core_compatibility(manifest, descriptors)

    assert exc_info.value.plugin_id == "atlas.c4"
    assert exc_info.value.core_version == "2.0.0"


def test_check_dependencies_passes_when_the_required_plugin_is_selected():
    manifest = _manifest(
        _plugin_entry("atlas.c4"),
        _plugin_entry("atlas.standard-catalog"),
    )
    descriptors = {
        "atlas.c4": _descriptor(
            "atlas.c4",
            requires_plugins={"atlas.standard-catalog": ">=0.1 <1"},
        )
    }

    check_dependencies(manifest, descriptors)  # must not raise


def test_check_dependencies_rejects_a_missing_required_plugin():
    manifest = _manifest(_plugin_entry("atlas.c4"))
    descriptors = {
        "atlas.c4": _descriptor(
            "atlas.c4",
            requires_plugins={"atlas.standard-catalog": ">=0.1 <1"},
        )
    }

    with pytest.raises(MissingDependencyError) as exc_info:
        check_dependencies(manifest, descriptors)

    assert exc_info.value.plugin_id == "atlas.c4"
    assert exc_info.value.missing == frozenset({"atlas.standard-catalog"})


def test_check_no_dependency_cycle_passes_for_an_acyclic_graph():
    manifest = _manifest(
        _plugin_entry("atlas.c4"),
        _plugin_entry("atlas.standard-catalog"),
    )
    descriptors = {
        "atlas.c4": _descriptor(
            "atlas.c4",
            requires_plugins={"atlas.standard-catalog": ">=0.1 <1"},
        ),
        "atlas.standard-catalog": _descriptor("atlas.standard-catalog"),
    }

    check_no_dependency_cycle(manifest, descriptors)  # must not raise


def test_check_no_dependency_cycle_rejects_a_two_plugin_cycle():
    manifest = _manifest(_plugin_entry("atlas.a"), _plugin_entry("atlas.b"))
    descriptors = {
        "atlas.a": _descriptor(
            "atlas.a",
            requires_plugins={"atlas.b": ">=0.1 <1"},
        ),
        "atlas.b": _descriptor(
            "atlas.b",
            requires_plugins={"atlas.a": ">=0.1 <1"},
        ),
    }

    with pytest.raises(DependencyCycleError) as exc_info:
        check_no_dependency_cycle(manifest, descriptors)

    assert set(exc_info.value.cycle) == {"atlas.a", "atlas.b"}


class _OIDCConfig(PluginConfigSchema):
    issuer: str
    client_secret: str | SecretRef


def test_check_plugin_config_passes_for_a_valid_config():
    manifest = _manifest(
        _plugin_entry(
            "atlas.auth.oidc",
            config={
                "issuer": "https://id.example.com",
                "client_secret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
            },
        )
    )
    descriptors = {
        "atlas.auth.oidc": _descriptor(
            "atlas.auth.oidc",
            config_schema=_OIDCConfig,
        )
    }

    check_plugin_config(manifest, descriptors)  # must not raise


def test_check_plugin_config_rejects_an_invalid_config():
    manifest = _manifest(
        _plugin_entry(
            "atlas.auth.oidc",
            config={
                "issuer": "https://id.example.com",
            },
        )
    )
    descriptors = {
        "atlas.auth.oidc": _descriptor(
            "atlas.auth.oidc",
            config_schema=_OIDCConfig,
        )
    }

    with pytest.raises(InvalidPluginConfigError) as exc_info:
        check_plugin_config(manifest, descriptors)

    assert exc_info.value.plugin_id == "atlas.auth.oidc"


def test_check_plugin_config_rejects_an_unknown_field():
    manifest = _manifest(
        _plugin_entry(
            "atlas.auth.oidc",
            config={
                "issuer": "https://id.example.com",
                "client_secret": "literal",
                "unexpectedField": True,
            },
        )
    )
    descriptors = {
        "atlas.auth.oidc": _descriptor(
            "atlas.auth.oidc",
            config_schema=_OIDCConfig,
        )
    }

    with pytest.raises(InvalidPluginConfigError):
        check_plugin_config(manifest, descriptors)


def test_check_plugin_config_skips_a_plugin_without_a_config_schema():
    manifest = _manifest(_plugin_entry("atlas.c4"))
    descriptors = {"atlas.c4": _descriptor("atlas.c4")}

    check_plugin_config(manifest, descriptors)  # must not raise


def test_validate_composition_passes_for_a_consistent_manifest_and_lock():
    manifest = _manifest(_plugin_entry("atlas.standard-catalog"))
    descriptors = {
        "atlas.standard-catalog": _descriptor(
            "atlas.standard-catalog",
            compatibility={"atlasCore": ">=0.1 <1"},
        )
    }

    validate_composition(manifest, _empty_lock(), descriptors)  # must not raise


def test_validate_composition_runs_the_duplicate_id_check_first():
    manifest = _manifest(
        _plugin_entry("atlas.apis"),
        _plugin_entry("atlas.apis"),
    )

    with pytest.raises(DuplicatePluginIdError):
        validate_composition(manifest, _empty_lock())


def test_auth_selection_rejects_empty_legacy_default_with_migration_guidance():
    manifest = Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "0.5.0"},
        }
    )

    with pytest.raises(
        InvalidAuthenticationSelectionError,
        match="select at least one provider.*atlas.auth.local",
    ):
        check_authentication_selection(
            manifest,
            Lock(
                distribution="company.atlas@2026.08",
                core="0.5.0",
                plugins={},
            ),
            {},
        )


def test_auth_selection_rejects_duplicate_provider_ids():
    manifest = _manifest()
    manifest = Manifest.model_validate(
        {
            **manifest.model_dump(),
            "auth": {
                "providers": [
                    {"id": "atlas.auth.local"},
                    {"id": "atlas.auth.local"},
                ],
                "default": "atlas.auth.local",
            },
        }
    )

    with pytest.raises(
        InvalidAuthenticationSelectionError,
        match="duplicate provider ids",
    ):
        check_authentication_selection(manifest, _empty_lock(), {})


def test_auth_selection_rejects_unselected_default():
    manifest = _manifest()
    manifest = Manifest.model_validate(
        {
            **manifest.model_dump(),
            "auth": {
                "providers": [{"id": "atlas.auth.local"}],
                "default": "atlas.auth.missing",
            },
        }
    )

    with pytest.raises(
        InvalidAuthenticationSelectionError,
        match="default provider.*not selected",
    ):
        check_authentication_selection(manifest, _empty_lock(), {})


def _search_manifest(*extra: dict, engine: str | None = None, search_extra=None):
    config = {"engine": engine} if engine is not None else None
    search = _plugin_entry("atlas.search", config=config)
    search.update(search_extra or {})
    return _manifest(search, *extra)


def test_search_engine_check_passes_without_search_or_engine_setting():
    check_search_engine_selection(_manifest(_plugin_entry("atlas.search-postgres")))
    check_search_engine_selection(_search_manifest())
    check_search_engine_selection(
        _search_manifest(_plugin_entry("atlas.search-postgres"))
    )


def test_search_engine_check_passes_for_a_selected_engine_plugin():
    check_search_engine_selection(
        _search_manifest(
            _plugin_entry("atlas.search-postgres"),
            _plugin_entry("atlas.search-meili"),
            engine="atlas.search-meili",
        )
    )


def test_search_engine_check_rejects_an_engine_missing_from_the_manifest():
    with pytest.raises(InvalidSearchEngineSelectionError, match="not in the manifest"):
        check_search_engine_selection(
            _search_manifest(
                _plugin_entry("atlas.search-postgres"), engine="atlas.search-meili"
            )
        )


def test_search_engine_check_rejects_a_disabled_engine_plugin():
    disabled = _plugin_entry("atlas.search-postgres")
    disabled["disabled"] = True
    with pytest.raises(InvalidSearchEngineSelectionError, match="disabled") as excinfo:
        check_search_engine_selection(
            _search_manifest(disabled, engine="atlas.search-postgres")
        )
    assert excinfo.value.engine_plugin_id == "atlas.search-postgres"


def test_search_engine_check_rejects_an_engine_without_backend():
    frontend_only = {
        "id": "atlas.search-postgres",
        "version": "0.1.0",
        "frontend": {"package": "atlas-search-postgres", "source": "workspace"},
    }
    with pytest.raises(InvalidSearchEngineSelectionError, match="no backend"):
        check_search_engine_selection(
            _search_manifest(frontend_only, engine="atlas.search-postgres")
        )


def test_search_engine_check_ignores_a_disabled_search_plugin():
    check_search_engine_selection(
        _search_manifest(engine="atlas.search-meili", search_extra={"disabled": True})
    )
