"""Base catalog entity contract (Core publishes its plugin-facing
surface as contract types).

Stands in for `server.apps.catalog.models.base.CatalogEntity` — Core's single
concrete identity row for every catalog entity kind — without `atlas_plugin_api`
importing it directly: `core/backend` is `package-mode = false` (never an
installable package), so a static import back to `server` would only work via
the shared dev virtualenv, exactly the undeclared coupling this contract
package exists to remove.

No plugin subclasses `CatalogEntity` (audited across every first-party plugin
during the contract-surface audit) — every plugin uses it
as an FK/`OneToOneField` target and performs real Django ORM operations on it
directly. Three pieces cover every real usage, none requiring a `server`
import:

- `CatalogEntity` (this module's `Protocol`) for static type hints.
- `get_catalog_entity_model()` for `.objects`/`.DoesNotExist`/class-attribute
  access, resolved lazily via Django's own app registry — the same mechanism
  `django.contrib.auth.get_user_model()` uses. Only callable after
  `django.setup()`; call it inside a function body, never cache its result at
  plugin module import time.
- `CATALOG_ENTITY_LABEL`, Django's standard lazy string reference for a
  `*Details` model's `entity = OneToOneField(CATALOG_ENTITY_LABEL, ...)`
  target — needs no import of the target class at all.
"""

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from django.apps import apps as _django_apps

if TYPE_CHECKING:
    from collections.abc import Iterable

CATALOG_ENTITY_LABEL = "catalog.CatalogEntity"

KIND_SYSTEM = "system"
KIND_COMPONENT = "component"
KIND_RESOURCE = "resource"
KIND_API = "api"
KIND_GROUP = "group"
# Stored/ref-visible kind stays "user" — see `server.apps.catalog.models.base`
# for why (a Python-identifier-only rename to avoid a naming collision with
# Authentication Core's `Principal` concept).
KIND_ACTOR = "user"

KIND_CHOICES = [
    (KIND_SYSTEM, "System"),
    (KIND_COMPONENT, "Component"),
    (KIND_RESOURCE, "Resource"),
    (KIND_API, "API"),
    (KIND_GROUP, "Group"),
    (KIND_ACTOR, "User"),
]

INGESTIBLE_KINDS = frozenset({KIND_SYSTEM, KIND_COMPONENT, KIND_RESOURCE, KIND_API})

# Provenance (`server.apps.catalog.models.base.CatalogEntity.SOURCE_MANUAL`/
# `.SOURCE_YAML`) — published as module constants, not resolved off
# `get_catalog_entity_model()`, since at least one plugin consumer
# (`atlas_plugin_ingestion.intent.EntityIntent.source_kind`) needs this as a
# dataclass field default evaluated at plugin module import time, before
# Django's app registry is guaranteed ready.
SOURCE_MANUAL = "manual"
SOURCE_YAML = "yaml"
SOURCE_KIND_CHOICES = [
    (SOURCE_MANUAL, "Manual"),
    (SOURCE_YAML, "YAML"),
]

# Removed/Revive/Purge lifecycle — published
# the same way as `SOURCE_*` above, for the same reason: at least one plugin
# consumer (`atlas_plugin_ingestion`'s zombie-entity reconciliation) needs
# these as plain module constants, not resolved off `get_catalog_entity_model()`.
STATUS_ACTIVE = "active"
STATUS_REMOVED = "removed"
STATUS_CHOICES = [
    (STATUS_ACTIVE, "Active"),
    (STATUS_REMOVED, "Removed"),
]

DETAILS_RELATED_NAME = {
    KIND_SYSTEM: "system_details",
    KIND_COMPONENT: "component_details",
    KIND_RESOURCE: "resource_details",
    KIND_API: "api_details",
    KIND_GROUP: "group_details",
    KIND_ACTOR: "actor_details",
}


@runtime_checkable
class CatalogEntity(Protocol):
    """Structural type for Core's `CatalogEntity` row — static typing only.

    A plugin needing real ORM access (`.objects`, `.DoesNotExist`, an FK
    target) uses `get_catalog_entity_model()`/`CATALOG_ENTITY_LABEL` instead;
    this `Protocol` isn't a runtime-substitutable stand-in for the concrete
    model.
    """

    id: Any
    kind: str
    name: str
    namespace: str
    title: str
    description: str
    documentation: str
    labels: dict
    tags: "Iterable[str]"
    links: list
    owner: Any
    owner_id: Any
    source_kind: str
    status: str
    created_at: Any
    updated_at: Any

    SOURCE_MANUAL: str
    SOURCE_YAML: str
    STATUS_ACTIVE: str
    STATUS_REMOVED: str

    @property
    def ref(self) -> str: ...

    @property
    def details(self) -> Any: ...


def get_catalog_entity_model() -> type:
    """Resolve Core's concrete `CatalogEntity` model via Django's app
    registry (`django.apps.apps.get_model`), the same lazy-resolution
    mechanism `django.contrib.auth.get_user_model()` uses.

    Must be called after `django.setup()` — from inside a function body or
    method, never cached at plugin module import time (app loading order
    isn't guaranteed at that point).
    """
    return _django_apps.get_model(CATALOG_ENTITY_LABEL)
