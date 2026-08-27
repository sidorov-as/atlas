"""Composition validation tests."""

import pytest
from atlas_plugin_api import authentication as authentication_module
from atlas_plugin_api.authentication import AuthenticationProviderRegistry

from server.apps.plugins.composition import (
    CompositionError,
    validate_composition,
)
from server.apps.plugins.permissions import registry as permission_registry
from server.apps.plugins.resolver import load_selected_descriptors


@pytest.fixture(autouse=True)
def _isolated_authentication_provider_registry(monkeypatch):
    """Runtime-hook tests must not reuse providers registered at app startup."""

    monkeypatch.setattr(
        authentication_module,
        "_authentication_provider_registry",
        AuthenticationProviderRegistry(),
    )


@pytest.fixture
def _clean_permission_registry():
    snapshot = dict(permission_registry._owners)
    yield
    permission_registry._owners.clear()
    permission_registry._owners.update(snapshot)


def test_validate_composition_passes_for_non_conflicting_plugins(
    _clean_permission_registry,
):
    descriptors = load_selected_descriptors(
        (
            "server.apps.plugins.tests.fixtures.plugin_no_hook",
            "server.apps.plugins.tests.fixtures.plugin_with_hook",
        )
    )

    # These fixture-only descriptors aren't meant to represent a full official
    # distribution, so the "atlas.standard-catalog is required" check
    # is opted out of here.
    validate_composition(
        descriptors, required_plugins=frozenset()
    )  # must not raise


def test_validate_composition_fails_when_two_plugins_claim_the_same_permission(
    _clean_permission_registry,
):
    descriptors = load_selected_descriptors(
        (
            "server.apps.plugins.tests.fixtures.plugin_permission_a",
            "server.apps.plugins.tests.fixtures.plugin_permission_b",
        )
    )

    with pytest.raises(CompositionError) as exc_info:
        validate_composition(descriptors, required_plugins=frozenset())

    message = str(exc_info.value)
    assert "fixture.shared.permission" in message
    assert "fixture.permission-a" in message
    assert "fixture.permission-b" in message


def test_validate_composition_fails_when_a_manifest_dependency_is_not_selected(
    _clean_permission_registry,
):
    """Composition fails if a selected plugin's declared dependency isn't
    satisfied."""
    descriptors = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_missing_dependency",)
    )

    with pytest.raises(CompositionError) as exc_info:
        validate_composition(descriptors, required_plugins=frozenset())

    message = str(exc_info.value)
    assert "fixture.needs-missing" in message
    assert "fixture.does-not-exist" in message


def test_validate_composition_passes_when_a_manifest_dependency_is_selected(
    _clean_permission_registry,
):
    from atlas_plugin_api import PluginDescriptor

    (needs_missing,) = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_missing_dependency",)
    )
    satisfying_dependency = PluginDescriptor(
        id="fixture.does-not-exist",
        version="1.0.0",
        compatibility={},
        django_apps=(),
        entry_point="server.apps.plugins.tests.fixtures.plugin_no_hook:PLUGIN",
    )

    validate_composition(
        (needs_missing, satisfying_dependency),
        required_plugins=frozenset(),
    )  # must not raise


def test_validate_composition_treats_a_disabled_dependency_as_still_satisfying(
    _clean_permission_registry,
):
    """A disabled plugin keeps its code installed:
    unlike `removed`, it still satisfies another
    plugin's `requires_plugins`."""
    from atlas_plugin_api import PluginDescriptor

    (needs_missing,) = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_missing_dependency",)
    )
    disabled_dependency = PluginDescriptor(
        id="fixture.does-not-exist",
        version="1.0.0",
        compatibility={},
        django_apps=(),
        entry_point="server.apps.plugins.tests.fixtures.plugin_no_hook:PLUGIN",
    )

    validate_composition(
        (needs_missing, disabled_dependency),
        required_plugins=frozenset(),
        disabled_ids=frozenset({"fixture.does-not-exist"}),
    )  # must not raise


def test_validate_composition_skips_registration_for_a_disabled_plugin(
    _clean_permission_registry,
):
    """A disabled plugin's contributions no longer register
    while its database tables and rows remain unchanged — the tables
    aren't exercised by this test (that's `resolve_installed_apps`, which
    doesn't take `disabled_ids` at all), just that registration is
    skipped."""
    from server.apps.plugins.tests.fixtures import plugin_with_hook

    plugin_with_hook.runtime_calls.clear()
    descriptors = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_with_hook",)
    )

    validate_composition(
        descriptors,
        required_plugins=frozenset(),
        disabled_ids=frozenset({"fixture.with-hook"}),
    )

    assert plugin_with_hook.runtime_calls == []


