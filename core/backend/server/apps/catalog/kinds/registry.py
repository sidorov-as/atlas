"""Core Entity Kind registry.

Re-exports `atlas_plugin_api.kinds`'s `EntityKindRegistry`/`DuplicateKindError`/
`registry` singleton — canonical home moved there
since none of this needs a
Django model/metaclass; a plugin registers against it via
`atlas_plugin_api.register_kind()`, not this module. Kept as a same-named
re-export so Core's own internal call sites
(`server.apps.catalog.services.entity_service`, tests) don't need to change.

Populated during the shared "load selected runtime entry points" phase
(`server.apps.plugins.runtime`), via each selected plugin's
`register_runtime()` hook (`register_default_kinds` below is
`server.apps.catalog.plugin`'s). That phase — not `CatalogConfig.ready()`
directly — owns this call.
"""

from atlas_plugin_api.kinds import (
    DuplicateKindError,
    EntityKindRegistry,
    registry,
)

__all__ = ["DuplicateKindError", "EntityKindRegistry", "registry"]
