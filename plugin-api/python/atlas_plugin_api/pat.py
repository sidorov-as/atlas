"""Personal Access Token validation contract (`personal-access-tokens` spec)
— mirrors `entity_service.py`'s "Protocol + bind/get singleton slot"
shape and its reasoning.

Core's `PersonalAccessToken` model (hash + short lookup prefix, scopes,
`expires_at`/`revoked_at`/`last_used_at`, owning-user FK) can't move here:
it does real Django ORM work, and, unlike `CatalogEntity`, nothing outside
Core needs to hold a reference to the row itself — only the *result* of
validating a raw token string against it. So this module publishes just
that narrow result:

- `ResolvedPersonalAccessToken`, a plain, ORM-free dataclass — the owning
  Django user plus the token's granted scopes, everything a caller (an
  auth backend, or later a scope check) needs.
- `PATValidator`, a `Protocol` describing "raw token string in, a resolved
  token or `None` out" — the single operation `atlas_plugin_api.auth.
  PATBearerAuth` needs.
- `bind_pat_validator()`/`get_pat_validator()`, a process-wide registration
  slot Core populates with its real validation function from its own
  `register_runtime()` hook, the same "load selected runtime entry points"
  phase that populates `bind_entity_service()` et al. — how a plugin's
  `PATBearerAuth` gets hold of Core's validation logic without
  `atlas_plugin_api` ever importing `server`.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ResolvedPersonalAccessToken:
    """What a valid raw token string resolves to: its owning Django user
    and its granted scopes (e.g. `catalog:read`, `flows:write`) — never the
    token row itself, so a caller across the plugin boundary can't reach
    into `PersonalAccessToken`'s own fields (`personal-access-tokens` spec:
    "Atlas SHALL persist only a salted hash and a short lookup prefix,
    never the plaintext").
    """

    user: Any
    scopes: frozenset[str]
    token_id: int | None = None


@runtime_checkable
class PATValidator(Protocol):
    """Structural type for Core's PAT validation function — resolves a raw
    `Authorization: Bearer <token>` value to the token it names, or `None`
    when the token doesn't exist, doesn't hash-match, is
    expired/revoked, or its owning account is no longer active
    (`personal-access-tokens` spec). Updates the token's `last_used_at` as
    a side effect of a successful resolution.
    """

    def __call__(self, raw_token: str) -> ResolvedPersonalAccessToken | None: ...


_pat_validator: PATValidator | None = None


def bind_pat_validator(validator: PATValidator) -> None:
    """Core-only: register the real PAT validation function, so
    `get_pat_validator()` can hand it out without `atlas_plugin_api` ever
    importing `server`. Called once from `server.apps.catalog.plugin.
    register_runtime()`, during the shared runtime entry-point-loading
    phase, before any request is served.
    """
    global _pat_validator
    _pat_validator = validator


def get_pat_validator() -> PATValidator:
    """Return the process-wide PAT validator Core registered via
    `bind_pat_validator()`. Only callable after that registration has
    run — from inside a function body or method, never cached at plugin
    module import time (matching `get_entity_service()`'s same caution).
    """
    if _pat_validator is None:
        msg = (
            "get_pat_validator() called before Core registered its PAT validator "
            "(server.apps.catalog.plugin.register_runtime() must run first)"
        )
        raise RuntimeError(msg)
    return _pat_validator
