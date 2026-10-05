"""Shared entity-controller helper contract tests.

No Django settings are configured in this package's own test environment
(see `test_catalog.py`'s equivalent guard) — `tag_colors()`/`metadata_out()`/
`entity_capabilities()` resolving against the real concrete models/registries
are covered from Core's side and by every plugin's own CRUD API tests, which
already exercise these call paths.
"""

import pytest
from dmr.response import APIError

from atlas_plugin_api.entity_helpers import (
    API_VERSION,
    bind_entity_helpers,
    delete_blocked,
    ingested_from,
    not_found,
    spec_owner_ref,
)


@pytest.fixture(autouse=True)
def _reset_bound_entity_helpers():
    import atlas_plugin_api.entity_helpers as module

    previous_adopt = module._adopt_impl
    previous_blocked_by = module._blocked_by_impl
    previous_blocked_by_reason = module._blocked_by_reason_impl
    try:
        yield
    finally:
        module._adopt_impl = previous_adopt
        module._blocked_by_impl = previous_blocked_by
        module._blocked_by_reason_impl = previous_blocked_by_reason


class _StubSpec:
    def __init__(self, *, fields_set, owner=None):
        self.model_fields_set = fields_set
        self.owner = owner


def test_api_version_constant():
    assert API_VERSION == "atlas/v1alpha1"


def test_not_found_and_delete_blocked_are_api_errors():
    assert isinstance(not_found("nope"), APIError)
    assert isinstance(delete_blocked("nope"), APIError)


def test_spec_owner_ref_returns_none_when_owner_unset():
    assert spec_owner_ref(None) is None
    assert spec_owner_ref(_StubSpec(fields_set={"name"})) is None


def test_spec_owner_ref_returns_the_set_owner():
    spec = _StubSpec(fields_set={"owner"}, owner="group:platform")
    assert spec_owner_ref(spec) == "group:platform"


def test_ingested_from_returns_none_when_not_ingested():
    class _Entity:
        ingestion_claim = None

    assert ingested_from(_Entity()) is None


def test_ingested_from_returns_none_without_the_ingestion_relation():
    class _Entity:
        pass

    assert ingested_from(_Entity()) is None


def test_ingested_from_returns_the_repository_source_id_and_path():
    class _Repo:
        def __str__(self):
            return "test-source/org/repo"

    class _Claim:
        repository = _Repo()

    class _Entity:
        ingestion_claim = _Claim()

    assert ingested_from(_Entity()) == "test-source/org/repo"


def test_adopt_raises_before_core_binds_its_implementation():
    import atlas_plugin_api.entity_helpers as module

    module._adopt_impl = None

    with pytest.raises(RuntimeError):
        module.adopt(instance=None, request=None, body=None)


def test_blocked_by_raises_before_core_binds_its_implementation():
    import atlas_plugin_api.entity_helpers as module

    module._blocked_by_impl = None

    with pytest.raises(RuntimeError):
        module.blocked_by(instance=None)


def test_blocked_by_reason_raises_before_core_binds_its_implementation():
    import atlas_plugin_api.entity_helpers as module

    module._blocked_by_reason_impl = None

    with pytest.raises(RuntimeError):
        module.blocked_by_reason(instance=None)


def test_bind_entity_helpers_registers_the_real_implementations():
    calls = []

    def _adopt(instance, request, body):
        calls.append((instance, request, body))

    def _blocked_by(instance):
        return "org/repo"

    def _blocked_by_reason(instance):
        return "removed_entity"

    bind_entity_helpers(
        adopt=_adopt, blocked_by=_blocked_by, blocked_by_reason=_blocked_by_reason
    )

    import atlas_plugin_api.entity_helpers as module

    module.adopt("e", "r", "b")
    assert calls == [("e", "r", "b")]
    assert module.blocked_by("e") == "org/repo"
    assert module.blocked_by_reason("e") == "removed_entity"


def test_entity_helpers_module_is_importable_without_django_setup():
    import atlas_plugin_api.entity_helpers  # noqa: F401
