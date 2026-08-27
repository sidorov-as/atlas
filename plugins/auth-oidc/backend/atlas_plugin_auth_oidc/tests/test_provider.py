from __future__ import annotations

import datetime as dt
import http.server
import ipaddress
import socket
import ssl
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Lock
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
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
from cryptography.hazmat.primitives.asymmetric import rsa

from atlas_plugin_auth_oidc.config import OIDCConfig
from atlas_plugin_auth_oidc.plugin import PROVIDER_ID
from atlas_plugin_auth_oidc.provider import (
    OIDCProtocolError,
    OIDCProvider,
    RequestsOIDCTransport,
)

ISSUER = "https://idp.example"
DISCOVERY = f"{ISSUER}/.well-known/openid-configuration"
CALLBACK = (
    f"https://atlas.example/auth/browser/v1/providers/{PROVIDER_ID}/callback"
)


def _config(**overrides):
    values = {
        "discoveryUrl": DISCOVERY,
        "expectedIssuer": ISSUER,
        "clientId": "atlas",
        "clientSecret": "test-secret",
        "scopes": ["openid", "profile", "email", "groups"],
        "groupsClaim": "groups",
    }
    values.update(overrides)
    return OIDCConfig.model_validate(values)


class FakeTransport:
    def __init__(self) -> None:
        self.unavailable = False
        self.userinfo_sub = "subject-42"
        self.posts: list[dict[str, str]] = []
        self._lock = Lock()

    def get_json(self, url, *, bearer_token=None):
        if self.unavailable:
            import requests

            raise requests.ConnectionError("upstream body with token")
        if url == DISCOVERY:
            return {
                "issuer": ISSUER,
                "authorization_endpoint": f"{ISSUER}/authorize",
                "token_endpoint": f"{ISSUER}/token",
                "userinfo_endpoint": f"{ISSUER}/userinfo",
                "jwks_uri": f"{ISSUER}/jwks",
                "code_challenge_methods_supported": ["S256"],
            }
        return {
            "sub": self.userinfo_sub,
            "preferred_username": "person",
            "name": "Example Person",
            "email": "person@example.com",
            "email_verified": True,
            "groups": ["engineering"],
        }

    def post_form(self, url, data):
        with self._lock:
            self.posts.append(dict(data))
        if self.unavailable:
            import requests

            raise requests.Timeout("raw upstream token response")
        return {"id_token": "encoded-id-token", "access_token": "access-token"}


def _context(attempt="attempt-1", *, expired=False):
    deadline = datetime.now(UTC) + timedelta(minutes=-1 if expired else 1)
    return RedirectFlowContext(
        provider_id=PROVIDER_ID,
        source_id=ISSUER,
        attempt_id=attempt,
        correlation_id=f"correlation-{attempt}",
        deadline=deadline,
        callback_url=CALLBACK,
    )


def _callback(attempt="attempt-1", **parameters):
    return RedirectCallbackContext(
        provider_id=PROVIDER_ID,
        source_id=ISSUER,
        attempt_id=attempt,
        correlation_id=f"correlation-{attempt}",
        deadline=datetime.now(UTC) + timedelta(minutes=1),
        callback_parameters=parameters,
        callback_url=CALLBACK,
    )


def _provider(transport=None):
    transport = transport or FakeTransport()

    def verify(_encoded, _metadata, config):
        return {
            "iss": ISSUER,
            "sub": "subject-42",
            "aud": config.client_id,
            "exp": 4_000_000_000,
            "iat": 2_000_000_000,
            "nonce": provider._derived_value("nonce", current_context[0]),
        }

    current_context = [_context()]
    provider = OIDCProvider(
        _config(), transport=transport, token_verifier=verify
    )
    provider._test_context = current_context
    return provider


def test_begin_uses_code_pkce_s256_nonce_and_exact_callback(settings):
    provider = _provider()
    context = _context()
    provider._test_context[0] = context

    challenge = provider.begin(context)
    query = parse_qs(urlsplit(challenge.authorization_url).query)

    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["nonce"]
    assert query["redirect_uri"] == [CALLBACK]
    assert query["scope"] == ["openid profile email groups"]


def test_complete_normalizes_verified_profile_and_complete_groups(settings):
    provider = _provider()
    context = _context()
    provider._test_context[0] = context

    result = provider.complete(_callback(code="code-1", state="state-1"))

    assert isinstance(result, VerifiedIdentity)
    assert result.subject == "subject-42"
    assert result.source_id == ISSUER
    assert result.groups.status is ExternalGroupSnapshotStatus.COMPLETE
    assert result.groups.groups == ("engineering",)
    assert result.attributes["email"].provenance.value == "verified_ownership"


def test_userinfo_subject_mismatch_fails_without_identity(settings):
    transport = FakeTransport()
    transport.userinfo_sub = "different-subject"
    provider = _provider(transport)
    provider._test_context[0] = _context()

    result = provider.complete(_callback(code="code-1"))

    assert result == AuthenticationFailure(
        AuthenticationFailureCategory.INVALID_RESULT
    )


