"""Fixture plugin with both runtime hooks, recording the order they ran in."""

from server.apps.plugins import PluginDescriptor

from . import plugin_with_hook

PLUGIN = PluginDescriptor(
    id="fixture.with-finalize",
    version="0.0.0",
    compatibility={},
    django_apps=(),
    entry_point="server.apps.plugins.tests.fixtures.plugin_with_finalize:PLUGIN",
)

calls: list[str] = []
finalized_after_all_registered = False
fail = False


def register_runtime() -> None:
    calls.append("register")


def finalize_runtime() -> None:
    global finalized_after_all_registered
    # The other fixture plugin is listed after this one, so its registration
    # only exists if finalization really waited for every register_runtime().
    finalized_after_all_registered = "fixture.with-hook" in (
        plugin_with_hook.runtime_calls
    )
    calls.append("finalize")
    if fail:
        raise RuntimeError("finalize failed")
