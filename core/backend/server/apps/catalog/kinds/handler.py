"""Entity Kind Handler protocol (entity-kind-registry spec,
plugin-architecture.md:142-150).

Re-exports `atlas_plugin_api.kinds`'s `EntityKindHandler`/`ValidateDeleteError`
— canonical home moved there,
since neither needs a Django model/metaclass. Kept as a same-named re-export
so Core's own internal call sites (`server.apps.catalog.services.
entity_service`, `api/helpers.py`, tests) don't need to change.
"""

from atlas_plugin_api.kinds import EntityKindHandler, ValidateDeleteError

__all__ = ["EntityKindHandler", "ValidateDeleteError"]