@pytest.mark.django_db
def test_boundary_composes_with_apis_deselected(
    _clean_permission_registry,
    monkeypatch,
):
    """A distribution without atlas.apis composes
    successfully — `atlas.apis` is
    optional, unlike
    `atlas.standard-catalog` (which stays selected and required here, so this
    exercises the real `composition.REQUIRED_PLUGINS` check too, not just the
    opted-out synthetic-fixture path the other tests in this module use).

    Runs the real runtime hooks against a throwaway registry (not the
    process-wide one, already populated by the real app startup this test
    session began with) so re-registering Standard Catalog's kinds here
    doesn't collide with that.

    `django_db`: this selection includes `atlas_plugin_ingestion.plugin`,
    whose descriptor now declares `job_ids` —
    `load_runtime_entry_points` resumes them, a real DB read/write.
    """
    import importlib

    import atlas_plugin_api.kinds as atlas_plugin_api_kinds_module
    from atlas_plugin_ingestion.extension_points import KeyedExtensionPoint

    import server.apps.catalog.kinds as kinds_package
    from server.apps.catalog.kinds.registry import EntityKindRegistry

    registry_module = importlib.import_module(
        "server.apps.catalog.kinds.registry"
    )
    ingestion_extension_points_module = importlib.import_module(
        "atlas_plugin_ingestion.extension_points",
    )

    fresh_registry = EntityKindRegistry()
    monkeypatch.setattr(kinds_package, "registry", fresh_registry)
    monkeypatch.setattr(registry_module, "registry", fresh_registry)
    # `register_kind()` resolves
    # `registry` as `atlas_plugin_api.kinds`'s own module global at call time —
    # the Core-side re-export patches above don't reach it, so it needs its
    # own patch too.
    monkeypatch.setattr(
        atlas_plugin_api_kinds_module, "registry", fresh_registry
    )
    # `atlas_plugin_ingestion.plugin.register_runtime()` also runs for real
    # here (it's in the descriptors below) — swap its own extension-point
    # registries too, same as the kind registry above, so re-registering
    # `GitHubConnector`/the YAML parser doesn't collide with the process-wide
    # ones already populated by the real app startup this test session
    # began with.
    monkeypatch.setattr(
        ingestion_extension_points_module,
        "connectors",
        KeyedExtensionPoint("atlas.ingestion.connectors.v1"),
    )
    monkeypatch.setattr(
        ingestion_extension_points_module,
        "parsers",
        KeyedExtensionPoint("atlas.ingestion.parsers.v1"),
    )
    # `atlas_plugin_standard_catalog.kinds.register_standard_catalog_kinds()`
    # registers a delete guard against `atlas_plugin_apis`'s
    # process-wide `DeleteGuardRegistry` whenever `atlas_plugin_apis` is
    # installed (real app startup's INSTALLED_APPS, independent of this
    # test's synthetic `descriptors` — `atlas.apis` deselected here doesn't
    # change that) — swap in a fresh one, same reason as the kind registry.
    from atlas_plugin_api import purge as purge_module
    from atlas_plugin_apis import (
        extension_points as apis_extension_points_module,
    )

    monkeypatch.setattr(
        apis_extension_points_module,
        "delete_guards",
        apis_extension_points_module.DeleteGuardRegistry(),
    )
    # `register_standard_catalog_kinds()` also registers a Purge reference
    # scanner against `atlas_plugin_api.purge`'s process-wide
    # `PurgeScannerRegistry`, and — when
    # `atlas.flows` is among the descriptors below — so does
    # `atlas_plugin_flows.plugin.register_runtime()`; swap in a fresh
    # registry, same reason as the kind/delete-guard registries.
    monkeypatch.setattr(
        purge_module, "purge_scanners", purge_module.PurgeScannerRegistry()
    )

    descriptors = load_selected_descriptors(
        (
            "server.apps.catalog.plugin",
            "atlas_plugin_ingestion.plugin",
            "atlas_plugin_standard_catalog.plugin",
        )
    )

    validate_composition(descriptors)  # real REQUIRED_PLUGINS; must not raise

    assert "api" not in fresh_registry.registered_ids()
    assert {"system", "component", "resource", "group", "user"} <= set(
        fresh_registry.registered_ids(),
    )


