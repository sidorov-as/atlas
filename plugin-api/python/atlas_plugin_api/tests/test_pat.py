"""PAT validation contract tests.

No Django settings are configured in this package's own test environment
(see `test_entity_service.py`'s equivalent guard); `pat.py` needs none — it
holds only a dataclass, a `Protocol`, and a bind/get singleton slot.
"""

import pytest

from atlas_plugin_api.pat import (
    PATValidator,
    ResolvedPersonalAccessToken,
    bind_pat_validator,
    get_pat_validator,
)


def _stub_validator(raw_token: str) -> ResolvedPersonalAccessToken | None:
    if raw_token == "atlaspat_valid":
        return ResolvedPersonalAccessToken(
            user="the-owner", scopes=frozenset({"catalog:read"})
        )
    return None


@pytest.fixture(autouse=True)
def _reset_bound_pat_validator():
    import atlas_plugin_api.pat as module

    previous = module._pat_validator
    try:
        yield
    finally:
        module._pat_validator = previous


def test_stub_validator_satisfies_the_published_protocol():
    assert isinstance(_stub_validator, PATValidator)


def test_get_pat_validator_raises_before_binding():
    import atlas_plugin_api.pat as module

    module._pat_validator = None

    with pytest.raises(RuntimeError):
        get_pat_validator()


def test_bind_pat_validator_registers_the_singleton():
    bind_pat_validator(_stub_validator)

    assert get_pat_validator() is _stub_validator


def test_resolved_personal_access_token_is_a_plain_frozen_dataclass():
    resolved = ResolvedPersonalAccessToken(
        user="alice", scopes=frozenset({"catalog:write"})
    )
    assert resolved.user == "alice"
    assert resolved.scopes == frozenset({"catalog:write"})


def test_pat_module_is_importable_without_django_setup():
    import atlas_plugin_api.pat  # noqa: F401
