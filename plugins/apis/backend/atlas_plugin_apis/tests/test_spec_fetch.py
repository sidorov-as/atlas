"""Tests for `fetch_spec_content`/`resolve_api_spec_url`.

The SSRF-defense mechanics themselves (address verification, redirect
re-validation, DNS-rebinding immunity, the streaming byte cap) are
exhaustively unit-tested in isolation at `atlas_plugin_api.safe_http`'s own
test suite. These tests instead confirm the *wiring*: that `spec_fetch.py`
actually routes through `safe_request`, translates every rejection into the
same `None` outcome `resolve_api_spec_url` already treated as "fetch
failed," and correctly layers its own YAML/JSON parse-size limit and
`ATLAS_APIS_SPEC_URL_ALLOWLIST` allowlist on top.
"""

from __future__ import annotations

import datetime
import http.server
import ipaddress
import socket
import ssl
import threading
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from atlas_plugin_api import safe_http
from server.apps.catalog.tests.factories import create_api, create_system

from atlas_plugin_apis import spec_fetch
from atlas_plugin_apis.spec_fetch import fetch_spec_content, resolve_api_spec_url

pytestmark = pytest.mark.django_db

SPEC_BODY = b'{"openapi": "3.0.0", "info": {"title": "t", "version": "1"}}'


# ---------------------------------------------------------------------------
# Test server helpers (same technique as `atlas_plugin_api.tests.test_safe_http`)
# ---------------------------------------------------------------------------


class _QuietHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


class _OkHandler(_QuietHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(len(SPEC_BODY)))
        self.end_headers()
        self.wfile.write(SPEC_BODY)


class _RedirectToOtherHostHandler(_QuietHandler):
    def do_GET(self) -> None:
        self.send_response(302)
        self.send_header("Location", "http://evil.test:1/somewhere")
        self.end_headers()


class _BigBodyHandler(_QuietHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Connection", "close")
        self.end_headers()
        chunk = b"x" * 65536
        for _ in range(50):  # 50 * 64KiB ~= 3.2MiB
            try:
                self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                return


class _DeeplyNestedHandler(_QuietHandler):
    def do_GET(self) -> None:
        body = (b"[" * 150) + (b"]" * 150)
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _WideFlatHandler(_QuietHandler):
    def do_GET(self) -> None:
        body = ("[" + ",".join("0" for _ in range(250_000)) + "]").encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def _serve(handler_cls: type[http.server.BaseHTTPRequestHandler]) -> Iterator[tuple[str, int]]:
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
    handler_cls: type[http.server.BaseHTTPRequestHandler], cert_path: str, key_path: str
) -> Iterator[tuple[str, int]]:
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
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname)]), critical=False)
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


def _mock_resolution(monkeypatch: pytest.MonkeyPatch, answers: dict[str, str]) -> list[str]:
    """See `atlas_plugin_api.tests.test_safe_http._mock_resolution` for why a
    literal IP address must pass through untouched (that's `urllib3` doing
    its own connect-time bookkeeping on an address already verified, not a
    fresh hostname resolution)."""
    calls: list[str] = []

    def fake_getaddrinfo(host, port=None, *args, **kwargs):
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port or 0))]
        calls.append(host)
        if host not in answers:
            raise AssertionError(f"unexpected DNS lookup for {host!r}")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (answers[host], port or 0))]

    monkeypatch.setattr(safe_http.socket, "getaddrinfo", fake_getaddrinfo)
    return calls


# ---------------------------------------------------------------------------
# Fixtures for the `resolve_api_spec_url` DB-backed test
# ---------------------------------------------------------------------------


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="billing-api", owner=group, system=system)


# ---------------------------------------------------------------------------
# Address verification: rejected before ever connecting
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",  # IPv4 loopback
        "169.254.169.254",  # IPv4 link-local / cloud metadata
        "10.0.0.5",  # RFC1918
    ],
)
def test_fetch_rejects_before_connecting_to_a_disallowed_ipv4_address(
    monkeypatch: pytest.MonkeyPatch, ip: str
) -> None:
    def fake_getaddrinfo(host, *args, **kwargs):
        assert host == "attacker.test"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    monkeypatch.setattr(safe_http.socket, "getaddrinfo", fake_getaddrinfo)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("must not connect to a disallowed address")

    monkeypatch.setattr(safe_http.requests.Session, "request", fail_if_called)

    assert fetch_spec_content("https://attacker.test/openapi.yaml") is None


@pytest.mark.parametrize(
    "ip",
    [
        "::1",  # IPv6 loopback
        "fe80::1",  # IPv6 link-local
    ],
)
def test_fetch_rejects_before_connecting_to_a_disallowed_ipv6_address(
    monkeypatch: pytest.MonkeyPatch, ip: str
) -> None:
    def fake_getaddrinfo(host, *args, **kwargs):
        assert host == "attacker.test"
        return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", (ip, 0, 0, 0))]

    monkeypatch.setattr(safe_http.socket, "getaddrinfo", fake_getaddrinfo)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("must not connect to a disallowed address")

    monkeypatch.setattr(safe_http.requests.Session, "request", fail_if_called)

    assert fetch_spec_content("https://attacker.test/openapi.yaml") is None