@pytest.mark.django_db
def test_boundary_composes_with_c4_deselected(monkeypatch):
    """A distribution without atlas.c4 composes successfully:
    `atlas.c4` is optional, unlike
    `atlas.standard-catalog` (which stays selected and required here, so this
    exercises the real `composition.REQUIRED_PLUGINS` check too, not just the
    opted-out synthetic-fixture path the other tests in this module use).

    Runs the real runtime hooks against throwaway registries (not the
    process-wide ones, already populated by the real app startup this test
    session began with, which does select `atlas.c4`) so this doesn't
    collide with that.

    `django_db`: this selection includes `atlas_plugin_ingestion.plugin`,
    whose descriptor now declares `job_ids` —
    `load_runtime_entry_points` resumes them, a real DB read/write.
    """
    import importlib

    import atlas_plugin_api.kinds as atlas_plugin_api_kinds_module
    import atlas_plugin_api.permissions as atlas_plugin_api_permissions
    from atlas_plugin_ingestion.extension_points import KeyedExtensionPoint

    import server.apps.catalog.kinds as kinds_package
    from server.apps.catalog.kinds.registry import EntityKindRegistry
    from server.apps.plugins import permissions as permissions_module
    from server.apps.plugins.permissions import PermissionRegistry

    kinds_registry_module = importlib.import_module(
        "server.apps.catalog.kinds.registry"
    )
    ingestion_extension_points_module = importlib.import_module(
        "atlas_plugin_ingestion.extension_points",
    )

    fresh_kind_registry = EntityKindRegistry()
    monkeypatch.setattr(kinds_package, "registry", fresh_kind_registry)
    monkeypatch.setattr(kinds_registry_module, "registry", fresh_kind_registry)
    # `register_kind()` resolves
    # `registry` as `atlas_plugin_api.kinds`'s own module global at call time —
    # the Core-side re-export patches above don't reach it, so it needs its
    # own patch too.
    monkeypatch.setattr(
        atlas_plugin_api_kinds_module, "registry", fresh_kind_registry
    )

    fresh_permission_registry = PermissionRegistry()
    monkeypatch.setattr(
        permissions_module, "registry", fresh_permission_registry
    )
    # `register_permission()`
    # resolves `registry` as `atlas_plugin_api.permissions`'s own module
    # global at call time — the Core-side re-export patch above doesn't
    # reach it, so it needs its own patch too, same as the kind registry.
    monkeypatch.setattr(
        atlas_plugin_api_permissions,
        "registry",
        fresh_permission_registry,
    )

    # `atlas_plugin_ingestion.plugin.register_runtime()` also runs for real
    # here (it's in the descriptors below) — swap its own extension-point
    # registries too, so re-registering `GitHubConnector`/the YAML parser
    # doesn't collide with the process-wide ones already populated by the
    # real app startup this test session began with.
    monkeypatch.setattr(
        ingestion_extension_points_module,
        "connectors",
        KeyedExtensionPoint("atlas.ingestion.connectors.v1"),
    )
    monkeypatch.setattr(
        ingestion_extension_points_module,
        "parsers",
        KeyedExtensionPoint("atlas.ingestion.parsers.v1"),
    )
    # `atlas_plugin_standard_catalog.kinds.register_standard_catalog_kinds()`
    # registers a delete guard against `atlas_plugin_apis`'s
    # process-wide `DeleteGuardRegistry` — `atlas.apis` is selected here, so
    # swap in a fresh one, same reason as the kind/permission registries.
    from atlas_plugin_api import purge as purge_module
    from atlas_plugin_apis import (
        extension_points as apis_extension_points_module,
    )

    monkeypatch.setattr(
        apis_extension_points_module,
        "delete_guards",
        apis_extension_points_module.DeleteGuardRegistry(),
    )
    # `register_standard_catalog_kinds()` also registers a Purge reference
    # scanner against `atlas_plugin_api.purge`'s process-wide
    # `PurgeScannerRegistry`, and — when
    # `atlas.flows` is among the descriptors below — so does
    # `atlas_plugin_flows.plugin.register_runtime()`; swap in a fresh
    # registry, same reason as the kind/delete-guard registries.
    monkeypatch.setattr(
        purge_module, "purge_scanners", purge_module.PurgeScannerRegistry()
    )

    descriptors = load_selected_descriptors(
        (
            "server.apps.catalog.plugin",
            "atlas_plugin_ingestion.plugin",
            "atlas_plugin_standard_catalog.plugin",
            "atlas_plugin_apis.plugin",
        )
    )

    validate_composition(descriptors)  # real REQUIRED_PLUGINS; must not raise

    assert not fresh_permission_registry.is_registered("atlas.c4.diagram.read")
    # Standard Catalog's own kinds and their declared capabilities are
    # unaffected.
    assert {"system", "component", "resource", "group", "user"} <= set(
        fresh_kind_registry.registered_ids(),
    )
    assert fresh_kind_registry.capabilities_for("system") == [
        "architecture.subject.v1"
    ]
    assert fresh_kind_registry.capabilities_for("group") == [
        "architecture.actor.v1"
    ]


