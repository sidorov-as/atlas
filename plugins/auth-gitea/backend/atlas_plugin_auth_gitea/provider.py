"""Gitea Authorization Code + PKCE provider behind the public contract."""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import secrets
import socket
from collections.abc import Mapping
from datetime import datetime
from threading import Lock
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit

import requests
from atlas_plugin_api import (
    AssuredAttribute,
    AttributeProvenance,
    AuthenticationFailure,
    AuthenticationFailureCategory,
    ExternalGroupSnapshot,
    ExternalProfile,
    RedirectCallbackContext,
    RedirectChallenge,
    RedirectFlowContext,
    VerifiedIdentity,
)
from atlas_plugin_api.safe_http import _PinnedHTTPAdapter

from .config import GiteaConfig
from .plugin import PROVIDER_DESCRIPTOR, PROVIDER_ID


class GiteaProtocolError(ValueError):
    """A Gitea response cannot be accepted as a verified identity."""


class GiteaTransport(Protocol):
    def get_profile(
        self, url: str, *, access_token: str
    ) -> Mapping[str, Any]: ...

    def get_health(self, url: str) -> Mapping[str, Any]: ...

    def exchange_code(
        self, url: str, data: Mapping[str, str]
    ) -> Mapping[str, Any]: ...


class AllauthGiteaTransport:
    """Use django-allauth's maintained request-session integration.

    Atlas owns callback correlation and normalized results, while the pinned
    allauth Gitea adapter remains the baseline for endpoints and HTTP behavior.
    Imports stay lazy so the static plugin descriptor remains Django-safe.
    """

    def __init__(self, config: GiteaConfig) -> None:
        self._timeout = (
            config.connect_timeout_seconds,
            config.read_timeout_seconds,
        )
        self._max_response_bytes = config.max_response_bytes
        self._allowed_private_origins = frozenset(config.allowed_destinations)
        self._allow_development_http = config.allow_development_http

    def _validate_resolved_destination(self, url: str) -> str:
        """Resolve `url`'s hostname once and return the single address the
        connection must be pinned to, having rejected it if any resolved
        address violates the configured policy. Returning (rather than
        discarding) the validated address lets callers connect to exactly
        what was checked instead of letting the HTTP client re-resolve the
        hostname a second time, which is the DNS-rebinding gap this closes
        """
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        try:
            resolved = socket.getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except OSError as error:
            raise GiteaProtocolError(
                "Gitea destination could not be resolved"
            ) from error
        addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
        seen: set[str] = set()
        for item in resolved:
            raw = str(item[4][0])
            if raw in seen:
                continue
            seen.add(raw)
            addresses.append(ipaddress.ip_address(raw))
        if not addresses:
            raise GiteaProtocolError("Gitea destination resolved no addresses")
        for address in addresses:
            if (
                address.is_link_local
                or address.is_multicast
                or address.is_reserved
            ):
                raise GiteaProtocolError(
                    "Gitea destination resolved to a prohibited address"
                )
            if address.is_loopback and not self._allow_development_http:
                raise GiteaProtocolError(
                    "Gitea loopback destination requires development opt-in"
                )
            if (
                address.is_private
                and origin not in self._allowed_private_origins
            ):
                raise GiteaProtocolError(
                    "Gitea private destination is not explicitly allowlisted"
                )
        return str(addresses[0])

    @staticmethod
    def _session():
        from allauth.socialaccount.adapter import get_adapter

        return get_adapter().get_requests_session()

    def _connect_pinned(
        self,
        method: str,
        url: str,
        address: str,
        *,
        headers: Mapping[str, str],
        data: Mapping[str, str] | None,
    ) -> requests.Response:
        """Connect to `address` (already validated by
        `_validate_resolved_destination`) directly on the allauth-managed
        session, instead of handing the original hostname to `requests` and
        letting it resolve again. The original hostname is still sent as
        `Host` and pinned as TLS SNI via `_PinnedHTTPAdapter` (shared with
        `atlas_plugin_api.safe_http`), so certificate validation is
        unaffected and allauth's session integration is kept rather than
        bypassed."""
        parsed = urlsplit(url)
        hostname = parsed.hostname
        assert hostname is not None
        authority = f"[{address}]" if ":" in address else address
        if parsed.port is not None:
            authority = f"{authority}:{parsed.port}"
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        pinned_url = f"{parsed.scheme}://{authority}{path}"

        send_headers = dict(headers)
        host_authority = (
            hostname if parsed.port is None else f"{hostname}:{parsed.port}"
        )
        send_headers.setdefault("Host", host_authority)

        adapter = _PinnedHTTPAdapter(
            hostname=hostname, is_https=parsed.scheme == "https"
        )
        with self._session() as session:
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            return session.request(
                method,
                pinned_url,
                headers=send_headers,
                data=data,
                timeout=self._timeout,
                allow_redirects=False,
            )

    def _json(self, response: requests.Response) -> Mapping[str, Any]:
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_response_bytes:
                    raise GiteaProtocolError("Gitea response is too large")
            except ValueError as error:
                raise GiteaProtocolError(
                    "Gitea response has invalid content length"
                ) from error
        if len(response.content) > self._max_response_bytes:
            raise GiteaProtocolError("Gitea response is too large")
        value = response.json()
        if not isinstance(value, dict):
            raise GiteaProtocolError("Gitea endpoint returned a non-object")
        return value

    def get_profile(self, url: str, *, access_token: str) -> Mapping[str, Any]:
        address = self._validate_resolved_destination(url)
        response = self._connect_pinned(
            "GET",
            url,
            address,
            headers={
                "Accept": "application/json",
                "Authorization": f"token {access_token}",
            },
            data=None,
        )
        return self._json(response)

    def get_health(self, url: str) -> Mapping[str, Any]:
        address = self._validate_resolved_destination(url)
        response = self._connect_pinned(
            "GET",
            url,
            address,
            headers={"Accept": "application/json"},
            data=None,
        )
        return self._json(response)

    def exchange_code(
        self, url: str, data: Mapping[str, str]
    ) -> Mapping[str, Any]:
        address = self._validate_resolved_destination(url)
        response = self._connect_pinned(
            "POST",
            url,
            address,
            headers={"Accept": "application/json"},
            data=data,
        )
        return self._json(response)


