from __future__ import annotations

import http.server
import ipaddress
import socket
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Lock
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from atlas_plugin_api import (
    AuthenticationFailure,
    AuthenticationFailureCategory,
    ExternalGroupSnapshotStatus,
    RedirectCallbackContext,
    RedirectFlowContext,
    RedirectProviderContractHooks,
    VerifiedIdentity,
    run_redirect_provider_contract,
)

from atlas_plugin_auth_gitea.config import GiteaConfig
from atlas_plugin_auth_gitea.plugin import PROVIDER_ID
from atlas_plugin_auth_gitea.provider import (
    AllauthGiteaTransport,
    GiteaProtocolError,
    GiteaProvider,
)

ORIGIN = "https://gitea.example"
CALLBACK = (
    f"https://atlas.example/auth/browser/v1/providers/{PROVIDER_ID}/callback"
)


def _config(**overrides):
    values = {
        "instanceOrigin": ORIGIN,
        "clientId": "atlas-client",
        "clientSecret": "test-client-secret",
        "scopes": ["read:user"],
        "oauthPkceEnabled": True,
    }
    values.update(overrides)
    return GiteaConfig.model_validate(values)


class FakeTransport:
    def __init__(self) -> None:
        self.unavailable = False
        self.invalid_profile = False
        self.posts: list[tuple[str, dict[str, str]]] = []
        self.profile_requests: list[tuple[str, str]] = []
        self._lock = Lock()

    def exchange_code(self, url, data):
        with self._lock:
            self.posts.append((url, dict(data)))
        if self.unavailable:
            raise requests.Timeout("token=raw-upstream-secret")
        return {
            "access_token": "gitea-access-token",
            "scope": "read:user admin write:organization",
        }

    def get_profile(self, url, *, access_token):
        with self._lock:
            self.profile_requests.append((url, access_token))
        if self.unavailable:
            raise requests.ConnectionError("raw upstream response body")
        if self.invalid_profile:
            return {"id": "", "login": "mutable-login"}
        return {
            "id": 248289761001,
            "login": "mutable-login",
            "name": "Example Person",
            "email": "person@example.com",
            "is_admin": True,
        }

    def get_health(self, url):
        if self.unavailable:
            raise requests.ConnectionError("client_secret=test-client-secret")
        return {"status": "pass"}


def _context(attempt="attempt-1", *, expired=False):
    return RedirectFlowContext(
        provider_id=PROVIDER_ID,
        source_id=ORIGIN,
        attempt_id=attempt,
        correlation_id=f"correlation-{attempt}",
        deadline=datetime.now(UTC) + timedelta(minutes=-1 if expired else 1),
        callback_url=CALLBACK,
    )


def _callback(attempt="attempt-1", **parameters):
    return RedirectCallbackContext(
        provider_id=PROVIDER_ID,
        source_id=ORIGIN,
        attempt_id=attempt,
        correlation_id=f"correlation-{attempt}",
        deadline=datetime.now(UTC) + timedelta(minutes=1),
        callback_parameters=parameters,
        callback_url=CALLBACK,
    )


