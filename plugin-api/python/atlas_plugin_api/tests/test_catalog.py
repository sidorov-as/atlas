"""Base catalog entity contract tests (`core-plugin-contract-surface` spec).

No Django settings are configured in this package's own test environment
(`atlas_plugin_api` must stay importable without one — see
`test_descriptor.py`'s equivalent guard), so these tests cover the
Django-independent half of the contract (the `Protocol`, the constants, the
label). `get_catalog_entity_model()` resolving to the real concrete model is
covered from Core's side, where Django is actually configured (`core/backend/
server/apps/catalog/tests/test_plugin_contract_surface.py`).
"""

from typing import ClassVar

from atlas_plugin_api.catalog import (
    CATALOG_ENTITY_LABEL,
    DETAILS_RELATED_NAME,
    INGESTIBLE_KINDS,
    KIND_ACTOR,
    KIND_API,
    KIND_CHOICES,
    KIND_COMPONENT,
    KIND_GROUP,
    KIND_RESOURCE,
    KIND_SYSTEM,
    CatalogEntity,
)


def test_catalog_entity_label_matches_core_app_label():
    # 'catalog' is `server.apps.catalog`'s Django app_label — see
    # `server.apps.catalog.apps.CatalogConfig` and every plugin `*Details`
    # model's `Meta.app_label = 'catalog'`.
    assert CATALOG_ENTITY_LABEL == "catalog.CatalogEntity"


def test_kind_constants():
    assert (
        KIND_SYSTEM,
        KIND_COMPONENT,
        KIND_RESOURCE,
        KIND_API,
        KIND_GROUP,
        KIND_ACTOR,
    ) == (
        "system",
        "component",
        "resource",
        "api",
        "group",
        "user",
    )
    assert {kind for kind, _ in KIND_CHOICES} == {
        KIND_SYSTEM,
        KIND_COMPONENT,
        KIND_RESOURCE,
        KIND_API,
        KIND_GROUP,
        KIND_ACTOR,
    }
    assert INGESTIBLE_KINDS == {KIND_SYSTEM, KIND_COMPONENT, KIND_RESOURCE, KIND_API}
    assert KIND_GROUP not in INGESTIBLE_KINDS
    assert KIND_ACTOR not in INGESTIBLE_KINDS


def test_details_related_name_covers_every_kind():
    assert set(DETAILS_RELATED_NAME) == {
        KIND_SYSTEM,
        KIND_COMPONENT,
        KIND_RESOURCE,
        KIND_API,
        KIND_GROUP,
        KIND_ACTOR,
    }


def test_catalog_entity_protocol_is_structural():
    class _FakeEntity:
        id = "e1"
        kind = KIND_SYSTEM
        name = "user-management"
        namespace = "default"
        title = ""
        description = ""
        documentation = ""
        labels: ClassVar[dict] = {}
        tags: ClassVar[list] = []
        links: ClassVar[list] = []
        owner = None
        owner_id = None
        source_kind = "manual"
        status = "active"
        created_at = None
        updated_at = None

        SOURCE_MANUAL = "manual"
        SOURCE_YAML = "yaml"
        STATUS_ACTIVE = "active"
        STATUS_REMOVED = "removed"

        @property
        def ref(self) -> str:
            return f"{self.kind}:{self.name}"

        @property
        def details(self):
            return None

    assert isinstance(_FakeEntity(), CatalogEntity)


def test_catalog_module_is_importable_without_django_setup():
    # A regression guard, mirroring `test_descriptor.py`'s equivalent: this
    # package has no configured Django settings in its own test environment,
    # so importing `atlas_plugin_api.catalog` (and calling `apps.get_model`
    # lazily only from within `get_catalog_entity_model`, never at import
    # time) must not raise.
    import atlas_plugin_api.catalog  # noqa: F401
