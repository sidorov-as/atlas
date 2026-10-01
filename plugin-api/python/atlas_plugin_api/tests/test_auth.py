"""Session- and PAT-Bearer-based auth contract tests.

No Django settings are configured in this package's own test environment
(see `test_catalog.py`'s equivalent guard) — `SessionAuth` needs none of its
own (it only reads `request.user.is_authenticated` off whatever controller
calls it); `PATBearerAuth` needs none either, since it goes through
`pat.get_pat_validator()`'s registered stub rather than a real Django model.
"""

import pytest

from atlas_plugin_api.auth import PATBearerAuth, SessionAuth
from atlas_plugin_api.pat import ResolvedPersonalAccessToken, bind_pat_validator


class _StubUser:
    def __init__(self, *, is_authenticated):
        self.is_authenticated = is_authenticated


class _StubRequest:
    def __init__(self, *, is_authenticated=False, headers=None):
        self.user = _StubUser(is_authenticated=is_authenticated)
        self.headers = headers or {}


class _StubController:
    def __init__(self, *, is_authenticated=False, headers=None):
        self.request = _StubRequest(is_authenticated=is_authenticated, headers=headers)


def test_session_auth_returns_itself_for_an_authenticated_session():
    auth = SessionAuth()
    controller = _StubController(is_authenticated=True)

    assert auth(endpoint=None, controller=controller) is auth


def test_session_auth_returns_none_for_an_unauthenticated_session():
    auth = SessionAuth()
    controller = _StubController(is_authenticated=False)

    assert auth(endpoint=None, controller=controller) is None


def test_session_auth_declares_a_cookie_security_scheme():
    auth = SessionAuth()
    assert "session" in auth.security_schemes
    assert auth.security_requirement == {"session": []}


def test_auth_module_is_importable_without_django_setup():
    import atlas_plugin_api.auth  # noqa: F401


@pytest.fixture(autouse=True)
def _reset_bound_pat_validator():
    import atlas_plugin_api.pat as module

    previous = module._pat_validator
    try:
        yield
    finally:
        module._pat_validator = previous


def _bind_stub_validator(*, valid_token="atlaspat_valid", user="the-owner"):
    resolved = ResolvedPersonalAccessToken(
        user=user, scopes=frozenset({"catalog:read"})
    )

    def _validator(raw_token: str) -> ResolvedPersonalAccessToken | None:
        return resolved if raw_token == valid_token else None

    bind_pat_validator(_validator)
    return resolved


def test_pat_bearer_auth_resolves_a_valid_token_and_sets_request_user():
    resolved = _bind_stub_validator()
    controller = _StubController(headers={"Authorization": "Bearer atlaspat_valid"})

    result = PATBearerAuth()(endpoint=None, controller=controller)

    assert isinstance(result, PATBearerAuth)
    assert result.resolved is resolved
    assert controller.request.user == "the-owner"


def test_pat_bearer_auth_returns_none_for_missing_authorization_header():
    _bind_stub_validator()
    controller = _StubController()

    assert PATBearerAuth()(endpoint=None, controller=controller) is None


def test_pat_bearer_auth_returns_none_for_non_bearer_scheme():
    _bind_stub_validator()
    controller = _StubController(headers={"Authorization": "Basic atlaspat_valid"})

    assert PATBearerAuth()(endpoint=None, controller=controller) is None


def test_pat_bearer_auth_returns_none_for_a_token_the_validator_rejects():
    _bind_stub_validator()
    controller = _StubController(headers={"Authorization": "Bearer atlaspat_wrong"})

    assert PATBearerAuth()(endpoint=None, controller=controller) is None


def test_pat_bearer_auth_never_mutates_the_shared_instance():
    """`dmr.security.base.SyncAuth` instances must stay stateless — a
    successful call returns a *new* instance, not `self`, so the
    class-level object configured in an endpoint's `auth = (...)` tuple
    never carries a previous request's resolved token into the next one.
    """
    _bind_stub_validator()
    shared = PATBearerAuth()
    controller = _StubController(headers={"Authorization": "Bearer atlaspat_valid"})

    result = shared(endpoint=None, controller=controller)

    assert result is not shared
    assert shared.resolved is None


def test_pat_bearer_auth_declares_a_bearer_security_scheme():
    auth = PATBearerAuth()
    assert "personalAccessToken" in auth.security_schemes
    assert auth.security_requirement == {"personalAccessToken": []}
