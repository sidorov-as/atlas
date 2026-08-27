"""Permission registration and authorization-check contract tests

No Django settings are configured in this package's own test environment
(`atlas_plugin_api` must stay importable without one — see
`test_descriptor.py`'s equivalent guard); `permissions.py` needs none,
unlike `catalog.py`'s `get_catalog_entity_model()`.
"""

import pytest

from atlas_plugin_api.permissions import (
    DuplicatePermissionError,
    InvalidPermissionEffectError,
    PermissionRegistry,
    PolicyEvaluator,
    bind_policy_evaluator,
    classify_permission_effect,
    get_policy_evaluator,
    register_permission,
    registry,
)


class _StubPolicyEvaluator:
    def check(self, principal, permission, resource):
        return permission.endswith(".read")


@pytest.fixture(autouse=True)
def _clean_registry():
    owners_snapshot = dict(registry._owners)
    effects_snapshot = dict(registry._effects)
    yield
    registry._owners.clear()
    registry._owners.update(owners_snapshot)
    registry._effects.clear()
    registry._effects.update(effects_snapshot)


@pytest.fixture(autouse=True)
def _reset_bound_policy_evaluator():
    import atlas_plugin_api.permissions as module

    previous = module._policy_evaluator
    try:
        yield
    finally:
        module._policy_evaluator = previous


def test_registering_a_permission_makes_it_registered():
    local_registry = PermissionRegistry()

    local_registry.register("atlas.c4.diagram.read", owner="atlas.c4")

    assert local_registry.is_registered("atlas.c4.diagram.read") is True


def test_duplicate_permission_registration_is_rejected_and_names_both_plugins():
    local_registry = PermissionRegistry()
    local_registry.register("atlas.c4.diagram.read", owner="atlas.c4")

    with pytest.raises(DuplicatePermissionError) as exc_info:
        local_registry.register(
            "atlas.c4.diagram.read",
            owner="atlas.standard-catalog",
        )

    error = exc_info.value
    assert error.permission_id == "atlas.c4.diagram.read"
    assert error.existing_owner == "atlas.c4"
    assert error.new_owner == "atlas.standard-catalog"
    assert "atlas.c4" in str(error)
    assert "atlas.standard-catalog" in str(error)


def test_unknown_permission_is_not_registered():
    local_registry = PermissionRegistry()

    assert local_registry.is_registered("does-not-exist") is False


def test_registered_ids_lists_registered_permission_ids_sorted():
    local_registry = PermissionRegistry()
    local_registry.register("atlas.c4.diagram.write", owner="atlas.c4")
    local_registry.register("atlas.c4.diagram.read", owner="atlas.c4")

    assert local_registry.registered_ids() == [
        "atlas.c4.diagram.read",
        "atlas.c4.diagram.write",
    ]


def test_register_permission_registers_against_the_process_wide_registry():
    register_permission(
        "atlas.test-fixture.permission.read", owner="atlas.test-fixture"
    )

    assert registry.is_registered("atlas.test-fixture.permission.read") is True


def test_stub_evaluator_satisfies_the_published_protocol():
    assert isinstance(_StubPolicyEvaluator(), PolicyEvaluator)


def test_get_policy_evaluator_raises_before_binding():
    import atlas_plugin_api.permissions as module

    module._policy_evaluator = None

    with pytest.raises(RuntimeError):
        get_policy_evaluator()


def test_bind_policy_evaluator_registers_the_singleton():
    evaluator = _StubPolicyEvaluator()

    bind_policy_evaluator(evaluator)

    assert get_policy_evaluator() is evaluator


def test_permissions_module_is_importable_without_django_setup():
    import atlas_plugin_api.permissions  # noqa: F401


# Permission effect classification.


def test_registering_without_effect_defaults_dot_read_to_read():
    local_registry = PermissionRegistry()
    local_registry.register("atlas.c4.diagram.read", owner="atlas.c4")

    assert local_registry.effect_for("atlas.c4.diagram.read") == "read"


def test_registering_without_effect_defaults_everything_else_to_write():
    local_registry = PermissionRegistry()
    local_registry.register("atlas.some-plugin.widget.sync", owner="atlas.some-plugin")

    assert local_registry.effect_for("atlas.some-plugin.widget.sync") == "write"


def test_explicit_read_effect_overrides_the_default_for_a_nonstandard_suffix():
    local_registry = PermissionRegistry()
    local_registry.register(
        "atlas.some-plugin.widget.sync",
        owner="atlas.some-plugin",
        effect="read",
    )

    assert local_registry.effect_for("atlas.some-plugin.widget.sync") == "read"


def test_unregistered_permission_has_no_effect():
    local_registry = PermissionRegistry()

    assert local_registry.effect_for("does-not-exist") is None


def test_invalid_effect_is_rejected():
    local_registry = PermissionRegistry()

    with pytest.raises(InvalidPermissionEffectError) as exc_info:
        local_registry.register(
            "atlas.c4.diagram.read", owner="atlas.c4", effect="delete"
        )

    assert exc_info.value.permission_id == "atlas.c4.diagram.read"
    assert exc_info.value.effect == "delete"
    assert not local_registry.is_registered("atlas.c4.diagram.read")


@pytest.mark.parametrize(
    "permission_id",
    [
        "system.read",
        "component.read",
        "atlas.flows.flow.read",
        "atlas.c4.diagram.read",
    ],
)
def test_classify_permission_effect_treats_dot_read_as_read_even_unregistered(
    permission_id,
):
    """Core never calls `register_permission` for its own `<kind>.read`
    ids — classification
    must not depend on registration for the five standard suffixes."""
    assert classify_permission_effect(permission_id) == "read"


@pytest.mark.parametrize(
    "permission_id",
    [
        "system.edit",
        "system.create",
        "system.delete",
        "system.purge",
        "atlas.apis.endpointDependency.create",
        "atlas.apis.endpointDependency.delete",
    ],
)
def test_standard_write_suffixes_are_write_even_unregistered(permission_id):
    assert classify_permission_effect(permission_id) == "write"


def test_classify_permission_effect_denies_an_unregistered_nonstandard_id():
    assert classify_permission_effect("atlas.some-plugin.widget.sync") == "write"


def test_classify_permission_effect_honors_an_explicit_read_declaration():
    register_permission(
        "atlas.test-fixture.widget.sync",
        owner="atlas.test-fixture",
        effect="read",
    )

    assert classify_permission_effect("atlas.test-fixture.widget.sync") == "read"


def test_classify_permission_effect_ignores_registry_for_standard_suffixes():
    """A plugin registering `.execute`/`.sync`-style ids can't accidentally
    reclassify a standard `<kind>.edit` id by registering it with a
    conflicting effect — the suffix rule always wins for the five
    standard suffixes, so the registry is never even consulted for them."""
    register_permission("component.edit", owner="atlas.test-fixture", effect="read")

    assert classify_permission_effect("component.edit") == "write"
