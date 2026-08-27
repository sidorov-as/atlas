"""Imports each locked backend plugin's real `PluginDescriptor`
(`atlas_plugin_api.descriptor`), for `composition.py`'s checks that need
compatibility ranges and manifest dependencies.

Only `workspace`-sourced plugins are resolvable this way, matching
`resolver.py`'s current scope: every locked plugin's backend package must
already be importable in the composer's own Python environment (true for
this monorepo's own build, where every plugin package is a `develop=true`
path dependency of the same `core/backend` virtualenv this composer runs
in; a real external operator's build would install the resolved packages
into the composer's environment before running this step).
"""

from importlib import import_module

from atlas_plugin_api import PluginDescriptor

from .generate import backend_module_path
from .lock import Lock


def load_backend_descriptors(lock: Lock) -> dict[str, PluginDescriptor]:
    """Import every locked plugin's backend module and return its `PLUGIN`
    descriptor, keyed by plugin id."""
    descriptors: dict[str, PluginDescriptor] = {}
    for key, locked in lock.plugins.items():
        if locked.backend is None:
            continue
        plugin_id = key.rsplit('@', 1)[0]
        module = import_module(backend_module_path(locked.backend.package))
        descriptors[plugin_id] = module.PLUGIN
    return descriptors
