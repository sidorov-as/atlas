"""Shared `kind:name` ref resolver.

Re-exports `atlas_plugin_api.refs`'s `parse_ref`/`resolve_ref`/`RefError`/
`DEFAULT_NAMESPACE` — canonical home moved there
since none of this needs a
concrete `server` import; a plugin resolves/parses refs against
`atlas_plugin_api.resolve_ref()`/`parse_ref()`, not this module. Kept as a
same-named re-export so Core's own internal call sites (`api/schemas.py`,
`api/filters.py`) don't need to change.
"""

from atlas_plugin_api.refs import (
    DEFAULT_NAMESPACE,
    REF_PATTERN,
    RefError,
    parse_ref,
    resolve_ref,
)

__all__ = [
    "DEFAULT_NAMESPACE",
    "REF_PATTERN",
    "RefError",
    "parse_ref",
    "resolve_ref",
]
