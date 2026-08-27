"""Static plugin descriptor for the APIs plugin.

The API Entity Kind — `ApiDetails`/`ApiKindHandler`, its spec-source/spec-URL
resolution, and its CRUD routes — lives here, split out of
`server.apps.catalog`, which previously owned this kind directly.

Optional in the official distribution: unlike `atlas.standard-catalog`, omitting it from
`SELECTED_PLUGINS` must not fail composition — it's absent from
`server.apps.plugins.composition.REQUIRED_PLUGINS`. It does, however,
declare a manifest dependency on `atlas.standard-catalog` (for `Component`'s
`providesApis`/`consumesApis` fields, and its own `system` reference) —
a real manifest dependency between plugins, checked by
`server.apps.plugins.composition._check_plugin_dependencies`.
"""

from atlas_plugin_api import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="atlas.apis",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_apis",),
    entry_point="atlas_plugin_apis.plugin:PLUGIN",
    requires_plugins={"atlas.standard-catalog": ">=0.1 <1"},
)

# `Endpoint` is plugin-owned child data, not a registered Entity Kind
# so it gets no
# automatic `{kind}.read`/`{kind}.edit` permission pair the way `api` does —
# it needs its own explicit permission, checked the same way
# `atlas.c4.diagram.read` is (`atlas_plugin_c4.permissions`).
ENDPOINT_READ_PERMISSION = "atlas.apis.endpoint.read"

# Purge of a removed Endpoint: gated the same way as whole-entity Purge — the
# permission name ending in `.purge` is what `RBACPolicyEvaluator` matches on
# to route the check through `has_purge_grant` rather than plain ownership
# (`server.apps.catalog.authorization`); checked against the owning `api`
# entity as `resource` since `Endpoint` has no owner Group of its own to
# scope a grant to (it inherits `api`'s owner).
ENDPOINT_PURGE_PERMISSION = "atlas.apis.endpoint.purge"

# `ServiceEndpointUsage` link permissions. Like
# `ENDPOINT_READ_PERMISSION`, `ServiceEndpointUsage` has no owner of its own
# to check membership against, so `.create`/`.delete` are checked the same
# unrestricted-if-authenticated way `.read` is — `RBACPolicyEvaluator` treats
# all three suffixes alike for exactly this reason
# (`server.apps.catalog.authorization`).
ENDPOINT_DEPENDENCY_READ_PERMISSION = "atlas.apis.endpointDependency.read"
ENDPOINT_DEPENDENCY_CREATE_PERMISSION = "atlas.apis.endpointDependency.create"
ENDPOINT_DEPENDENCY_DELETE_PERMISSION = "atlas.apis.endpointDependency.delete"

# `Operation` is plugin-owned child data, not a registered Entity Kind either
# same
# unrestricted-if-authenticated permission shape as `ENDPOINT_READ_PERMISSION`.
OPERATION_READ_PERMISSION = "atlas.apis.operation.read"

# Purge of a removed Operation — same shape as `ENDPOINT_PURGE_PERMISSION`.
OPERATION_PURGE_PERMISSION = "atlas.apis.operation.purge"

# `ServiceOperationUsage` link permissions — same unrestricted-if-authenticated shape as
# `ENDPOINT_DEPENDENCY_*_PERMISSION`; no evaluator change needed (
# `RBACPolicyEvaluator` already grants `.create`/`.delete` to any
# authenticated principal for `resource=None`).
OPERATION_DEPENDENCY_READ_PERMISSION = "atlas.apis.operationDependency.read"
OPERATION_DEPENDENCY_CREATE_PERMISSION = "atlas.apis.operationDependency.create"
OPERATION_DEPENDENCY_DELETE_PERMISSION = "atlas.apis.operationDependency.delete"


def register_runtime() -> None:
    """Populate this plugin's runtime registrations.

    Called by the shared "load selected runtime entry points" phase
    (`server.apps.plugins.runtime.load_runtime_entry_points`), after
    `django.setup()` — never at import time.
    """
    from atlas_plugin_api import register_permission

    from atlas_plugin_apis.kinds import register_apis_kinds

    register_apis_kinds(owner=PLUGIN.id)
    register_permission(ENDPOINT_READ_PERMISSION, owner=PLUGIN.id)
    register_permission(ENDPOINT_PURGE_PERMISSION, owner=PLUGIN.id)
    register_permission(ENDPOINT_DEPENDENCY_READ_PERMISSION, owner=PLUGIN.id)
    register_permission(ENDPOINT_DEPENDENCY_CREATE_PERMISSION, owner=PLUGIN.id)
    register_permission(ENDPOINT_DEPENDENCY_DELETE_PERMISSION, owner=PLUGIN.id)
    register_permission(OPERATION_READ_PERMISSION, owner=PLUGIN.id)
    register_permission(OPERATION_PURGE_PERMISSION, owner=PLUGIN.id)
    register_permission(OPERATION_DEPENDENCY_READ_PERMISSION, owner=PLUGIN.id)
    register_permission(OPERATION_DEPENDENCY_CREATE_PERMISSION, owner=PLUGIN.id)
    register_permission(OPERATION_DEPENDENCY_DELETE_PERMISSION, owner=PLUGIN.id)