def test_begin_uses_gitea_authorization_code_pkce_s256_and_minimal_scope():
    provider = GiteaProvider(_config(), transport=FakeTransport())

    challenge = provider.begin(_context())
    parsed = urlsplit(challenge.authorization_url)
    query = parse_qs(parsed.query)

    assert parsed.path == "/login/oauth/authorize"
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["read:user"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"]
    assert query["state"]
    assert query["redirect_uri"] == [CALLBACK]


def test_complete_exchanges_code_and_reads_established_profile_endpoint():
    transport = FakeTransport()
    provider = GiteaProvider(_config(), transport=transport)
    context = _callback(code="authorization-code", state="core-state")

    result = provider.complete(context)

    assert isinstance(result, VerifiedIdentity)
    assert transport.posts[0][0] == f"{ORIGIN}/login/oauth/access_token"
    assert transport.posts[0][1]["code_verifier"]
    assert transport.profile_requests == [
        (f"{ORIGIN}/api/v1/user", "gitea-access-token")
    ]


def test_profile_normalization_uses_numeric_id_and_never_authorizes():
    provider = GiteaProvider(_config(), transport=FakeTransport())

    result = provider.complete(_callback(code="authorization-code"))

    assert isinstance(result, VerifiedIdentity)
    assert result.provider_id == PROVIDER_ID
    assert result.source_id == ORIGIN
    assert result.subject == "248289761001"
    assert result.profile.username == "mutable-login"
    assert result.profile.display_name == "Example Person"
    assert result.profile.email == "person@example.com"
    assert result.groups.status is ExternalGroupSnapshotStatus.UNSUPPORTED
    assert set(result.attributes) == {"username", "displayName", "email"}
    assert "scope" not in result.attributes
    assert "is_admin" not in result.attributes


def test_mutable_profile_changes_do_not_change_the_stable_subject():
    provider = GiteaProvider(_config(), transport=FakeTransport())

    first = provider._normalize({"id": 42, "login": "before"})
    second = provider._normalize(
        {"id": "42", "login": "after", "email": "new@example.com"}
    )

    assert first.subject == second.subject == "42"


def test_invalid_subject_and_source_fail_without_identity():
    transport = FakeTransport()
    transport.invalid_profile = True
    provider = GiteaProvider(_config(), transport=transport)

    assert provider.complete(_callback(code="code")) == AuthenticationFailure(
        AuthenticationFailureCategory.INVALID_RESULT
    )

    wrong_source = RedirectCallbackContext(
        provider_id=PROVIDER_ID,
        source_id="https://replacement.example",
        attempt_id="wrong-source",
        correlation_id="correlation-wrong-source",
        deadline=datetime.now(UTC) + timedelta(minutes=1),
        callback_parameters={"code": "code"},
        callback_url=CALLBACK,
    )
    assert provider.complete(wrong_source) == AuthenticationFailure(
        AuthenticationFailureCategory.INVALID_RESULT
    )


def test_safe_failure_and_health_diagnostics_do_not_expose_upstream_details():
    transport = FakeTransport()
    transport.unavailable = True
    provider = GiteaProvider(_config(), transport=transport)

    failure = provider.complete(_callback(code="secret-code"))
    diagnostic = provider.health()

    assert failure == AuthenticationFailure(
        AuthenticationFailureCategory.UNAVAILABLE, retryable=True
    )
    assert "secret-code" not in repr(failure)
    assert "test-client-secret" not in repr(diagnostic)
    assert diagnostic == {
        "providerId": PROVIDER_ID,
        "status": "unavailable",
        "category": "upstream_unavailable",
    }


def test_healthy_diagnostic_is_allowlisted_and_logout_is_local_only():
    provider = GiteaProvider(_config(), transport=FakeTransport())

    assert provider.health() == {
        "providerId": PROVIDER_ID,
        "status": "available",
        "category": "ok",
    }
    assert provider.descriptor.remote_logout.value == "unsupported"
    assert not hasattr(provider, "remote_logout")


def test_transport_dns_rejects_metadata_and_requires_private_allowlist(
    monkeypatch,
):
    transport = AllauthGiteaTransport(_config())
    monkeypatch.setattr(
        "atlas_plugin_auth_gitea.provider.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (None, None, None, None, ("169.254.169.254", 443))
        ],
    )
    with pytest.raises(GiteaProtocolError, match="prohibited"):
        transport._validate_resolved_destination(f"{ORIGIN}/api/v1/user")

    monkeypatch.setattr(
        "atlas_plugin_auth_gitea.provider.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.5", 443))],
    )
    with pytest.raises(GiteaProtocolError, match="allowlisted"):
        transport._validate_resolved_destination(f"{ORIGIN}/api/v1/user")

    allowed = AllauthGiteaTransport(_config(allowedDestinations=[ORIGIN]))
    allowed._validate_resolved_destination(f"{ORIGIN}/api/v1/user")


class _QuietHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


class _JsonOkHandler(_QuietHandler):
    def _respond(self) -> None:
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self._respond()

    def do_POST(self) -> None:
        self._respond()


@contextmanager
def _serve(handler_cls: type[http.server.BaseHTTPRequestHandler]):
    server = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _mock_resolution(monkeypatch, answers: dict[str, str]) -> list[str]:
    """Point `socket.getaddrinfo` at fixed answers for specific hostnames and
    return the list of hostnames it was actually asked to resolve, in order.
    A literal IP address always "resolves" to itself with no real lookup and
    is passed through to the real resolver without being counted -- it isn't
    a fresh hostname resolution, just the connection layer's normal
    bookkeeping on an address that was already pinned."""
    calls: list[str] = []
    real_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(host, port=None, *args, **kwargs):
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            return real_getaddrinfo(host, port, *args, **kwargs)
        calls.append(host)
        if host not in answers:
            raise AssertionError(f"unexpected DNS lookup for {host!r}")
        address = (answers[host], port or 0)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", address)]

    monkeypatch.setattr(
        "atlas_plugin_auth_gitea.provider.socket.getaddrinfo", fake_getaddrinfo
    )
    return calls


