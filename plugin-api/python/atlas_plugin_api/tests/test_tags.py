"""Tag contract tests.

No Django settings are configured in this package's own test environment
(see `test_catalog.py`'s equivalent guard); `get_tag_model()`/
`ensure_tags_exist()` resolving against the real concrete model is covered
from Core's side (`core/backend/server/apps/catalog/tests/
test_plugin_contract_surface.py`).
"""

from atlas_plugin_api.tags import DEFAULT_TAG_COLOR, TAG_LABEL, TAG_PALETTE


def test_tag_label_matches_core_app_label():
    assert TAG_LABEL == "catalog.Tag"


def test_tag_palette_constants():
    assert DEFAULT_TAG_COLOR == TAG_PALETTE[0]
    assert "blue" in TAG_PALETTE


def test_tags_module_is_importable_without_django_setup():
    import atlas_plugin_api.tags  # noqa: F401
