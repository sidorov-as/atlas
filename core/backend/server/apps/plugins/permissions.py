"""Core permission registry.

Re-exports `atlas_plugin_api.permissions`'s `PermissionRegistry`/
`DuplicatePermissionError`/`registry` singleton — canonical home moved there
since none of this needs a
Django model; a plugin registers a permission id via
`atlas_plugin_api.register_permission()`, not this module. Kept as a
same-named re-export so Core's own internal call sites (composition
validation, startup logging, tests) don't need to change.
"""

from atlas_plugin_api.permissions import (
    DuplicatePermissionError,
    PermissionRegistry,
    registry,
)

__all__ = ["DuplicatePermissionError", "PermissionRegistry", "registry"]
