"""SSRF-safe outbound HTTP fetch helper.

A shared primitive for making outbound HTTP requests to operator- or
user-supplied URLs/hostnames without exposing the backend to SSRF or
DNS-rebinding. Used by call sites that would otherwise trust a
caller-supplied hostname without verifying the destination isn't
internal — `atlas_plugin_apis.spec_fetch` calls `safe_request`, while the
OIDC/Gitea auth providers' token-exchange and userinfo calls reuse its
pinned-connection adapter instead of `requests.get`/`.post` directly.

Threat model this defends against: a naive
`requests.get(user_supplied_url)` is unsafe even if the hostname is checked
before the call, two ways —

- **SSRF**: the hostname resolves to a private/loopback/link-local address
  (RFC1918, `127.0.0.1`, the `169.254.169.254` cloud-metadata case, etc.),
  reaching a network-internal service the caller was never meant to reach.
- **DNS rebinding**: an earlier "safe" resolution doesn't bind the later TCP
  connect — `requests` re-resolves the hostname itself when it actually
  connects, so an attacker-controlled DNS answer can serve a public address
  to the pre-check resolution and a private one moments later, at connect
  time.

`safe_request` defends against both by resolving the hostname once,
rejecting the request if any resolved address is disallowed, and
connecting to that specific verified address directly — never re-resolving
the hostname at connect time — while still presenting the original hostname
as the `Host` header and TLS SNI value so certificate validation is
unaffected. Redirects are re-validated the same way, hop by hop, up to a
caller-configurable limit, and the response body is read incrementally so an
oversized response is aborted mid-stream rather than fully buffered.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import SplitResult, urljoin, urlsplit

import requests
from requests.adapters import HTTPAdapter

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class SafeHttpError(Exception):
    """Base class for every error `safe_request` raises. A caller that only
    cares whether a fetch was rejected for safety (as opposed to some other
    failure) can catch this without matching each specific subclass."""


class UnsafeUrlError(SafeHttpError, ValueError):
    """The request URL itself is disallowed before any DNS lookup or network
    connection is attempted: embedded credentials, a fragment, or a
    non-HTTPS scheme without `allow_http=True`."""


class BlockedAddressError(SafeHttpError):
    """Every address `hostname` resolved to falls in a private, loopback,
    link-local, multicast, unique-local, or otherwise IANA-reserved range.
    Raised for the original request URL and
    for any redirect target re-validated during the request."""

    def __init__(self, hostname: str, addresses: Sequence[str]) -> None:
        super().__init__(
            f"{hostname!r} resolved only to disallowed addresses: "
            f"{', '.join(addresses)}"
        )
        self.hostname = hostname
        self.addresses = tuple(addresses)


class TooManyRedirectsError(SafeHttpError):
    """The response redirected more times than `max_redirects` allows,
    including the `max_redirects=0` case ("never follow")."""

    def __init__(self, max_redirects: int, location: str) -> None:
        super().__init__(
            f"redirect to {location!r} exceeds max_redirects={max_redirects}"
        )
        self.max_redirects = max_redirects
        self.location = location


class ResponseTooLargeError(SafeHttpError):
    """The response body exceeded `max_response_bytes` while being read;
    raised mid-stream, independent of what `Content-Length` declared."""

    def __init__(self, max_response_bytes: int) -> None:
        super().__init__(
            f"response body exceeded max_response_bytes={max_response_bytes}"
        )
        self.max_response_bytes = max_response_bytes


@dataclass(frozen=True)
class SafeHttpResponse:
    """The result of a successful `safe_request` call.

    `resolved_address` is the specific verified IP the connection was
    pinned to (the final one, after any redirects) — exposed for caller
    logging/debugging, never for reuse in a follow-up request.
    """

    status_code: int
    headers: Mapping[str, str]
    url: str
    resolved_address: str
    content: bytes


def safe_request(
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    data: Any = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    allow_http: bool = False,
    exempt_hosts: Sequence[str] = (),
) -> SafeHttpResponse:
    """Make an SSRF-safe HTTP request to `url`.

    Raises `UnsafeUrlError` if `url` carries embedded credentials, a
    fragment, or a disallowed scheme; `BlockedAddressError` if `url`'s
    hostname (or any redirect target's hostname) resolves only to a
    private/loopback/link-local/reserved address; `TooManyRedirectsError`
    if following a redirect would exceed `max_redirects`; and
    `ResponseTooLargeError` if the response body exceeds
    `max_response_bytes`.

    `max_redirects=0` means no redirect is ever followed. `allow_http=True`
    opts this whole call into the `http://` scheme; the default rejects it.

    `exempt_hosts` additionally opts specific, exact hostnames out of the
    reserved-address requirement — for a caller with its own
    operator-configured allowlist of hosts known to be intentionally
    internal (e.g. the APIs plugin's `spec_url` allowlist). Checked fresh
    per hop against that hop's own hostname, so a redirect from an exempted
    host to a *different*, non-exempted host gets no exemption — the
    allowlist can't be used to pivot into an arbitrary address via a
    redirect.
    """
    current_url = url
    current_method = method
    current_data = data
    hops = 0

    while True:
        parsed = _validate_url(current_url, allow_http=allow_http)
        # Resolved and verified fresh for every hop (including redirect
        # targets) so a redirect can't smuggle a disallowed address past the
        # original check, and so nothing here ever re-resolves the *same*
        # hostname after it's been pinned for a hop (the DNS-rebinding
        # defense: see `_do_hop`, which connects to `address` directly).
        address = _resolve_and_verify(
            parsed.hostname, allow_reserved=parsed.hostname in exempt_hosts
        )
        status, resp_headers, location, content = _do_hop(
            parsed,
            address,
            method=current_method,
            headers=headers,
            data=current_data,
            timeout=timeout,
            max_response_bytes=max_response_bytes,
        )

        if status in _REDIRECT_STATUSES and location:
            if hops >= max_redirects:
                raise TooManyRedirectsError(max_redirects, location)
            hops += 1
            current_url = urljoin(current_url, location)
            if status == 303 or (status in (301, 302) and current_method == "POST"):
                current_method = "GET"
                current_data = None
            continue

        return SafeHttpResponse(
            status_code=status,
            headers=resp_headers,
            url=current_url,
            resolved_address=address,
            content=content,
        )


def _validate_url(url: str, *, allow_http: bool) -> SplitResult:
    """Reject a request URL before any DNS lookup or network connection is
    attempted."""
    parsed = urlsplit(url)
    if parsed.fragment:
        raise UnsafeUrlError(f"URL must not contain a fragment: {url!r}")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError(f"URL must not contain embedded credentials: {url!r}")
    scheme = parsed.scheme.lower()
    if scheme == "http":
        if not allow_http:
            raise UnsafeUrlError(
                f"http:// is not allowed unless allow_http=True: {url!r}"
            )
    elif scheme != "https":
        raise UnsafeUrlError(f"unsupported scheme {scheme!r}: {url!r}")
    if not parsed.hostname:
        raise UnsafeUrlError(f"URL has no hostname: {url!r}")
    return parsed


def _is_allowed_address(ip: str) -> bool:
    """`ipaddress`-backed check for "publicly routable, not internal"."""
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        # `::ffff:127.0.0.1` etc. — verify the mapped v4 address, not the
        # (technically "global") v6 wrapper around it.
        addr = addr.ipv4_mapped
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _resolve_and_verify(hostname: str, *, allow_reserved: bool = False) -> str:
    """Resolve `hostname` once and return a single verified address to
    connect to. Rejects the request outright if *any* resolved address is
    disallowed, not only when every address is (prefer
    reject-if-any-ambiguity for safety) — i.e. "reject the
    request if any resolved address falls in a ... reserved range" — unless
    `allow_reserved` is set, in which case `hostname` still gets resolved
    and pinned exactly once (the DNS-rebinding defense applies regardless),
    it just isn't rejected for landing on a private/reserved address."""
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        # DNS failure is treated as "can't verify it's safe" and fails
        # closed, the same as an explicitly disallowed address.
        raise BlockedAddressError(hostname, ()) from exc

    addresses: list[str] = []
    seen: set[str] = set()
    for info in infos:
        ip = info[4][0]
        if ip not in seen:
            seen.add(ip)
            addresses.append(ip)

    if not allow_reserved:
        disallowed = [ip for ip in addresses if not _is_allowed_address(ip)]
        if disallowed:
            raise BlockedAddressError(hostname, disallowed)
    return addresses[0]


class _PinnedHTTPAdapter(HTTPAdapter):
    """A `requests` transport adapter that pins TLS verification (and, for
    HTTPS, the SNI value) to `hostname` regardless of what host it actually
    connects to. `_do_hop` rewrites the request URL's host to the
    pre-verified IP address before sending; without this adapter, `requests`
    would present and validate that IP for TLS instead of `hostname` (design
    doc's flagged TLS-validation risk)."""

    def __init__(self, *, hostname: str, is_https: bool) -> None:
        self._hostname = hostname
        self._is_https = is_https
        super().__init__()

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        if self._is_https:
            kwargs["assert_hostname"] = self._hostname
            kwargs["server_hostname"] = self._hostname
        super().init_poolmanager(*args, **kwargs)


def _authority(host: str, port: int | None) -> str:
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    return host if port is None else f"{host}:{port}"


def _read_bounded(response: requests.Response, max_response_bytes: int) -> bytes:
    """Read `response`'s body incrementally, aborting as soon as
    `max_response_bytes` is exceeded — independent of what `Content-Length`
    declared. Requires the caller to have made the
    request with `stream=True`, or the body would already be fully buffered
    before this ever runs."""
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_response_bytes:
            raise ResponseTooLargeError(max_response_bytes)
        chunks.append(chunk)
    return b"".join(chunks)


def _do_hop(
    parsed: SplitResult,
    address: str,
    *,
    method: str,
    headers: Mapping[str, str] | None,
    data: Any,
    timeout: float,
    max_response_bytes: int,
) -> tuple[int, dict[str, str], str | None, bytes]:
    """Perform one HTTP request/response, connected to the already-verified
    `address`, and return `(status, headers, location, content)`. Redirects
    are never followed here — `safe_request`'s loop re-validates and issues
    each hop itself."""
    hostname = parsed.hostname
    assert hostname is not None
    is_https = parsed.scheme == "https"
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    pinned_url = f"{parsed.scheme}://{_authority(address, parsed.port)}{path}"

    send_headers = dict(headers or {})
    send_headers.setdefault("Host", _authority(hostname, parsed.port))

    adapter = _PinnedHTTPAdapter(hostname=hostname, is_https=is_https)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    try:
        response = session.request(
            method,
            pinned_url,
            headers=send_headers,
            data=data,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
        )
        try:
            content = _read_bounded(response, max_response_bytes)
        finally:
            response.close()
        return (
            response.status_code,
            dict(response.headers),
            response.headers.get("Location"),
            content,
        )
    finally:
        session.close()