def test_nonce_mismatch_is_rejected(settings):
    transport = FakeTransport()
    provider = OIDCProvider(
        _config(),
        transport=transport,
        token_verifier=lambda *_args: {
            "iss": ISSUER,
            "sub": "subject-42",
            "aud": "atlas",
            "nonce": "wrong-nonce",
        },
    )

    result = provider.complete(_callback(code="code-1"))

    assert result == AuthenticationFailure(
        AuthenticationFailureCategory.INVALID_RESULT
    )


def test_discovery_issuer_mismatch_is_rejected(settings):
    class WrongIssuerTransport(FakeTransport):
        def get_json(self, url, *, bearer_token=None):
            value = dict(super().get_json(url, bearer_token=bearer_token))
            if url == DISCOVERY:
                value["issuer"] = "https://attacker.example"
            return value

    provider = _provider(WrongIssuerTransport())

    try:
        provider.begin(_context())
    except OIDCProtocolError as error:
        assert "issuer mismatch" in str(error)
    else:
        raise AssertionError("issuer mismatch was accepted")


def test_runtime_source_must_match_expected_issuer(settings):
    provider = _provider()
    wrong_source = RedirectFlowContext(
        provider_id=PROVIDER_ID,
        source_id="https://replacement.example",
        attempt_id="attempt-source-mismatch",
        correlation_id="correlation-source-mismatch",
        deadline=datetime.now(UTC) + timedelta(minutes=1),
        callback_url=CALLBACK,
    )

    with pytest.raises(OIDCProtocolError):
        provider.begin(wrong_source)

    result = provider.complete(
        RedirectCallbackContext(
            provider_id=PROVIDER_ID,
            source_id=wrong_source.source_id,
            attempt_id=wrong_source.attempt_id,
            correlation_id=wrong_source.correlation_id,
            deadline=wrong_source.deadline,
            callback_parameters={"code": "one-use"},
            callback_url=CALLBACK,
        )
    )
    assert result == AuthenticationFailure(
        AuthenticationFailureCategory.INVALID_RESULT
    )


def test_id_token_signature_algorithm_issuer_audience_and_time_validation():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    base_claims = {
        "iss": ISSUER,
        "sub": "subject-42",
        "aud": "atlas",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    metadata = {"jwks_uri": f"{ISSUER}/jwks"}
    transport = FakeTransport()
    original_get = transport.get_json

    def get_json(url, *, bearer_token=None):
        if url == metadata["jwks_uri"]:
            return {
                "keys": [
                    jwt.algorithms.RSAAlgorithm.to_jwk(
                        private_key.public_key(), as_dict=True
                    )
                ]
            }
        return original_get(url, bearer_token=bearer_token)

    transport.get_json = get_json
    provider = OIDCProvider(_config(), transport=transport)

    valid = jwt.encode(base_claims, private_key, algorithm="RS256")
    claims = provider._verify_id_token(valid, metadata, provider.config)
    assert claims["sub"] == "subject-42"

    invalid_claim_sets = (
        {**base_claims, "iss": "https://replacement.example"},
        {**base_claims, "aud": "different-client"},
        {
            **base_claims,
            "exp": int((now - timedelta(minutes=1)).timestamp()),
        },
    )
    for claims in invalid_claim_sets:
        token = jwt.encode(claims, private_key, algorithm="RS256")
        with pytest.raises(jwt.PyJWTError):
            provider._verify_id_token(token, metadata, provider.config)

    wrong_signature = jwt.encode(base_claims, other_key, algorithm="RS256")
    with pytest.raises(jwt.InvalidSignatureError):
        provider._verify_id_token(wrong_signature, metadata, provider.config)

    symmetric = jwt.encode(base_claims, "shared-secret" * 3, algorithm="HS256")
    with pytest.raises(OIDCProtocolError, match="algorithm"):
        provider._verify_id_token(symmetric, metadata, provider.config)


def test_trusted_jwks_key_rotation_accepts_new_kid():
    keys = {
        "old": rsa.generate_private_key(public_exponent=65537, key_size=2048),
        "new": rsa.generate_private_key(public_exponent=65537, key_size=2048),
    }
    now = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "sub": "subject-42",
        "aud": "atlas",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }

    metadata = {"jwks_uri": f"{ISSUER}/jwks"}
    transport = FakeTransport()
    original_get = transport.get_json

    def get_json(url, *, bearer_token=None):
        if url == metadata["jwks_uri"]:
            return {
                "keys": [
                    {
                        **jwt.algorithms.RSAAlgorithm.to_jwk(
                            key.public_key(), as_dict=True
                        ),
                        "kid": kid,
                    }
                    for kid, key in keys.items()
                ]
            }
        return original_get(url, bearer_token=bearer_token)

    transport.get_json = get_json
    provider = OIDCProvider(_config(), transport=transport)

    for kid in ("old", "new"):
        token = jwt.encode(
            claims, keys[kid], algorithm="RS256", headers={"kid": kid}
        )
        assert (
            provider._verify_id_token(token, metadata, provider.config)["sub"]
            == "subject-42"
        )


