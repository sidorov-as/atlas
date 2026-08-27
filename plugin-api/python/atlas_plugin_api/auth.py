"""Session-based auth for the entity CRUD API (`core-plugin-contract-surface`
spec: "Core publishes its plugin-facing surface as contract types").

Wraps Django's own session/`AuthenticationMiddleware` — any endpoint requiring
only a session (safe methods) is satisfied once `request.user` is populated,
regardless of how the session was established. Needs no Django model/Core
dependency at all (just `dmr`, already a direct dependency of every
first-party plugin's own CRUD API), so it moves here outright, the same way
`kinds.py` did. `server.apps.catalog.api.auth` re-exports it for Core's own
internal call sites.
"""

from typing import Self, override

from dmr.controller import Controller
from dmr.endpoint import Endpoint
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security.base import SyncAuth
from dmr.serializer import BaseSerializer


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
