"""Static plugin descriptor for `server.apps.catalog`.

Kept in its own module, separate from `settings/`, so a later extraction
change can move this file wholesale
into a separately packaged distribution instead of untangling it out of
settings code.

`register_runtime()` hands Core's `EntityService` singleton to
`atlas_plugin_api` (`bind_entity_service()`), so `get_entity_service()` can
return it to a plugin without `atlas_plugin_api` ever importing `server`
the same shared "load
selected runtime entry points" phase (`server.apps.plugins.runtime`) that
populates the Entity Kind registry. It does the same for the `PolicyEvaluator`
singleton (`bind_policy_evaluator()`), for the `adopt`/
`blocked_by`/`blocked_by_reason` functions (`bind_entity_helpers()` —
these need Core's own `EntityWritePermission` and a
conditionally-installed plugin, neither of which `atlas_plugin_api` may
depend on), and for the PAT validation function (`bind_pat_validator()` —
`atlas_plugin_api.auth.PATBearerAuth` needs it the same way a plugin
calling `EntityService` needs `bind_entity_service()`, since
`PersonalAccessToken` is a real Django model `atlas_plugin_api` cannot
import). The APIs plugin
moved the last kind core registered directly (`api`) out to
`atlas_plugin_apis`, so these are this app's only runtime registrations left.
"""

from atlas_plugin_api import (
    AuthenticationProviderContribution,
    PluginDescriptor,
)
from atlas_plugin_api.architecture_relationships import (
    bind_architecture_relationship_service,
)
from atlas_plugin_api.entity_helpers import bind_entity_helpers
from atlas_plugin_api.entity_service import bind_entity_service
from atlas_plugin_api.membership import bind_membership_service
from atlas_plugin_api.pat import bind_pat_validator
from atlas_plugin_api.permissions import bind_policy_evaluator

from .auth_descriptors import LOCAL_PROVIDER_DESCRIPTOR

PLUGIN = PluginDescriptor(
    id="atlas.catalog",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("server.apps.catalog",),
    entry_point="server.apps.catalog.plugin:PLUGIN",
    authentication_providers=(
        AuthenticationProviderContribution(
            descriptor=LOCAL_PROVIDER_DESCRIPTOR,
            supported_group_sync_modes=("none",),
        ),
    ),
)


def register_runtime() -> None:
    from atlas_plugin_api import (
        register_authentication_provider,
        register_search_source,
    )

    from server.apps.catalog.api.helpers import (
        adopt,
        blocked_by,
        blocked_by_reason,
    )
    from server.apps.catalog.authorization import policy_evaluator
    from server.apps.catalog.local_authentication import LocalCredentialProvider
    from server.apps.catalog.membership import membership_service
    from server.apps.catalog.search_source import catalog_search_source
    from server.apps.catalog.services.architecture_relationship_service import (
        architecture_relationship_service,
    )
    from server.apps.catalog.services.entity_service import entity_service
    from server.apps.catalog.services.pat_service import (
        validate_personal_access_token,
    )

    register_authentication_provider(LocalCredentialProvider(), owner=PLUGIN.id)
    register_search_source(catalog_search_source, owner=PLUGIN.id)

    bind_entity_service(entity_service)
    bind_architecture_relationship_service(architecture_relationship_service)
    bind_policy_evaluator(policy_evaluator)
    bind_membership_service(membership_service)
    bind_entity_helpers(
        adopt=adopt,
        blocked_by=blocked_by,
        blocked_by_reason=blocked_by_reason,
    )
    bind_pat_validator(validate_personal_access_token)
