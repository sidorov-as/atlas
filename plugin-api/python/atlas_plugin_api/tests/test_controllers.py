"""Shared DMR controller base tests.

Unlike every other test module in this package, `controllers.py` genuinely
needs Django settings configured to import at all (see its module
docstring) — this test relies on the full backend suite's
`DJANGO_SETTINGS_MODULE`, exactly like Core's original
`server.apps.catalog.api.helpers.AtlasController` did.
"""

from dmr.plugins.pydantic import PydanticSerializer

from atlas_plugin_api.controllers import AtlasController


def test_atlas_controller_pins_the_pydantic_serializer():
    assert AtlasController.serializer is PydanticSerializer