@pytest.mark.django_db
def test_boundary_composes_with_database_schema_deselected(monkeypatch):
    """A distribution without the plugin
    composes successfully —
    `atlas.database-schema` is optional, like `atlas.apis`/`atlas.c4`.
    Unlike those plugins it registers no runtime hook of its own (`plugin.py`
    docstring), so deselecting it changes nothing about the kind or
    permission registries — `resource` still declares `schema.host.v1`
    (Standard Catalog's own declaration), proving Resources keep functioning
    without the facet plugin.

    `django_db`: this selection includes `atlas_plugin_ingestion.plugin`,
    whose descriptor now declares `job_ids` —
    `load_runtime_entry_points` resumes them, a real DB read/write.

    Runs the real runtime hooks against a throwaway kind registry (not the
    process-wide one, already populated by the real app startup this test
    session began with, which does select `atlas.database-schema`) so this
    doesn't collide with that.
    """
    import importlib

    import atlas_plugin_api.kinds as atlas_plugin_api_kinds_module
    from atlas_plugin_ingestion.extension_points import KeyedExtensionPoint

    import server.apps.catalog.kinds as kinds_package
    from server.apps.catalog.kinds.registry import EntityKindRegistry

    registry_module = importlib.import_module(
        "server.apps.catalog.kinds.registry"
    )
    ingestion_extension_points_module = importlib.import_module(
        "atlas_plugin_ingestion.extension_points",
    )

    fresh_registry = EntityKindRegistry()
    monkeypatch.setattr(kinds_package, "registry", fresh_registry)
    monkeypatch.setattr(registry_module, "registry", fresh_registry)
    # `register_kind()` resolves
    # `registry` as `atlas_plugin_api.kinds`'s own module global at call time —
    # the Core-side re-export patches above don't reach it, so it needs its
    # own patch too.
    monkeypatch.setattr(
        atlas_plugin_api_kinds_module, "registry", fresh_registry
    )
    # `atlas_plugin_ingestion.plugin.register_runtime()` also runs for real
    # here (it's in the descriptors below) — swap its own extension-point
    # registries too, so re-registering `GitHubConnector`/the YAML parser
    # doesn't collide with the process-wide ones already populated by the
    # real app startup this test session began with.
    monkeypatch.setattr(
        ingestion_extension_points_module,
        "connectors",
        KeyedExtensionPoint("atlas.ingestion.connectors.v1"),
    )
    monkeypatch.setattr(
        ingestion_extension_points_module,
        "parsers",
        KeyedExtensionPoint("atlas.ingestion.parsers.v1"),
    )
    # `atlas_plugin_standard_catalog.kinds.register_standard_catalog_kinds()`
    # registers a delete guard against `atlas_plugin_apis`'s
    # process-wide `DeleteGuardRegistry` whenever `atlas_plugin_apis` is
    # installed (real app startup's INSTALLED_APPS) — swap in a fresh one,
    # same reason as the kind registry.
    from atlas_plugin_api import purge as purge_module
    from atlas_plugin_apis import (
        extension_points as apis_extension_points_module,
    )

    monkeypatch.setattr(
        apis_extension_points_module,
        "delete_guards",
        apis_extension_points_module.DeleteGuardRegistry(),
    )
    # `register_standard_catalog_kinds()` also registers a Purge reference
    # scanner against `atlas_plugin_api.purge`'s process-wide
    # `PurgeScannerRegistry`, and — when
    # `atlas.flows` is among the descriptors below — so does
    # `atlas_plugin_flows.plugin.register_runtime()`; swap in a fresh
    # registry, same reason as the kind/delete-guard registries.
    monkeypatch.setattr(
        purge_module, "purge_scanners", purge_module.PurgeScannerRegistry()
    )

    descriptors = load_selected_descriptors(
        (
            "server.apps.catalog.plugin",
            "atlas_plugin_ingestion.plugin",
            "atlas_plugin_standard_catalog.plugin",
        )
    )

    validate_composition(descriptors)  # real REQUIRED_PLUGINS; must not raise

    assert "resource" in fresh_registry.registered_ids()
    assert fresh_registry.capabilities_for("resource") == ["schema.host.v1"]


