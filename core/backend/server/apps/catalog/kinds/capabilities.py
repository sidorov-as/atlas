"""Well-known Entity Kind capability identifiers.

Re-exports `atlas_plugin_api.kinds`'s capability id constants — canonical
home moved there. Kept as a
same-named re-export so Core's own internal call sites don't need to change.
"""

from atlas_plugin_api.kinds import (
    ARCHITECTURE_ACTOR_V1,
    ARCHITECTURE_SUBJECT_V1,
    SCHEMA_HOST_V1,
)

__all__ = ["ARCHITECTURE_ACTOR_V1", "ARCHITECTURE_SUBJECT_V1", "SCHEMA_HOST_V1"]
