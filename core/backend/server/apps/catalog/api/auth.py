"""Session-based auth for the entity CRUD API.

Re-exports `atlas_plugin_api.auth`'s `SessionAuth` — canonical home moved
there, since it needs no
`server` import at all. Kept as a same-named re-export so Core's own
internal call sites (Tag/ArchitectureRelationship controllers) don't
need to change.
"""

from atlas_plugin_api.auth import SessionAuth

__all__ = ["SessionAuth"]