def test_health_and_remote_logout_are_allowlisted_and_token_free():
    transport = FakeTransport()
    original_get = transport.get_json

    def get_json(url, *, bearer_token=None):
        value = original_get(url, bearer_token=bearer_token)
        if url == DISCOVERY:
            return {
                **value,
                "end_session_endpoint": f"{ISSUER}/logout",
            }
        return value

    transport.get_json = get_json
    provider = OIDCProvider(_config(remoteLogout=True), transport=transport)

    assert provider.health() == {
        "providerId": PROVIDER_ID,
        "status": "available",
        "category": "ok",
    }
    target = provider.remote_logout("https://atlas.example/login?logged-out=1")
    assert target is not None
    assert target.startswith(f"{ISSUER}/logout?")
    assert "token" not in target.casefold()


def test_transport_rejects_metadata_dns_and_requires_private_allowlist(
    monkeypatch,
):
    transport = RequestsOIDCTransport(_config())
    monkeypatch.setattr(
        "atlas_plugin_auth_oidc.provider.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (None, None, None, None, ("169.254.169.254", 443))
        ],
    )
    with pytest.raises(OIDCProtocolError, match="prohibited"):
        transport._validate_resolved_destination(DISCOVERY)

    monkeypatch.setattr(
        "atlas_plugin_auth_oidc.provider.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.5", 443))],
    )
    with pytest.raises(OIDCProtocolError, match="allowlisted"):
        transport._validate_resolved_destination(DISCOVERY)

    allowed = RequestsOIDCTransport(_config(allowedDestinations=[ISSUER]))
    allowed._validate_resolved_destination(DISCOVERY)


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


@contextmanager
def _serve_https(
    handler_cls: type[http.server.BaseHTTPRequestHandler],
    cert_path: str,
    key_path: str,
):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    server = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _generate_self_signed_cert(hostname: str, tmp_path) -> tuple[str, str]:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    now = dt.datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(hostname)]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return str(cert_path), str(key_path)


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
        "atlas_plugin_auth_oidc.provider.socket.getaddrinfo", fake_getaddrinfo
    )
    return calls


def test_get_json_resolves_hostname_exactly_once(monkeypatch):
    with _serve(_JsonOkHandler) as (server_host, server_port):
        calls = _mock_resolution(monkeypatch, {"localhost": server_host})
        origin = f"http://localhost:{server_port}"
        transport = RequestsOIDCTransport(
            _config(allowDevelopmentHttp=True, allowedDestinations=[origin])
        )

        result = transport.get_json(f"{origin}/discovery")

        assert result == {"ok": True}
        assert calls == ["localhost"]


def test_post_form_resolves_hostname_exactly_once(monkeypatch):
    with _serve(_JsonOkHandler) as (server_host, server_port):
        calls = _mock_resolution(monkeypatch, {"localhost": server_host})
        origin = f"http://localhost:{server_port}"
        transport = RequestsOIDCTransport(
            _config(allowDevelopmentHttp=True, allowedDestinations=[origin])
        )

        result = transport.post_form(f"{origin}/token", {"grant_type": "x"})

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
            "atlas_plugin_auth_oidc.provider.socket.getaddrinfo",
            fake_getaddrinfo,
        )
        origin = f"http://{hostname}:{server_port}"
        transport = RequestsOIDCTransport(
            _config(allowDevelopmentHttp=True, allowedDestinations=[origin])
        )

        result = transport.get_json(f"{origin}/discovery")

        assert result == {"ok": True}
        assert calls == [hostname]


def test_tls_certificate_is_validated_against_original_hostname_not_pinned_ip(
    monkeypatch, tmp_path
):
    """The connection is pinned to a bare IP address the server's
    certificate was never issued for -- this only succeeds if the TLS
    handshake presents and verifies the *original hostname* as SNI, not the
    IP (Host header and TLS SNI are unaffected)."""
    hostname = "op.example.test"
    cert_path, key_path = _generate_self_signed_cert(hostname, tmp_path)

    with _serve_https(_JsonOkHandler, cert_path, key_path) as (
        server_host,
        server_port,
    ):
        _mock_resolution(monkeypatch, {hostname: server_host})
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", cert_path)
        origin = f"https://{hostname}:{server_port}"
        transport = RequestsOIDCTransport(
            _config(allowDevelopmentHttp=True, allowedDestinations=[origin])
        )

        result = transport.get_json(f"{origin}/discovery")

        assert result == {"ok": True}


def test_redirect_provider_passes_public_contract(settings):
    attempt_number = 0
    contexts = {}

    def provider_factory():
        nonlocal attempt_number
        attempt_number += 1
        transport = FakeTransport()
        context = _context(f"attempt-{attempt_number}")
        contexts["current"] = context
        provider = _provider(transport)
        provider._test_context[0] = context
        contexts["transport"] = transport
        return provider

    def callback(_challenge, **parameters):
        context = contexts["current"]
        return RedirectCallbackContext(
            provider_id=PROVIDER_ID,
            source_id=ISSUER,
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
            source_id=ISSUER,
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