def test_boundary_composes_with_ingestion_deselected(monkeypatch):
    """A distribution without atlas.ingestion composes
    successfully — `atlas.ingestion` is
    optional, unlike `atlas.standard-catalog` (which stays selected and
    required here, so this exercises the real `composition.REQUIRED_PLUGINS`
    check too, not just the opted-out synthetic-fixture path the other tests
    in this module use).

    Unlike `atlas.ingestion` itself (`plugin.py`'s `register_runtime` only
    touches its own `atlas.ingestion.connectors.v1`/`.parsers.v1` extension
    points), Standard Catalog registers real kinds against the process-wide
    `EntityKindRegistry` — so, same as the sibling boundary tests, a fresh
    registry is swapped in before re-running its `register_runtime` here to
    avoid colliding with the one the real app startup already populated.

    "No ingestion scheduling runs" is checked at the `resolve_installed_apps`
    level: `atlas_plugin_ingestion` (and its `django_apscheduler` job-store
    dependency) are simply absent from the resolved app list when the
    plugin isn't selected, and `runapscheduler`/the discovery job it
    registers live inside that app — an uninstalled app can't schedule
    anything, so there's nothing further to assert at runtime.

    "Manual entity CRUD via the API is unaffected" is checked directly
    against the real (already-composed) test session's API, since ingestion
    deselection changes nothing about how `EntityService`-backed writes work.
    """
    import importlib

    import atlas_plugin_api.kinds as atlas_plugin_api_kinds_module

    import server.apps.catalog.kinds as kinds_package
    from server.apps.catalog.kinds.registry import EntityKindRegistry
    from server.apps.plugins.resolver import resolve_installed_apps

    registry_module = importlib.import_module(
        "server.apps.catalog.kinds.registry"
    )

    fresh_registry = EntityKindRegistry()
    monkeypatch.setattr(kinds_package, "registry", fresh_registry)
    monkeypatch.setattr(registry_module, "registry", fresh_registry)
    # `register_kind()` resolves
    # `registry` as `atlas_plugin_api.kinds`'s own module global at call time —
    # the Core-side re-export patches above don't reach it, so it needs its
    # own patch too.
    monkeypatch.setattr(
        atlas_plugin_api_kinds_module, "registry", fresh_registry
    )
    # `atlas_plugin_standard_catalog.kinds.register_standard_catalog_kinds()`
    # registers a delete guard against `atlas_plugin_apis`'s
    # process-wide `DeleteGuardRegistry` whenever `atlas_plugin_apis` is
    # installed (real app startup's INSTALLED_APPS) — swap in a fresh one,
    # same reason as the kind registry.
    from atlas_plugin_api import purge as purge_module
    from atlas_plugin_apis import (
        extension_points as apis_extension_points_module,
    )

    monkeypatch.setattr(
        apis_extension_points_module,
        "delete_guards",
        apis_extension_points_module.DeleteGuardRegistry(),
    )
    # `register_standard_catalog_kinds()` also registers a Purge reference
    # scanner against `atlas_plugin_api.purge`'s process-wide
    # `PurgeScannerRegistry`, and — when
    # `atlas.flows` is among the descriptors below — so does
    # `atlas_plugin_flows.plugin.register_runtime()`; swap in a fresh
    # registry, same reason as the kind/delete-guard registries.
    monkeypatch.setattr(
        purge_module, "purge_scanners", purge_module.PurgeScannerRegistry()
    )

    descriptors = load_selected_descriptors(
        (
            "server.apps.catalog.plugin",
            "atlas_plugin_standard_catalog.plugin",
        )
    )

    validate_composition(descriptors)  # real REQUIRED_PLUGINS; must not raise

    assert {"system", "component", "resource", "group", "user"} <= set(
        fresh_registry.registered_ids(),
    )

    installed_apps = resolve_installed_apps(descriptors)
    assert "atlas_plugin_ingestion" not in installed_apps
    assert "django_apscheduler" not in installed_apps