# ---------------------------------------------------------------------------
# Redirect handling and DNS rebinding
# ---------------------------------------------------------------------------


def test_fetch_rejects_a_redirect_to_a_disallowed_address(
    monkeypatch: pytest.MonkeyPatch, settings
) -> None:
    with _serve(_RedirectToOtherHostHandler) as (server_host, server_port):
        settings.ATLAS_APIS_SPEC_URL_ALLOWLIST = ["safe.test"]
        _mock_resolution(monkeypatch, {"safe.test": server_host, "evil.test": "10.0.0.5"})

        assert fetch_spec_content(f"http://safe.test:{server_port}/start") is None


def test_fetch_is_immune_to_dns_rebinding(
    monkeypatch: pytest.MonkeyPatch, settings
) -> None:
    with _serve(_OkHandler) as (server_host, server_port):
        settings.ATLAS_APIS_SPEC_URL_ALLOWLIST = ["rebind.test"]
        calls = _mock_resolution(monkeypatch, {"rebind.test": server_host})

        content = fetch_spec_content(f"http://rebind.test:{server_port}/openapi.yaml")

        assert content == SPEC_BODY.decode()
        assert calls == ["rebind.test"]


# ---------------------------------------------------------------------------
# Bounded streaming reads
# ---------------------------------------------------------------------------


def test_fetch_rejects_an_oversized_response(
    monkeypatch: pytest.MonkeyPatch, settings
) -> None:
    monkeypatch.setattr(spec_fetch, "MAX_SPEC_RESPONSE_BYTES", 1024)
    with _serve(_BigBodyHandler) as (server_host, server_port):
        settings.ATLAS_APIS_SPEC_URL_ALLOWLIST = ["big.test"]
        _mock_resolution(monkeypatch, {"big.test": server_host})

        assert fetch_spec_content(f"http://big.test:{server_port}/openapi.yaml") is None


# ---------------------------------------------------------------------------
# YAML/JSON parse size and nesting-depth limits
# ---------------------------------------------------------------------------


def test_fetch_rejects_a_deeply_nested_body(
    monkeypatch: pytest.MonkeyPatch, settings
) -> None:
    with _serve(_DeeplyNestedHandler) as (server_host, server_port):
        settings.ATLAS_APIS_SPEC_URL_ALLOWLIST = ["nested.test"]
        _mock_resolution(monkeypatch, {"nested.test": server_host})

        assert fetch_spec_content(f"http://nested.test:{server_port}/openapi.yaml") is None


def test_fetch_rejects_a_body_with_too_many_nodes(
    monkeypatch: pytest.MonkeyPatch, settings
) -> None:
    with _serve(_WideFlatHandler) as (server_host, server_port):
        settings.ATLAS_APIS_SPEC_URL_ALLOWLIST = ["wide.test"]
        _mock_resolution(monkeypatch, {"wide.test": server_host})

        assert fetch_spec_content(f"http://wide.test:{server_port}/openapi.yaml") is None


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_fetch_resolves_a_legitimate_https_spec_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """No false-positive regression: an ordinary HTTPS fetch to a verified
    address still succeeds. The test server is necessarily on loopback, so
    `_is_allowed_address` is patched open here — address policy itself is
    covered by the dedicated rejection tests above and by
    `atlas_plugin_api.safe_http`'s own suite."""
    hostname = "safe.example.test"
    cert_path, key_path = _generate_self_signed_cert(hostname, tmp_path)

    with _serve_https(_OkHandler, cert_path, key_path) as (server_host, server_port):
        _mock_resolution(monkeypatch, {hostname: server_host})
        monkeypatch.setattr(safe_http, "_is_allowed_address", lambda ip: True)
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", cert_path)

        content = fetch_spec_content(f"https://{hostname}:{server_port}/openapi.yaml")

        assert content == SPEC_BODY.decode()


def test_fetch_resolves_an_allowlisted_internal_host(
    monkeypatch: pytest.MonkeyPatch, settings
) -> None:
    """Exercises the real `ATLAS_APIS_SPEC_URL_ALLOWLIST` mechanism
    end-to-end: the server is plain HTTP on loopback (both normally
    disallowed) and succeeds only because its hostname is allowlisted."""
    with _serve(_OkHandler) as (server_host, server_port):
        settings.ATLAS_APIS_SPEC_URL_ALLOWLIST = ["internal.test"]
        _mock_resolution(monkeypatch, {"internal.test": server_host})

        content = fetch_spec_content(f"http://internal.test:{server_port}/openapi.yaml")

        assert content == SPEC_BODY.decode()


# ---------------------------------------------------------------------------
# Behavior preservation: a rejected/unsafe fetch is indistinguishable
# from any other failed fetch to `resolve_api_spec_url`
# ---------------------------------------------------------------------------


def test_resolve_api_spec_url_treats_a_rejected_fetch_like_any_failed_fetch(
    monkeypatch: pytest.MonkeyPatch, api
) -> None:
    details = api.api_details
    details.spec_content = "existing: content"
    details.spec_url = "https://attacker.test/openapi.yaml"

    monkeypatch.setattr(spec_fetch, "fetch_spec_content", lambda url: None)

    resolve_api_spec_url(details)

    assert details.spec_resolve_failed is True
    assert details.spec_content == "existing: content"
