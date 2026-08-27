"""Shared DMR controller base (`core-plugin-contract-surface` spec: "Core
publishes its plugin-facing surface as contract types").

Kept in its own module, deliberately *not* re-exported from `atlas_plugin_api`'s
top-level `__init__.py` (unlike everything else it publishes):
`dmr.controller.Controller.__init_subclass__` validates DMR's settings the
moment a concrete controller subclass (one with a `serializer` set, like
`AtlasController`) is defined — not lazily, at class-body execution time.
Every other module in this package is deliberately importable before
`django.setup()` (see `catalog.py`'s docstring, `test_catalog.py`'s
"importable without Django setup" guards); `atlas_plugin_api/__init__.py`
importing this module unconditionally would break that for the whole
package, including at plugin-descriptor discovery time (before Django is
configured). A plugin's own `api/views.py` — like Core's original
`server.apps.catalog.api.helpers.AtlasController` before it — is only ever
imported after `django.setup()` (via URL routing), so importing this module
directly there (`from atlas_plugin_api.controllers import AtlasController`)
is safe.
"""

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class AtlasController(Controller):
    """Pin the DMR serializer without relying on generic introspection."""

    serializer = PydanticSerializer
