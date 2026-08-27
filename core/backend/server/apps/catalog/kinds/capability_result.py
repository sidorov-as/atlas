"""Typed capability-call result.

Re-exports `atlas_plugin_api.kinds`'s `CapabilityResult`/`Ok`/`Unavailable`/
`Error` — canonical home moved there, since none of this needs a Django
model/metaclass. Kept as a
same-named re-export so Core's own internal call sites
(`server.apps.catalog.services.entity_service`, `api/helpers.py`, tests)
don't need to change.
"""

from atlas_plugin_api.kinds import CapabilityResult, Error, Ok, Unavailable

__all__ = ["CapabilityResult", "Error", "Ok", "Unavailable"]
