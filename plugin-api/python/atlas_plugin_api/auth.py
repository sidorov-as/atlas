"""Session- and Personal-Access-Token-based auth for `dmr` APIs
(`core-plugin-contract-surface` spec: "Core publishes its plugin-facing
surface as contract types").

`SessionAuth` wraps Django's own session/`AuthenticationMiddleware` — any
endpoint requiring only a session (safe methods) is satisfied once
`request.user` is populated, regardless of how the session was established.
Needs no Django model/Core dependency at all (just `dmr`, already a direct
dependency of every first-party plugin's own CRUD API), so it moves here
outright, the same way `kinds.py` did. `server.apps.catalog.api.auth`
re-exports it for Core's own internal call sites.

`PATBearerAuth` (`personal-access-tokens`/`mcp-plugin` specs) resolves an
`Authorization: Bearer <token>` header through `pat.get_pat_validator()` —
unlike `SessionAuth`, it does need Core's registered validator (real
Django ORM work against `PersonalAccessToken`), the same
bind/get-a-singleton indirection `entity_service.py` uses for
`EntityService`. `dmr` auth instances must stay stateless (shared/reused
across every request — see `dmr.security.base.SyncAuth`'s own docstring),
so `__call__` never mutates `self`; it returns a *new* `PATBearerAuth`
carrying the just-resolved token, so a later scope check
(`request_auth(request)`) can read `.resolved.scopes` without a second
lookup, while the shared, class-level instance configured in an
endpoint's `auth = (...)` tuple never holds any per-request state itself.

`require_scope()` is that later scope check (`personal-access-tokens` spec:
"PAT scopes narrow ... the holder's existing RBAC"): a controller calls it
at the top of a write-`Endpoint` body to deny a request whose resolved PAT
doesn't carry the given scope, before any `EntityService`/`FlowService`
call — independent of, and checked ahead of, the underlying user's own
RBAC (which `EntityService`/`FlowService` still enforce on their own,
exactly as for any other caller). Lives here rather than in `atlas.mcp`
itself since it's generic over any scope string and any `PATBearerAuth`-
protected endpoint a future plugin might add, not MCP-specific.
"""

from http import HTTPStatus
from typing import Self, override

from dmr.controller import Controller
from dmr.endpoint import Endpoint
from dmr.errors import ErrorType, format_error
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.response import APIError
from dmr.security.base import SyncAuth, request_auth
from dmr.serializer import BaseSerializer

from .pat import ResolvedPersonalAccessToken, get_pat_validator

_BEARER_PREFIX = "Bearer "


class SessionAuth(SyncAuth):
    """Authenticates a request that carries an authenticated Django session."""

    __slots__ = ()

    @property
    @override
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        return {
            "session": SecurityScheme(
                type="apiKey",
                name="sessionid",
                security_scheme_in="cookie",
                description="Django session cookie, established via allauth headless login",
            ),
        }

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        return {"session": []}

    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: "Controller[BaseSerializer]",
    ) -> Self | None:
        if controller.request.user.is_authenticated:
            return self
        return None


class PATBearerAuth(SyncAuth):
    """Authenticates a request carrying a valid Atlas Personal Access Token
    as a Bearer credential. On success, sets `controller.request.user` to
    the token's owning Django user and returns a new instance carrying the
    `ResolvedPersonalAccessToken` (owner + scopes) for a later scope check
    to read — see module docstring.
    """

    __slots__ = ("resolved",)

    def __init__(self, resolved: ResolvedPersonalAccessToken | None = None) -> None:
        self.resolved = resolved

    @property
    @override
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        return {
            "personalAccessToken": SecurityScheme(
                type="http",
                scheme="bearer",
                description="Atlas Personal Access Token",
            ),
        }

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        return {"personalAccessToken": []}

    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: "Controller[BaseSerializer]",
    ) -> Self | None:
        header = controller.request.headers.get("Authorization", "")
        if not header.startswith(_BEARER_PREFIX):
            return None
        raw_token = header.removeprefix(_BEARER_PREFIX).strip()
        if not raw_token:
            return None
        resolved = get_pat_validator()(raw_token)
        if resolved is None:
            return None
        controller.request.user = resolved.user
        return type(self)(resolved=resolved)


def require_scope(controller: "Controller[BaseSerializer]", scope: str) -> None:
    """Deny `controller.request` unless it was authenticated by a
    `PATBearerAuth` whose resolved token carries `scope` — raises a 403
    `APIError` otherwise (`personal-access-tokens` spec: "A request
    authenticated by a PAT SHALL be denied if the operation falls outside
    that token's granted scopes, even when the underlying user's own RBAC
    would otherwise allow it"). A request authenticated some other way (or
    not authenticated at all, which `PATBearerAuth.__call__` already would
    have rejected before an endpoint body runs) has no scopes to check and
    is denied the same way, rather than silently passing.
    """
    auth = request_auth(controller.request)
    if not isinstance(auth, PATBearerAuth) or auth.resolved is None:
        raise APIError(
            format_error(
                "This endpoint requires a Personal Access Token",
                error_type=ErrorType.security,
            ),
            status_code=HTTPStatus.FORBIDDEN,
        )
    if scope not in auth.resolved.scopes:
        raise APIError(
            format_error(
                f"This token's scope does not permit {scope!r}",
                error_type=ErrorType.security,
            ),
            status_code=HTTPStatus.FORBIDDEN,
        )
