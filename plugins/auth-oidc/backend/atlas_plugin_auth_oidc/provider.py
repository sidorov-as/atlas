"""OIDC Authorization Code + PKCE implementation behind the public contract."""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import secrets
import socket
from collections.abc import Callable, Mapping
from datetime import datetime
from threading import Lock
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit

import jwt
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

from .config import OIDCConfig, _is_loopback_hostname
from .plugin import PROVIDER_DESCRIPTOR, PROVIDER_ID


class OIDCProtocolError(ValueError):
    pass


class OIDCTransport(Protocol):
    def get_json(
        self, url: str, *, bearer_token: str | None = None
    ) -> Mapping[str, Any]: ...

    def post_form(
        self, url: str, data: Mapping[str, str]
    ) -> Mapping[str, Any]: ...


class RequestsOIDCTransport:
    def __init__(self, config: OIDCConfig) -> None:
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
            raise OIDCProtocolError(
                "OIDC destination could not be resolved"
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
            raise OIDCProtocolError("OIDC destination resolved no addresses")
        for address in addresses:
            if (
                address.is_link_local
                or address.is_multicast
                or address.is_reserved
            ):
                raise OIDCProtocolError(
                    "OIDC destination resolved to a prohibited address"
                )
            if address.is_loopback and not self._allow_development_http:
                raise OIDCProtocolError(
                    "OIDC loopback destination requires development opt-in"
                )
            if (
                address.is_private
                and origin not in self._allowed_private_origins
            ):
                raise OIDCProtocolError(
                    "OIDC private destination is not explicitly allowlisted"
                )
        return str(addresses[0])

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
        `_validate_resolved_destination`) directly, instead of handing the
        original hostname to `requests` and letting it resolve again. The
        original hostname is still sent as `Host` and pinned as TLS SNI via
        `_PinnedHTTPAdapter` (shared with `atlas_plugin_api.safe_http`), so
        certificate validation is unaffected."""
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
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        try:
            return session.request(
                method,
                pinned_url,
                headers=send_headers,
                data=data,
                timeout=self._timeout,
                allow_redirects=False,
            )
        finally:
            session.close()

    def _json(self, response: requests.Response) -> Mapping[str, Any]:
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_response_bytes:
                    raise OIDCProtocolError("OIDC response is too large")
            except ValueError as error:
                raise OIDCProtocolError(
                    "OIDC response has invalid content length"
                ) from error
        if len(response.content) > self._max_response_bytes:
            raise OIDCProtocolError("OIDC response is too large")
        value = response.json()
        if not isinstance(value, dict):
            raise OIDCProtocolError("OIDC endpoint returned a non-object")
        return value

    def get_json(
        self, url: str, *, bearer_token: str | None = None
    ) -> Mapping[str, Any]:
        address = self._validate_resolved_destination(url)
        headers = {"Accept": "application/json"}
        if bearer_token is not None:
            headers["Authorization"] = f"Bearer {bearer_token}"
        return self._json(
            self._connect_pinned(
                "GET", url, address, headers=headers, data=None
            )
        )

    def post_form(self, url: str, data: Mapping[str, str]) -> Mapping[str, Any]:
        address = self._validate_resolved_destination(url)
        return self._json(
            self._connect_pinned(
                "POST",
                url,
                address,
                headers={"Accept": "application/json"},
                data=data,
            )
        )


TokenVerifier = Callable[
    [str, Mapping[str, Any], OIDCConfig], Mapping[str, Any]
]


def configured_oidc() -> OIDCConfig:
    from atlas_plugin_api import get_plugin_config

    config = get_plugin_config(PROVIDER_ID, OIDCConfig)
    if config.has_unresolved_secrets():
        raise RuntimeError(
            "atlas.auth.oidc has no resolved typed configuration"
        )
    return config


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class OIDCProvider:
    descriptor = PROVIDER_DESCRIPTOR

    def __init__(
        self,
        config: OIDCConfig,
        *,
        transport: OIDCTransport | None = None,
        token_verifier: TokenVerifier | None = None,
    ) -> None:
        if not isinstance(config.client_secret, str):
            raise TypeError(
                "OIDC client secret must be resolved before runtime"
            )
        self.config = config
        self._client_secret = config.client_secret
        self.transport = transport or RequestsOIDCTransport(config)
        self.token_verifier = token_verifier or self._verify_id_token
        self._consumed_attempts: set[str] = set()
        self._consume_lock = Lock()

    def _derived_value(self, purpose: str, context: object) -> str:
        attempt_id = str(getattr(context, "attempt_id"))
        source_id = str(getattr(context, "source_id"))
        material = (
            f"{purpose}\0{PROVIDER_ID}\0{source_id}\0{attempt_id}".encode()
        )
        return _base64url(
            hmac.new(
                self._client_secret.encode(), material, hashlib.sha256
            ).digest()
        )

    def _validate_url(self, value: object, *, field: str) -> str:
        if not isinstance(value, str):
            raise OIDCProtocolError(f"OIDC metadata has no {field}")
        parsed = urlsplit(value)
        if (
            parsed.username
            or parsed.password
            or parsed.fragment
            or not parsed.netloc
        ):
            raise OIDCProtocolError(f"OIDC {field} is invalid")
        development_http = (
            parsed.scheme == "http"
            and self.config.allow_development_http
            and _is_loopback_hostname(parsed.hostname)
        )
        if parsed.scheme != "https" and not development_http:
            raise OIDCProtocolError(f"OIDC {field} must use HTTPS")
        origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        configured_origins = {
            f"{item.scheme}://{item.netloc}".rstrip("/")
            for item in (
                urlsplit(self.config.discovery_url),
                urlsplit(self.config.expected_issuer),
            )
            if item.netloc
        }
        configured_origins.update(self.config.allowed_destinations)
        if origin not in configured_origins:
            raise OIDCProtocolError(
                f"OIDC {field} destination is not allowlisted"
            )
        try:
            address = ipaddress.ip_address(parsed.hostname or "")
        except ValueError:
            address = None
        if (
            address is not None
            and (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_reserved
            )
            and not self.config.allow_development_http
        ):
            raise OIDCProtocolError(
                f"OIDC {field} private destination is not allowed"
            )
        return value

    def _metadata(self) -> Mapping[str, Any]:
        self._validate_url(self.config.discovery_url, field="discovery URL")
        metadata = self.transport.get_json(self.config.discovery_url)
        if metadata.get("issuer") != self.config.expected_issuer:
            raise OIDCProtocolError("OIDC discovery issuer mismatch")
        methods = metadata.get("code_challenge_methods_supported")
        if methods is not None and "S256" not in methods:
            raise OIDCProtocolError("OIDC provider does not support PKCE S256")
        self._validate_url(
            metadata.get("authorization_endpoint"),
            field="authorization endpoint",
        )
        self._validate_url(
            metadata.get("token_endpoint"), field="token endpoint"
        )
        self._validate_url(metadata.get("jwks_uri"), field="JWKS endpoint")
        if metadata.get("userinfo_endpoint") is not None:
            self._validate_url(
                metadata["userinfo_endpoint"], field="UserInfo endpoint"
            )
        return metadata

    def begin(self, context: RedirectFlowContext) -> RedirectChallenge:
        if context.source_id != self.config.expected_issuer:
            raise OIDCProtocolError(
                "OIDC flow source does not match the expected issuer"
            )
        metadata = self._metadata()
        verifier = self._derived_value("pkce", context)
        challenge = _base64url(hashlib.sha256(verifier.encode()).digest())
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.config.client_id,
                "redirect_uri": context.callback_url,
                "scope": " ".join(self.config.scopes),
                "state": secrets.token_urlsafe(32),
                "nonce": self._derived_value("nonce", context),
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return RedirectChallenge(
            f"{metadata['authorization_endpoint']}?{query}"
        )

    def _verify_id_token(
        self,
        encoded: str,
        metadata: Mapping[str, Any],
        config: OIDCConfig,
    ) -> Mapping[str, Any]:
        header = jwt.get_unverified_header(encoded)
        if header.get("alg") not in config.allowed_algorithms:
            raise OIDCProtocolError("OIDC token algorithm is not allowed")
        jwks = self.transport.get_json(str(metadata["jwks_uri"]))
        keys = jwks.get("keys")
        if not isinstance(keys, list):
            raise OIDCProtocolError("OIDC JWKS response is invalid")
        kid = header.get("kid")
        matching = [
            item
            for item in keys
            if isinstance(item, dict)
            and (kid is None or item.get("kid") == kid)
        ]
        if len(matching) != 1:
            raise OIDCProtocolError("OIDC signing key is unavailable")
        key = jwt.PyJWK.from_dict(matching[0]).key
        claims = jwt.decode(
            encoded,
            key,
            algorithms=list(config.allowed_algorithms),
            audience=config.client_id,
            issuer=config.expected_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
        if not isinstance(claims, dict):
            raise OIDCProtocolError("OIDC ID token claims are invalid")
        return claims

    def _normalize(
        self, claims: Mapping[str, Any], userinfo: Mapping[str, Any] | None
    ) -> VerifiedIdentity:
        values = userinfo or claims
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise OIDCProtocolError("OIDC subject is missing")
        if userinfo is not None and userinfo.get("sub") != subject:
            raise OIDCProtocolError("OIDC UserInfo subject mismatch")
        email = values.get("email")
        username = values.get("preferred_username")
        display_name = values.get("name")
        profile = ExternalProfile(
            username=username
            if isinstance(username, str) and username.strip()
            else None,
            display_name=(
                display_name
                if isinstance(display_name, str) and display_name.strip()
                else None
            ),
            email=email if isinstance(email, str) and email.strip() else None,
        )
        attributes: dict[str, AssuredAttribute] = {}
        if profile.email is not None:
            provenance = (
                AttributeProvenance.VERIFIED_OWNERSHIP
                if values.get("email_verified") is True
                else AttributeProvenance.SELF_ASSERTED
            )
            attributes["email"] = AssuredAttribute(profile.email, provenance)
        for name, value in (
            ("username", profile.username),
            ("displayName", profile.display_name),
        ):
            if value is not None:
                attributes[name] = AssuredAttribute(
                    value, AttributeProvenance.AUTHORITY_MANAGED
                )
        groups = ExternalGroupSnapshot.unsupported()
        if self.config.groups_claim is not None:
            raw_groups = values.get(self.config.groups_claim)
            if raw_groups is None:
                groups = ExternalGroupSnapshot.unavailable()
            elif isinstance(raw_groups, list) and all(
                isinstance(item, str) and item.strip() for item in raw_groups
            ):
                groups = ExternalGroupSnapshot.complete(
                    tuple(dict.fromkeys(raw_groups))
                )
            else:
                raise OIDCProtocolError("OIDC groups claim is invalid")
        return VerifiedIdentity(
            provider_id=PROVIDER_ID,
            source_id=self.config.expected_issuer,
            subject=subject,
            profile=profile,
            attributes=attributes,
            groups=groups,
        )

    def complete(
        self, context: RedirectCallbackContext
    ) -> VerifiedIdentity | AuthenticationFailure:
        if context.source_id != self.config.expected_issuer:
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_RESULT
            )
        if context.deadline <= datetime.now(context.deadline.tzinfo):
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_RESULT
            )
        if context.callback_parameters.get("error"):
            return AuthenticationFailure(AuthenticationFailureCategory.CANCELED)
        code = context.callback_parameters.get("code")
        if not code:
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
            metadata = self._metadata()
            token = self.transport.post_form(
                str(metadata["token_endpoint"]),
                {
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.config.client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": context.callback_url or "",
                    "code_verifier": self._derived_value("pkce", context),
                },
            )
            encoded = token.get("id_token")
            access_token = token.get("access_token")
            if not isinstance(encoded, str) or not isinstance(
                access_token, str
            ):
                raise OIDCProtocolError("OIDC token response is incomplete")
            claims = self.token_verifier(encoded, metadata, self.config)
            if claims.get("nonce") != self._derived_value("nonce", context):
                raise OIDCProtocolError("OIDC nonce mismatch")
            audience = claims.get("aud")
            if isinstance(audience, list) and len(audience) > 1:
                if claims.get("azp") != self.config.client_id:
                    raise OIDCProtocolError("OIDC authorized party mismatch")
            elif claims.get("azp") not in (None, self.config.client_id):
                raise OIDCProtocolError("OIDC authorized party mismatch")
            userinfo = None
            endpoint = metadata.get("userinfo_endpoint")
            if endpoint is not None:
                userinfo = self.transport.get_json(
                    str(endpoint), bearer_token=access_token
                )
            return self._normalize(claims, userinfo)
        except (
            OIDCProtocolError,
            jwt.PyJWTError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_RESULT
            )
        except requests.RequestException:
            return AuthenticationFailure(
                AuthenticationFailureCategory.UNAVAILABLE, retryable=True
            )

    def health(self) -> Mapping[str, str]:
        """Probe discovery only and return an allowlisted diagnostic."""

        try:
            self._metadata()
        except requests.RequestException:
            return {
                "providerId": PROVIDER_ID,
                "status": "unavailable",
                "category": "upstream_unavailable",
            }
        except (OIDCProtocolError, KeyError, TypeError, ValueError):
            return {
                "providerId": PROVIDER_ID,
                "status": "unavailable",
                "category": "invalid_configuration_or_metadata",
            }
        return {
            "providerId": PROVIDER_ID,
            "status": "available",
            "category": "ok",
        }

    def remote_logout(self, return_url: str) -> str | None:
        """Build a validated upstream logout URL without retaining tokens."""

        if not self.config.remote_logout:
            return None
        metadata = self._metadata()
        endpoint = metadata.get("end_session_endpoint")
        if endpoint is None:
            return None
        target = self._validate_url(endpoint, field="logout endpoint")
        separator = "&" if "?" in target else "?"
        query = urlencode({"post_logout_redirect_uri": return_url})
        return f"{target}{separator}{query}"
