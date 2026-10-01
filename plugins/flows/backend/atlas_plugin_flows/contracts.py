"""Declared contract-only package — the Flow schemas and plain exception
type other plugins (notably the new `atlas.mcp`) are allowed to depend on.

Re-exports `FlowIn`/`FlowPatch` from `api.schemas` (already pure Pydantic,
no Django ORM or `dmr` coupling — the single source of truth, also used by
this plugin's own REST controllers) plus `FlowNotFoundError`, a plain
`LookupError` subclass with no ORM dependency of its own. Both fit the
"types only, no Django models or business logic" bar
`atlas_plugin_apis.contracts` sets. `FlowService` itself is real,
ORM-backed business logic, so — mirroring `atlas_plugin_apis`'s own
contracts/extension_points split — it lives in `extension_points.py`
instead, not here.
"""

from atlas_plugin_flows.api.schemas import FlowIn, FlowPatch


class FlowNotFoundError(LookupError):
    """No `Flow` exists for the given id.

    Mirrors `atlas_plugin_api.entity_service.EntityNotFoundError`'s
    "plain-`LookupError`, no Django model" convention: `FlowService.get`/
    `.update`/`.delete` raise this instead of a `dmr` `APIError`, leaving it
    to each caller (the REST controllers today, `atlas.mcp` tomorrow) to
    translate it into whatever shape its own transport needs.
    """


__all__ = ["FlowIn", "FlowNotFoundError", "FlowPatch"]
