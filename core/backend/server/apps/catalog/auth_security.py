"""Shared authentication security policy and secret-safe primitives."""

from __future__ import annotations

import hashlib
import ipaddress
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.utils import timezone

REDACTED = "[REDACTED]"
MAX_AUTH_REQUEST_BYTES = 64 * 1024
MAX_CALLBACK_FIELDS = 32
MAX_CALLBACK_VALUE_BYTES = 4096

_SECRET_KEY_PARTS = (
    "authorization",
    "bind_dn",
    "bind_password",
    "code",
    "credential",
    "id_token",
    "password",
    "raw",
    "refresh",
    "secret",
    "state",
    "token",
)


def is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in _SECRET_KEY_PARTS)


def redact_authentication_data(value: Any, *, key: object = "") -> Any:
    """Recursively retain shape while removing authentication material."""

    if is_sensitive_key(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(item_key): redact_authentication_data(item_value, key=item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact_authentication_data(item) for item in value]
    if isinstance(value, bytes):
        return REDACTED
    return value


def redact_authentication_event(_logger, _method_name, event_dict):
    """Structlog/logging processor using the same recursive redaction policy."""

    return redact_authentication_data(event_dict)


def safe_exception_category(error: BaseException) -> str:
    """Classify an exception without ever returning its message."""

    name = type(error).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "connection" in name or "transport" in name:
        return "upstream_unavailable"
    return "provider_error"


def authentication_policy_digest(
    policy: Mapping[str, Any] | None = None,
) -> str:
    if policy is None:
        from .auth_policy import authentication_policy

        policy = authentication_policy()
    serialized = json.dumps(
        redact_authentication_data(policy),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def current_policy_generation() -> int:
    """Synchronize a durable policy generation shared by every worker."""

    from .models import AuthenticationPolicyState

    digest = authentication_policy_digest()
    with transaction.atomic():
        state, _ = (
            AuthenticationPolicyState.objects.select_for_update().get_or_create(
                pk=1, defaults={"digest": digest}
            )
        )
        if state.digest != digest:
            state.digest = digest
            state.generation += 1
            state.save(update_fields=("digest", "generation", "updated_at"))
        return state.generation


def principal_generation(user) -> int:
    from .models import AuthenticationPrincipalState

    state, _ = AuthenticationPrincipalState.objects.get_or_create(user=user)
    return state.revocation_generation


def revoke_principal_sessions(user) -> int:
    """Durably invalidate sessions on every worker without scanning them."""

    from .models import AuthenticationPrincipalState

    with transaction.atomic():
        state, _ = (
            AuthenticationPrincipalState.objects.select_for_update().get_or_create(
                user=user
            )
        )
        state.revocation_generation += 1
        state.save(update_fields=("revocation_generation", "updated_at"))
        return state.revocation_generation


def source_binding_generation(provider_id: str, source_id: str | None) -> int:
    if not source_id or provider_id == "atlas.auth.local":
        return 0
    from .models import AuthenticationSourceBinding

    binding = AuthenticationSourceBinding.objects.filter(
        provider_id=provider_id, source_id=source_id, revoked_at__isnull=True
    ).first()
    return binding.generation if binding is not None else 1


def trusted_client_address(request) -> str:
    """Trust forwarding only from explicitly configured proxy addresses."""

    remote = request.META.get("REMOTE_ADDR", "unknown")
    policy = getattr(settings, "ATLAS_AUTHENTICATION", {})
    trusted = frozenset(policy.get("trustedProxyAddresses", ()))
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if remote in trusted and forwarded:
        return forwarded.split(",", 1)[0].strip() or remote
    return remote


def consume_authentication_budget(
    *,
    scope: str,
    subject: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """Consume a database-backed fixed-window budget atomically."""

    from .models import AuthenticationRateLimit

    key_hash = hashlib.sha256(f"{scope}\0{subject}".encode()).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        row, _ = (
            AuthenticationRateLimit.objects.select_for_update().get_or_create(
                key_hash=key_hash,
                defaults={"scope": scope, "window_started_at": now, "count": 0},
            )
        )
        elapsed = (now - row.window_started_at).total_seconds()
        if elapsed >= window_seconds:
            row.window_started_at = now
            row.count = 0
            elapsed = 0
        allowed = row.count < limit
        if allowed:
            row.count += 1
            row.save(update_fields=("count", "window_started_at", "updated_at"))
        retry_after = max(1, window_seconds - int(elapsed))
        return allowed, retry_after


def authentication_budget_allowed(
    request, *, provider_id: str, account: str = ""
) -> tuple[bool, int]:
    client = trusted_client_address(request)
    checks = [
        ("deployment", "all", 60, 300),
        ("client", client, 30, 300),
        ("provider", provider_id, 40, 300),
    ]
    if account:
        checks.append(
            ("account", f"{provider_id}:{account.casefold()}", 8, 300)
        )
    retry_after = 0
    for scope, subject, limit, window in checks:
        allowed, retry = consume_authentication_budget(
            scope=scope, subject=subject, limit=limit, window_seconds=window
        )
        retry_after = max(retry_after, retry)
        if not allowed:
            return False, retry_after
    return True, retry_after


def validate_outbound_url(
    url: str,
    *,
    allowed_origins: tuple[str, ...] | list[str] | set[str],
    allow_development_http: bool = False,
) -> str:
    """Validate an identity-service URL before sending data to it."""

    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError("identity-service URL is invalid")
    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    normalized_allowed = {item.rstrip("/") for item in allowed_origins}
    if origin not in normalized_allowed:
        raise ValueError("identity-service destination is not allowlisted")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    unsafe_address = address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
    )
    if unsafe_address and not allow_development_http:
        raise ValueError("private identity-service destination is not allowed")
    if parsed.scheme != "https" and not allow_development_http:
        raise ValueError("identity-service URL must use HTTPS")
    return url
