"""Unit tests for `atlas_plugin_api.safe_http`.

Address-verification rules are tested directly against `_is_allowed_address`/
`_resolve_and_verify` (no network needed). HTTP mechanics (redirects,
streaming byte cap, TLS hostname pinning) are tested against real local
`http.server` instances, with DNS mocked via `socket.getaddrinfo` and, where
a test's own local server would otherwise be rejected for being on loopback,
`_is_allowed_address` patched open — so the two concerns (is this address
allowed; does the transport behave correctly once it is) are verified
independently.
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
from atlas_plugin_api.safe_http import (
    BlockedAddressError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    UnsafeUrlError,
    safe_request,
)

# ---------------------------------------------------------------------------
# Test server helpers
# ---------------------------------------------------------------------------


class _QuietHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


@contextmanager
def _serve(
    handler_cls: type[http.server.BaseHTTPRequestHandler],
) -> Iterator[tuple[str, int]]:
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
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(hostname)]), critical=False
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


def _mock_resolution(
    monkeypatch: pytest.MonkeyPatch, answers: dict[str, str]
) -> list[str]:
    """Point `socket.getaddrinfo` at fixed answers for specific hostnames and
    return the list of hostnames it was actually asked to resolve, in order.

    `safe_http` and `urllib3` share the same stdlib `socket` module, so this
    also intercepts the *second* `getaddrinfo` call `urllib3` makes when it
    actually connects to our already-pinned IP. A literal IP address always
    "resolves" to itself with no real lookup (true of the real `getaddrinfo`
    too) and is passed through without being counted — it isn't a fresh
    hostname resolution, just `urllib3` doing its normal connect-time
    bookkeeping on an address `safe_http` already verified.
    """
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
# Address verification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ip",
    [
        "10.0.0.5",  # RFC1918
        "172.16.0.5",  # RFC1918
        "192.168.1.5",  # RFC1918
        "127.0.0.1",  # IPv4 loopback
        "169.254.169.254",  # IPv4 link-local / cloud metadata
        "224.0.0.1",  # IPv4 multicast
        "0.0.0.0",  # unspecified
    ],
)
def test_is_allowed_address_rejects_ipv4_special_ranges(ip: str) -> None:
    assert safe_http._is_allowed_address(ip) is False


@pytest.mark.parametrize(
    "ip",
    [
        "::1",  # IPv6 loopback
        "fe80::1",  # IPv6 link-local
        "fc00::1",  # IPv6 unique-local
        "ff02::1",  # IPv6 multicast
        "::ffff:127.0.0.1",  # IPv4-mapped loopback
        "::ffff:10.0.0.5",  # IPv4-mapped RFC1918
    ],
)
def test_is_allowed_address_rejects_ipv6_special_ranges(ip: str) -> None:
    assert safe_http._is_allowed_address(ip) is False


def test_is_allowed_address_accepts_publicly_routable_addresses() -> None:
    assert safe_http._is_allowed_address("93.184.216.34") is True
    assert safe_http._is_allowed_address("2606:2800:220:1:248:1893:25c8:1946") is True


def test_rejects_before_connecting_when_any_resolved_address_is_disallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hostname that resolves to a mix of public and private addresses is
    rejected outright, not partially trusted (prefer
    reject-if-any-ambiguity for safety)."""

    def fake_getaddrinfo(host, *args, **kwargs):
        assert host == "mixed.test"
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0)),
        ]

    monkeypatch.setattr(safe_http.socket, "getaddrinfo", fake_getaddrinfo)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("must not connect once any resolved address is disallowed")

    monkeypatch.setattr(safe_http.requests.Session, "request", fail_if_called)

    with pytest.raises(BlockedAddressError) as exc_info:
        safe_request("https://mixed.test/spec.yaml")

    assert "10.0.0.5" in str(exc_info.value)


