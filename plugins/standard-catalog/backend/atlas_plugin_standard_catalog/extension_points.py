"""`atlas_plugin_standard_catalog`'s cross-plugin function surface for the
auto-`consumesAPI` write.

`atlas_plugin_apis`'s link-service view needs to write
`ComponentDetails.consumes_apis` when a Service is first linked to one of an
API's Endpoints, but must not import `ComponentDetails`/`atlas_plugin_
standard_catalog.models` directly — the same "one
ORM-backed plugin-to-plugin edge, one narrow function" shape
`atlas_plugin_apis.extension_points.due_for_spec_refresh` already uses for
the reverse direction. Since `atlas.apis` already declares
`requires_plugins={'atlas.standard-catalog': ...}`, it's allowed to call this
function directly (no registry indirection needed, unlike `atlas_plugin_apis
.extension_points.register_delete_guard`, which exists only because
`atlas.standard-catalog` does *not* depend on `atlas.apis` and so can't
import it back).
"""

from atlas_plugin_api import CatalogEntity, recompute_relations

__all__ = ["add_consumed_api"]


def add_consumed_api(
    component_entity: CatalogEntity,
    api_entity: CatalogEntity,
) -> bool:
    """Ensure `component_entity` `consumesAPI` `api_entity`, creating that
    M2M row and recomputing relations only if it isn't already there.

    Returns `True` if this call created a new `consumesAPI` relation, `False`
    if `component_entity` already consumed `api_entity` (the
    `apiRelationCreated` flag). The M2M `.add()` itself is idempotent, but
    the read-before-write here is what lets a caller report which happened
    without a second, separate query of its own — `atlas_plugin_apis` never
    needs to inspect `ComponentDetails.consumes_apis` itself to know.

    Bypasses `ComponentKindHandler.update_details`'s normal spec-PATCH flow
    (that's the whole point — avoiding the race a
    read-modify-write spec-PATCH would have), so `recompute_relations` is
    called explicitly here rather than left to a kind handler to trigger.
    """
    details = component_entity.component_details
    already_present = details.consumes_apis.filter(pk=api_entity.pk).exists()
    if not already_present:
        details.consumes_apis.add(api_entity)
        recompute_relations(component_entity)
    return not already_present
