"""Declared contract-only package — the subset of Standard
Catalog's manifest/patch schemas other plugins are allowed to depend on.

Re-exports from `api.schemas` (the single source of truth, also used by
this plugin's own CRUD views): Pydantic types and value objects only, no
Django models or business logic, so a dependent plugin never needs to
import `atlas_plugin_standard_catalog.api.schemas`/`.models` directly.
"""

from atlas_plugin_standard_catalog.api.schemas import (
    ActorIn,
    ActorSpecPatch,
    ComponentIn,
    ComponentSpecPatch,
    ResourceIn,
    ResourceSpecPatch,
    SystemIn,
    SystemSpecPatch,
)

__all__ = [
    "ActorIn",
    "ActorSpecPatch",
    "ComponentIn",
    "ComponentSpecPatch",
    "ResourceIn",
    "ResourceSpecPatch",
    "SystemIn",
    "SystemSpecPatch",
]