@pytest.mark.django_db
def test_manual_entity_crud_via_api_unaffected_by_ingestion(
    owner_client, group
):
    """A distribution without atlas.ingestion composes
    successfully — manual entity CRUD via
    the API goes through `EntityService` exactly as it did before ingestion
    was extracted into its own plugin; nothing about `atlas.ingestion`'s
    presence in `SELECTED_PLUGINS` is on that path."""
    response = owner_client.post(
        "/api/systems/",
        {
            "metadata": {"name": "manual-only-system"},
            "spec": {"owner": "group:platform"},
        },
    )
    assert response.status_code == 201
    system_id = response.json()["id"]

    updated = owner_client.patch(
        f"/api/systems/{system_id}/",
        {"metadata": {"title": "Manual Only"}},
    )
    assert updated.status_code == 200
    assert updated.json()["metadata"]["title"] == "Manual Only"

    read = owner_client.get(f"/api/systems/{system_id}/")
    assert read.status_code == 200
    assert read.json()["metadata"]["name"] == "manual-only-system"


def test_validate_composition_fails_when_standard_catalog_is_not_selected(
    _clean_permission_registry,
):
    """Omitting the required plugin fails composition."""
    descriptors = load_selected_descriptors(
        ("server.apps.plugins.tests.fixtures.plugin_no_hook",)
    )

    with pytest.raises(CompositionError) as exc_info:
        validate_composition(descriptors)

    assert "atlas.standard-catalog" in str(exc_info.value)


def test_boundary_core_starts_with_standard_catalog_deselected(
    _clean_permission_registry,
    monkeypatch,
):
    """Core builds and starts with Standard Catalog deselected —
    a test-only configuration, not
    a supported deployment (the real `SELECTED_PLUGINS` keeps
    `atlas.standard-catalog` required via `composition.REQUIRED_PLUGINS`).

    `atlas.ingestion` is deliberately not part of this selection: since
    it declares its own `requires_plugins` on
    `atlas.standard-catalog`, so selecting it
    here would fail the dependency check this test isn't exercising.

    Runs the real `server.apps.catalog` runtime hooks against a throwaway
    registry (not the process-wide one, already populated by the real app
    startup this test session began with) so re-registering `api` here
    doesn't collide with that.
    """
    import importlib

    import atlas_plugin_api.kinds as atlas_plugin_api_kinds_module

    import server.apps.catalog.kinds as kinds_package
    from server.apps.catalog.kinds.registry import EntityKindRegistry

    # `kinds/__init__.py`'s `from .registry import registry` shadows the
    # `registry` submodule's own name on the `kinds` package with the
    # singleton instance — `importlib.import_module` (unlike `import a.b.c`,
    # which resolves via that shadowed attribute chain) reaches the actual
    # submodule so its `registry` attribute can be patched too.
    registry_module = importlib.import_module(
        "server.apps.catalog.kinds.registry"
    )

    fresh_registry = EntityKindRegistry()
    monkeypatch.setattr(kinds_package, "registry", fresh_registry)
    monkeypatch.setattr(registry_module, "registry", fresh_registry)
    # `register_kind()` resolves
    # `registry` as `atlas_plugin_api.kinds`'s own module global at call time —
    # the Core-side re-export patches above don't reach it, so it needs its
    # own patch too.
    monkeypatch.setattr(
        atlas_plugin_api_kinds_module, "registry", fresh_registry
    )

    descriptors = load_selected_descriptors(("server.apps.catalog.plugin",))

    validate_composition(
        descriptors, required_plugins=frozenset()
    )  # must not raise

    standard_catalog_kinds = {
        "system",
        "component",
        "resource",
        "group",
        "user",
    }
    assert not standard_catalog_kinds & set(fresh_registry.registered_ids())


