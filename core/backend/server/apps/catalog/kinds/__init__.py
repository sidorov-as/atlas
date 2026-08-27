from .capabilities import (
    ARCHITECTURE_ACTOR_V1,
    ARCHITECTURE_SUBJECT_V1,
    SCHEMA_HOST_V1,
)
from .capability_result import CapabilityResult, Error, Ok, Unavailable
from .handler import EntityKindHandler, ValidateDeleteError
from .registry import DuplicateKindError, EntityKindRegistry, registry

__all__ = [
    "ARCHITECTURE_ACTOR_V1",
    "ARCHITECTURE_SUBJECT_V1",
    "SCHEMA_HOST_V1",
    "CapabilityResult",
    "DuplicateKindError",
    "Error",
    "EntityKindHandler",
    "EntityKindRegistry",
    "Ok",
    "Unavailable",
    "ValidateDeleteError",
    "registry",
]

# `server.apps.catalog` registers no concrete Entity Kind of its own — System/
# Component/Resource/Group/Actor are registered by the Standard Catalog
# plugin (`atlas_plugin_standard_catalog.kinds.register_standard_catalog_kinds`)
# and `api` by the APIs plugin (`atlas_plugin_apis.kinds.register_apis_kinds`)
# — core itself owns no kind (plugin-architecture.md's
# core boundary), matching Atlas Core registering nothing at all.
#
# A plugin registers/resolves against `atlas_plugin_api.register_kind()`/
# `resolve_capability()`, not this package directly
# every submodule here is a
# same-named re-export of `atlas_plugin_api.kinds`, kept only for Core's own
# internal call sites.
