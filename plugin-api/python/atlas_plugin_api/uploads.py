"""Upload ticket contract: targets a plugin makes uploadable, and the ticket
service Core binds.

A plugin registers an `UploadTarget` keyed by `(kind, field)` from its
`register_runtime()`, with an adapter that applies a raw body to the entity.
Core owns the ticket model, the public `PUT` route, and issuance; it binds an
`UploadTicketService` here so a plugin (the MCP plugin's `request_attach`)
can issue tickets without importing `server`. Nothing in this module touches
Django.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


class UploadValidationError(Exception):
    """The body or ticket parameters are unacceptable; `reason` is shown to
    the caller verbatim (include the parser/validator message)."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class UploadForbiddenError(Exception):
    """The ticket's issuing user may not write this target."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class UnknownUploadTargetError(Exception):
    """No plugin registered an upload target for `(kind, field)`."""

    def __init__(self, kind: str, field_name: str, supported: tuple[str, ...]) -> None:
        self.kind = kind
        self.field = field_name
        self.supported = supported
        names = ", ".join(supported) or "none"
        super().__init__(
            f"No upload target {field_name!r} for kind {kind!r} (supported: {names})"
        )


class DuplicateUploadTargetError(Exception):
    pass


@dataclass(frozen=True)
class UploadResult:
    """What an adapter returns on success; `summary` goes to the client."""

    summary: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class UploadAdapter(Protocol):
    """Applies an uploaded body to one `(kind, field)` target."""

    def validate_params(self, params: Mapping[str, Any]) -> dict[str, Any]:
        """Check ticket parameters at request time and return the cleaned
        dict stored on the ticket. Raise `UploadValidationError`."""
        ...

    def apply(
        self, entity: Any, body: bytes, params: Mapping[str, Any], user: Any
    ) -> UploadResult:
        """Write `body` into the entity on behalf of `user`, through the same
        functions the regular write path uses. Raise `UploadValidationError`
        (unacceptable content) or `UploadForbiddenError`; either must leave
        the stored content unchanged."""
        ...


@dataclass(frozen=True)
class UploadTarget:
    kind: str
    field: str
    required_scope: str
    max_bytes: int
    adapter: UploadAdapter


_targets: dict[tuple[str, str], tuple[UploadTarget, str | None]] = {}


def register_upload_target(target: UploadTarget, *, owner: str | None = None) -> None:
    key = (target.kind, target.field)
    if key in _targets:
        msg = f"upload target {key!r} is already registered"
        raise DuplicateUploadTargetError(msg)
    if target.max_bytes < 1:
        msg = "upload target max_bytes must be positive"
        raise ValueError(msg)
    _targets[key] = (target, owner)


def get_upload_target(kind: str, field_name: str) -> UploadTarget:
    """Raises `UnknownUploadTargetError`, naming the fields supported for
    `kind`."""
    entry = _targets.get((kind, field_name))
    if entry is None:
        raise UnknownUploadTargetError(kind, field_name, supported_upload_fields(kind))
    return entry[0]


def supported_upload_fields(kind: str) -> tuple[str, ...]:
    return tuple(sorted(f for (k, f) in _targets if k == kind))


def list_upload_targets() -> tuple[UploadTarget, ...]:
    return tuple(target for target, _ in _targets.values())


@dataclass(frozen=True)
class IssuedUploadTicket:
    """Returned once at issuance; `path` embeds the token."""

    path: str
    expires_at: datetime
    max_bytes: int


@runtime_checkable
class UploadTicketService(Protocol):
    def issue(
        self,
        *,
        user: Any,
        token_id: int | None,
        scopes: frozenset[str],
        entity: Any,
        field: str,
        params: Mapping[str, Any],
    ) -> IssuedUploadTicket:
        """Raises `UnknownUploadTargetError`, `UploadForbiddenError`
        (scope, RBAC, YAML-managed), or `UploadValidationError`."""
        ...


_ticket_service: UploadTicketService | None = None


def bind_upload_ticket_service(service: UploadTicketService) -> None:
    """Core-only; called from `server.apps.catalog.plugin.register_runtime()`."""
    global _ticket_service
    _ticket_service = service


def get_upload_ticket_service() -> UploadTicketService:
    if _ticket_service is None:
        msg = (
            "get_upload_ticket_service() called before Core registered it "
            "(server.apps.catalog.plugin.register_runtime() must run first)"
        )
        raise RuntimeError(msg)
    return _ticket_service
