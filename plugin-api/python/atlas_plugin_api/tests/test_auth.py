"""Session-based auth contract tests.

No Django settings are configured in this package's own test environment
(see `test_catalog.py`'s equivalent guard) — `SessionAuth` needs none of its
own (it only reads `request.user.is_authenticated` off whatever controller
calls it).
"""

from atlas_plugin_api.auth import SessionAuth


class _StubUser:
    def __init__(self, *, is_authenticated):
        self.is_authenticated = is_authenticated


class _StubRequest:
    def __init__(self, *, is_authenticated):
        self.user = _StubUser(is_authenticated=is_authenticated)


class _StubController:
    def __init__(self, *, is_authenticated):
        self.request = _StubRequest(is_authenticated=is_authenticated)


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