def test_dns_rebinding_does_not_bypass_the_initial_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hostname is resolved once per hop and pinned for that hop's entire
    connection — a DNS answer that would differ on a second lookup is never
    consulted, because there is no second lookup."""
    with _serve(_OkHandler) as (server_host, server_port):
        calls = _mock_resolution(monkeypatch, {"rebind.test": server_host})
        monkeypatch.setattr(safe_http, "_is_allowed_address", lambda ip: True)

        response = safe_request(f"http://rebind.test:{server_port}/ok", allow_http=True)

        assert response.status_code == 200
        assert response.content == b"ok"
        assert calls == ["rebind.test"]


# ---------------------------------------------------------------------------
# Per-hostname reserved-address exemption (`exempt_hosts`, for a caller's own
# operator-configured allowlist)
# ---------------------------------------------------------------------------


def test_exempt_hosts_allows_a_reserved_address_for_that_exact_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real local test server binds to loopback — a genuinely reserved
    address, normally rejected outright — so a successful fetch here can only
    mean `exempt_hosts` actually bypassed that check for this exact host."""
    with _serve(_OkHandler) as (server_host, server_port):
        _mock_resolution(monkeypatch, {"internal.test": server_host})

        response = safe_request(
            f"http://internal.test:{server_port}/ok",
            allow_http=True,
            exempt_hosts=["internal.test"],
        )

        assert response.status_code == 200
        assert response.content == b"ok"
        assert response.resolved_address == server_host


def test_exempt_hosts_does_not_extend_to_a_redirect_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exempted host redirecting elsewhere doesn't hand its exemption to
    wherever it points — each hop's hostname is checked against
    `exempt_hosts` on its own, not the request's original hostname."""
    with _serve(_RedirectToOtherHostHandler) as (server_host, server_port):
        _mock_resolution(
            monkeypatch, {"safe.test": server_host, "evil.test": "10.0.0.5"}
        )

        with pytest.raises(BlockedAddressError) as exc_info:
            safe_request(
                f"http://safe.test:{server_port}/start",
                allow_http=True,
                exempt_hosts=["safe.test"],
            )

        assert exc_info.value.hostname == "evil.test"


# ---------------------------------------------------------------------------
# URL/scheme constraints
# ---------------------------------------------------------------------------


def test_rejects_url_with_embedded_credentials() -> None:
    with pytest.raises(UnsafeUrlError):
        safe_request("https://user:pass@example.test/spec.yaml")


def test_rejects_url_with_fragment() -> None:
    with pytest.raises(UnsafeUrlError):
        safe_request("https://example.test/spec.yaml#section")


def test_rejects_http_by_default() -> None:
    with pytest.raises(UnsafeUrlError):
        safe_request("http://example.test/spec.yaml")


def test_allows_http_when_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    with _serve(_OkHandler) as (server_host, server_port):
        _mock_resolution(monkeypatch, {"opt-in.test": server_host})
        monkeypatch.setattr(safe_http, "_is_allowed_address", lambda ip: True)

        response = safe_request(f"http://opt-in.test:{server_port}/ok", allow_http=True)

        assert response.status_code == 200
        assert response.content == b"ok"


# ---------------------------------------------------------------------------
# Redirect handling
# ---------------------------------------------------------------------------


class _OkHandler(_QuietHandler):
    def do_GET(self) -> None:
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _RedirectOnceHandler(_QuietHandler):
    def do_GET(self) -> None:
        if self.path == "/start":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.end_headers()
            return
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _RedirectToOtherHostHandler(_QuietHandler):
    def do_GET(self) -> None:
        self.send_response(302)
        self.send_header("Location", "http://evil.test:1/somewhere")
        self.end_headers()


class _RedirectLoopHandler(_QuietHandler):
    def do_GET(self) -> None:
        self.send_response(302)
        self.send_header("Location", "/start")
        self.end_headers()


def test_follows_redirect_to_a_verified_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _serve(_RedirectOnceHandler) as (server_host, server_port):
        _mock_resolution(monkeypatch, {"safe.test": server_host})
        monkeypatch.setattr(safe_http, "_is_allowed_address", lambda ip: True)

        response = safe_request(
            f"http://safe.test:{server_port}/start", allow_http=True
        )

        assert response.status_code == 200
        assert response.content == b"ok"
        assert response.url.endswith("/ok")


