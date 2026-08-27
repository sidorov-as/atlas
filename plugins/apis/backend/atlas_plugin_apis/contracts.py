"""Declared contract-only package — the subset of the API
kind's manifest/patch schemas other plugins are allowed to depend on.

Re-exports from `api.schemas` (the single source of truth, also used by
this plugin's own CRUD views): Pydantic types only, no Django models or
business logic, so a dependent plugin never needs to import
`atlas_plugin_apis.api.schemas`/`.models` directly.
"""

from atlas_plugin_apis.api.schemas import ApiIn, ApiSpecPatch
from atlas_plugin_apis.models import ApiDetails

# `ApiDetails.SPEC_SOURCE_*` are plain string constants (a value, not a
# Django model class or business logic), so re-exporting them here — like
# `atlas_plugin_api.catalog`'s `SOURCE_MANUAL`/`SOURCE_YAML` — lets a
# dependent plugin's own code/tests reference a spec source without
# importing `atlas_plugin_apis.models` directly.
SPEC_SOURCE_NONE = ApiDetails.SPEC_SOURCE_NONE
SPEC_SOURCE_INLINE = ApiDetails.SPEC_SOURCE_INLINE
SPEC_SOURCE_URL = ApiDetails.SPEC_SOURCE_URL

__all__ = [
    "SPEC_SOURCE_INLINE",
    "SPEC_SOURCE_NONE",
    "SPEC_SOURCE_URL",
    "ApiIn",
    "ApiSpecPatch",
]