def test_boundary_composes_with_flows_deselected(monkeypatch):
    """A distribution without atlas.flows composes
    successfully — `atlas.flows` is
    optional, unlike `atlas.standard-catalog` (which stays selected and
    required here, so this exercises the real `composition.REQUIRED_PLUGINS`
    check too, not just the opted-out synthetic-fixture path the other
    tests in this module use).

    `atlas_plugin_flows.plugin.register_runtime()` only registers
    `atlas.flows.flow.edit`/`.read` (no kind, no delete guard, no extension
    point) — so, unlike the c4/database-schema/ingestion boundary tests
    above, only the permission registry needs swapping to avoid colliding
    with the process-wide one the real app startup already populated
    (which does select `atlas.flows`); the kind registry swap here is only
    to isolate Standard Catalog's own real `register_runtime()` call the
    same way the ingestion-deselected test above does.
    """
    import importlib

    import atlas_plugin_api.kinds as atlas_plugin_api_kinds_module
    import atlas_plugin_api.permissions as atlas_plugin_api_permissions

    import server.apps.catalog.kinds as kinds_package
    from server.apps.catalog.kinds.registry import EntityKindRegistry
    from server.apps.plugins import permissions as permissions_module
    from server.apps.plugins.permissions import PermissionRegistry

    registry_module = importlib.import_module(
        "server.apps.catalog.kinds.registry"
    )

    fresh_kind_registry = EntityKindRegistry()
    monkeypatch.setattr(kinds_package, "registry", fresh_kind_registry)
    monkeypatch.setattr(registry_module, "registry", fresh_kind_registry)
    monkeypatch.setattr(
        atlas_plugin_api_kinds_module, "registry", fresh_kind_registry
    )

    fresh_permission_registry = PermissionRegistry()
    monkeypatch.setattr(
        permissions_module, "registry", fresh_permission_registry
    )
    monkeypatch.setattr(
        atlas_plugin_api_permissions,
        "registry",
        fresh_permission_registry,
    )
    # `atlas_plugin_standard_catalog.kinds.register_standard_catalog_kinds()`
    # registers a delete guard against `atlas_plugin_apis`'s
    # process-wide `DeleteGuardRegistry` whenever `atlas_plugin_apis` is
    # installed (real app startup's INSTALLED_APPS) — swap in a fresh one,
    # same reason as the kind registry
    # (`test_boundary_composes_with_ingestion_deselected`).
    from atlas_plugin_api import purge as purge_module
    from atlas_plugin_apis import (
        extension_points as apis_extension_points_module,
    )

    monkeypatch.setattr(
        apis_extension_points_module,
        "delete_guards",
        apis_extension_points_module.DeleteGuardRegistry(),
    )
    # `register_standard_catalog_kinds()` also registers a Purge reference
    # scanner against `atlas_plugin_api.purge`'s process-wide
    # `PurgeScannerRegistry`, and — when
    # `atlas.flows` is among the descriptors below — so does
    # `atlas_plugin_flows.plugin.register_runtime()`; swap in a fresh
    # registry, same reason as the kind/delete-guard registries.
    monkeypatch.setattr(
        purge_module, "purge_scanners", purge_module.PurgeScannerRegistry()
    )

    descriptors = load_selected_descriptors(
        (
            "server.apps.catalog.plugin",
            "atlas_plugin_standard_catalog.plugin",
        )
    )

    validate_composition(descriptors)  # real REQUIRED_PLUGINS; must not raise

    assert not fresh_permission_registry.is_registered("atlas.flows.flow.edit")
    assert not fresh_permission_registry.is_registered("atlas.flows.flow.read")
    assert {"system", "component", "resource", "group", "user"} <= set(
        fresh_kind_registry.registered_ids(),
    )


def test_boundary_fails_when_flows_selected_without_standard_catalog():
    """Missing Standard Catalog fails composition:
    `atlas.flows` declares a manifest
    dependency on `atlas.standard-catalog`; selecting
    it alone fails composition, identifying the unsatisfied dependency.
    `_check_plugin_dependencies` runs before `load_runtime_entry_points`
    (composition.py's `validate_composition`), so this fails before any
    runtime hook runs — no registry swap needed, unlike the boundary tests
    above."""
    descriptors = load_selected_descriptors(("atlas_plugin_flows.plugin",))

    with pytest.raises(CompositionError) as exc_info:
        validate_composition(descriptors, required_plugins=frozenset())

    message = str(exc_info.value)
    assert "atlas.flows" in message
    assert "atlas.standard-catalog" in message