def configured_gitea() -> GiteaConfig:
    from atlas_plugin_api import get_plugin_config

    config = get_plugin_config(PROVIDER_ID, GiteaConfig)
    if config.has_unresolved_secrets():
        raise RuntimeError(
            "atlas.auth.gitea has no resolved typed configuration"
        )
    return config


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class GiteaProvider:
    descriptor = PROVIDER_DESCRIPTOR

    def __init__(
        self,
        config: GiteaConfig,
        *,
        transport: GiteaTransport | None = None,
    ) -> None:
        if not isinstance(config.client_secret, str):
            raise TypeError(
                "Gitea client secret must be resolved before runtime"
            )
        self.config = config
        self._client_secret = config.client_secret
        self.transport = transport or AllauthGiteaTransport(config)
        self._consumed_attempts: set[str] = set()
        self._consume_lock = Lock()

    @property
    def source_id(self) -> str:
        return self.config.instance_origin

    @property
    def authorization_url(self) -> str:
        return f"{self.source_id}/login/oauth/authorize"

    @property
    def token_url(self) -> str:
        return f"{self.source_id}/login/oauth/access_token"

    @property
    def profile_url(self) -> str:
        return f"{self.source_id}/api/v1/user"

    def _derived_verifier(self, context: object) -> str:
        material = (
            f"pkce\0{PROVIDER_ID}\0{getattr(context, 'source_id')}\0"
            f"{getattr(context, 'attempt_id')}"
        ).encode()
        return _base64url(
            hmac.new(
                self._client_secret.encode(), material, hashlib.sha256
            ).digest()
        )

    def _context_is_valid(self, context: object) -> bool:
        return (
            getattr(context, "provider_id", None) == PROVIDER_ID
            and getattr(context, "source_id", None) == self.source_id
            and getattr(context, "deadline")
            > datetime.now(getattr(context, "deadline").tzinfo)
        )

    def begin(self, context: RedirectFlowContext) -> RedirectChallenge:
        if not self._context_is_valid(context):
            raise GiteaProtocolError(
                "Gitea flow context does not match the configured source"
            )
        verifier = self._derived_verifier(context)
        challenge = _base64url(hashlib.sha256(verifier.encode()).digest())
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.config.client_id,
                "redirect_uri": context.callback_url,
                "scope": " ".join(self.config.scopes),
                "state": secrets.token_urlsafe(32),
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return RedirectChallenge(f"{self.authorization_url}?{query}")

    @staticmethod
    def _subject(profile: Mapping[str, Any]) -> str:
        value = profile.get("id")
        if isinstance(value, bool):
            raise GiteaProtocolError("Gitea user id is invalid")
        if isinstance(value, int) and value > 0:
            return str(value)
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            normalized = str(int(value))
            if normalized != "0":
                return normalized
        raise GiteaProtocolError("Gitea user id is missing or invalid")

    @staticmethod
    def _optional_text(profile: Mapping[str, Any], key: str) -> str | None:
        value = profile.get(key)
        return value if isinstance(value, str) and value.strip() else None

    def _normalize(self, profile_data: Mapping[str, Any]) -> VerifiedIdentity:
        profile = ExternalProfile(
            username=self._optional_text(profile_data, "login"),
            display_name=(
                self._optional_text(profile_data, "name")
                or self._optional_text(profile_data, "full_name")
            ),
            email=self._optional_text(profile_data, "email"),
        )
        attributes: dict[str, AssuredAttribute] = {}
        for name, value in (
            ("username", profile.username),
            ("displayName", profile.display_name),
        ):
            if value is not None:
                attributes[name] = AssuredAttribute(
                    value, AttributeProvenance.AUTHORITY_MANAGED
                )
        if profile.email is not None:
            attributes["email"] = AssuredAttribute(
                profile.email, AttributeProvenance.SELF_ASSERTED
            )
        return VerifiedIdentity(
            provider_id=PROVIDER_ID,
            source_id=self.source_id,
            subject=self._subject(profile_data),
            profile=profile,
            attributes=attributes,
            groups=ExternalGroupSnapshot.unsupported(),
        )

    def complete(
        self, context: RedirectCallbackContext
    ) -> VerifiedIdentity | AuthenticationFailure:
        if not self._context_is_valid(context):
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_RESULT
            )
        if context.callback_parameters.get("error"):
            return AuthenticationFailure(AuthenticationFailureCategory.CANCELED)
        code = context.callback_parameters.get("code")
        if not code or context.callback_url is None:
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_RESULT
            )
        with self._consume_lock:
            if context.attempt_id in self._consumed_attempts:
                return AuthenticationFailure(
                    AuthenticationFailureCategory.INVALID_RESULT
                )
            self._consumed_attempts.add(context.attempt_id)
        try:
            token = self.transport.exchange_code(
                self.token_url,
                {
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.config.client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": context.callback_url,
                    "code_verifier": self._derived_verifier(context),
                },
            )
            access_token = token.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise GiteaProtocolError(
                    "Gitea token response has no access token"
                )
            profile = self.transport.get_profile(
                self.profile_url, access_token=access_token
            )
            return self._normalize(profile)
        except GiteaProtocolError:
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_RESULT
            )
        except requests.RequestException:
            return AuthenticationFailure(
                AuthenticationFailureCategory.UNAVAILABLE, retryable=True
            )
        except (KeyError, TypeError, ValueError):
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_RESULT
            )

    def health(self) -> Mapping[str, str]:
        """Return an allowlisted, secret-free provider diagnostic."""

        try:
            self.transport.get_health(f"{self.source_id}/api/healthz")
        except requests.RequestException:
            return {
                "providerId": PROVIDER_ID,
                "status": "unavailable",
                "category": "upstream_unavailable",
            }
        except (GiteaProtocolError, TypeError, ValueError):
            return {
                "providerId": PROVIDER_ID,
                "status": "unavailable",
                "category": "invalid_response",
            }
        return {
            "providerId": PROVIDER_ID,
            "status": "available",
            "category": "ok",
        }
