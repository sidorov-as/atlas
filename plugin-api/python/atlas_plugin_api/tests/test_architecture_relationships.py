"""Architecture Relationship contract tests.

No Django settings are configured in this package's own test environment
(see `test_catalog.py`'s equivalent guard); `get_architecture_relationship_model()`
resolving to the real concrete model is covered from Core's side
(`core/backend/server/apps/catalog/tests/test_plugin_contract_surface.py`).
"""

from atlas_plugin_api.architecture_relationships import (
    ARCHITECTURE_RELATIONSHIP_LABEL,
    ARCHITECTURE_RELATIONSHIP_ORIGIN_MANUAL,
    ARCHITECTURE_RELATIONSHIP_ORIGIN_YAML,
)


def test_architecture_relationship_label_matches_core_app_label():
    assert ARCHITECTURE_RELATIONSHIP_LABEL == "catalog.ArchitectureRelationship"


def test_origin_constants():
    assert ARCHITECTURE_RELATIONSHIP_ORIGIN_MANUAL == "manual"
    assert ARCHITECTURE_RELATIONSHIP_ORIGIN_YAML == "yaml"


def test_architecture_relationships_module_is_importable_without_django_setup():
    import atlas_plugin_api.architecture_relationships  # noqa: F401