def test_redirect_to_disallowed_address_is_not_followed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _serve(_RedirectToOtherHostHandler) as (server_host, server_port):
        _mock_resolution(
            monkeypatch, {"safe.test": server_host, "evil.test": "10.0.0.5"}
        )
        # Only the test server's own real (loopback) address is "allowed"
        # here — isolates the redirect-following mechanics from address
        # policy, which is covered by the dedicated address-verification
        # tests above.
        monkeypatch.setattr(
            safe_http, "_is_allowed_address", lambda ip: ip == server_host
        )

        with pytest.raises(BlockedAddressError) as exc_info:
            safe_request(f"http://safe.test:{server_port}/start", allow_http=True)

        assert exc_info.value.hostname == "evil.test"


def test_zero_max_redirects_follows_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    with _serve(_RedirectOnceHandler) as (server_host, server_port):
        _mock_resolution(monkeypatch, {"safe.test": server_host})
        monkeypatch.setattr(safe_http, "_is_allowed_address", lambda ip: True)

        with pytest.raises(TooManyRedirectsError):
            safe_request(
                f"http://safe.test:{server_port}/start",
                allow_http=True,
                max_redirects=0,
            )


def test_too_many_redirects_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    with _serve(_RedirectLoopHandler) as (server_host, server_port):
        _mock_resolution(monkeypatch, {"safe.test": server_host})
        monkeypatch.setattr(safe_http, "_is_allowed_address", lambda ip: True)

        with pytest.raises(TooManyRedirectsError):
            safe_request(
                f"http://safe.test:{server_port}/start",
                allow_http=True,
                max_redirects=2,
            )


# ---------------------------------------------------------------------------
# Bounded streaming reads
# ---------------------------------------------------------------------------


class _BigBodyHandler(_QuietHandler):
    chunks_fully_sent = 0

    def do_GET(self) -> None:
        self.send_response(200)
        # No Content-Length at all (a compliant client would otherwise stop
        # reading at whatever length it declares, cap or no cap) — the cap
        # must hold even when the body's true size is only discoverable by
        # reading it.
        self.send_header("Connection", "close")
        self.end_headers()
        chunk = b"x" * 65536
        for _ in range(50):  # 50 * 64KiB ~= 3.2MiB
            try:
                self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                return
            type(self).chunks_fully_sent += 1


def test_oversized_response_is_aborted_mid_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _BigBodyHandler.chunks_fully_sent = 0
    with _serve(_BigBodyHandler) as (server_host, server_port):
        _mock_resolution(monkeypatch, {"safe.test": server_host})
        monkeypatch.setattr(safe_http, "_is_allowed_address", lambda ip: True)

        with pytest.raises(ResponseTooLargeError):
            safe_request(
                f"http://safe.test:{server_port}/big",
                allow_http=True,
                max_response_bytes=1024,
            )

    # The client must have given up long before the server finished writing
    # all 50 chunks — proving the body was never fully buffered first.
    assert _BigBodyHandler.chunks_fully_sent < 50


# ---------------------------------------------------------------------------
# TLS hostname pinning
# ---------------------------------------------------------------------------


def test_tls_certificate_is_validated_against_original_hostname_not_pinned_ip(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """The connection is pinned to a bare IP address, which the server's
    certificate was never issued for — so this only succeeds if the TLS
    handshake presents and verifies the *original hostname*, not the IP
    (the verified address is used for the actual connection, "presenting the
    original hostname as the Host header and
    TLS SNI value")."""
    hostname = "safe.example.test"
    cert_path, key_path = _generate_self_signed_cert(hostname, tmp_path)

    with _serve_https(_OkHandler, cert_path, key_path) as (server_host, server_port):
        _mock_resolution(monkeypatch, {hostname: server_host})
        monkeypatch.setattr(safe_http, "_is_allowed_address", lambda ip: True)
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", cert_path)

        response = safe_request(f"https://{hostname}:{server_port}/")

        assert response.status_code == 200
        assert response.content == b"ok"
        assert response.resolved_address == server_host