def test_get_profile_resolves_hostname_exactly_once(monkeypatch):
    with _serve(_JsonOkHandler) as (server_host, server_port):
        calls = _mock_resolution(monkeypatch, {"localhost": server_host})
        origin = f"http://localhost:{server_port}"
        transport = AllauthGiteaTransport(
            _config(allowDevelopmentHttp=True, allowedDestinations=[origin])
        )

        result = transport.get_profile(
            f"{origin}/api/v1/user", access_token="token-123"
        )

        assert result == {"ok": True}
        assert calls == ["localhost"]


def test_get_health_resolves_hostname_exactly_once(monkeypatch):
    with _serve(_JsonOkHandler) as (server_host, server_port):
        calls = _mock_resolution(monkeypatch, {"localhost": server_host})
        origin = f"http://localhost:{server_port}"
        transport = AllauthGiteaTransport(
            _config(allowDevelopmentHttp=True, allowedDestinations=[origin])
        )

        result = transport.get_health(f"{origin}/api/healthz")

        assert result == {"ok": True}
        assert calls == ["localhost"]


def test_exchange_code_resolves_hostname_exactly_once(monkeypatch):
    with _serve(_JsonOkHandler) as (server_host, server_port):
        calls = _mock_resolution(monkeypatch, {"localhost": server_host})
        origin = f"http://localhost:{server_port}"
        transport = AllauthGiteaTransport(
            _config(allowDevelopmentHttp=True, allowedDestinations=[origin])
        )

        result = transport.exchange_code(
            f"{origin}/login/oauth/access_token", {"grant_type": "x"}
        )

        assert result == {"ok": True}
        assert calls == ["localhost"]


def test_connects_to_originally_validated_address_despite_later_dns_change(
    monkeypatch,
):
    """A DNS answer that would differ on a second lookup is never consulted,
    because the transport resolves the hostname once and connects to that
    same address (a DNS answer that changes between
    validation and connection)."""
    with _serve(_JsonOkHandler) as (server_host, server_port):
        hostname = "localhost"
        real_getaddrinfo = socket.getaddrinfo
        calls: list[str] = []

        def fake_getaddrinfo(host, port=None, *args, **kwargs):
            try:
                ipaddress.ip_address(host)
            except ValueError:
                pass
            else:
                return real_getaddrinfo(host, port, *args, **kwargs)
            calls.append(host)
            # The first (validation) lookup sees the real, safe address; any
            # further lookup would see a different, unreachable one.
            answer = server_host if len(calls) == 1 else "203.0.113.1"
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (answer, 0))
            ]

        monkeypatch.setattr(
            "atlas_plugin_auth_gitea.provider.socket.getaddrinfo",
            fake_getaddrinfo,
        )
        origin = f"http://{hostname}:{server_port}"
        transport = AllauthGiteaTransport(
            _config(allowDevelopmentHttp=True, allowedDestinations=[origin])
        )

        result = transport.get_profile(
            f"{origin}/api/v1/user", access_token="token-123"
        )

        assert result == {"ok": True}
        assert calls == [hostname]


def test_redirect_provider_passes_public_contract():
    attempt_number = 0
    contexts = {}

    def provider_factory():
        nonlocal attempt_number
        attempt_number += 1
        transport = FakeTransport()
        context = _context(f"attempt-{attempt_number}")
        contexts["current"] = context
        contexts["transport"] = transport
        return GiteaProvider(_config(), transport=transport)

    def callback(_challenge, **parameters):
        context = contexts["current"]
        return RedirectCallbackContext(
            provider_id=PROVIDER_ID,
            source_id=ORIGIN,
            attempt_id=context.attempt_id,
            correlation_id=context.correlation_id,
            deadline=context.deadline,
            callback_parameters=parameters,
            callback_url=CALLBACK,
        )

    hooks = RedirectProviderContractHooks(
        provider_factory=provider_factory,
        start_context_factory=lambda: contexts["current"],
        valid_callback_factory=lambda challenge: callback(
            challenge, code="valid"
        ),
        mismatched_callback_factory=lambda challenge: callback(challenge),
        expired_callback_factory=lambda challenge: RedirectCallbackContext(
            provider_id=PROVIDER_ID,
            source_id=ORIGIN,
            attempt_id=contexts["current"].attempt_id,
            correlation_id=contexts["current"].correlation_id,
            deadline=datetime.now(UTC) - timedelta(seconds=1),
            callback_parameters={"code": "expired"},
            callback_url=CALLBACK,
        ),
        browser_mismatched_callback_factory=lambda challenge: callback(
            challenge
        ),
        unavailable_callback_factory=lambda challenge: (
            setattr(contexts["transport"], "unavailable", True)
            or callback(challenge, code="unavailable")
        ),
    )

    run_redirect_provider_contract(hooks)
