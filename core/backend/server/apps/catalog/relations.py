"""Relation derivation and targeted recompute-on-write.

Re-exports `atlas_plugin_api.relations`'s `recompute_relations`/
`entity_relations` — canonical home moved there
since none of this needs a
concrete `server` import; a plugin recomputes an entity's relations against
`atlas_plugin_api.recompute_relations()`, not this module. Kept as a
same-named re-export so Core's own internal call sites (`api/helpers.py`)
don't need to change.
"""

from atlas_plugin_api.relations import entity_relations, recompute_relations

__all__ = ["entity_relations", "recompute_relations"]
