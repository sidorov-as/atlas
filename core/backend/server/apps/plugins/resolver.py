"""Static-phase selected-plugin resolver.

Reads the plugins named in `SELECTED_PLUGINS`, and computes `INSTALLED_APPS`
from only their declared `django_apps` — an importable-but-unselected
plugin contributes nothing. Runs before `django.setup()`
(plugin-architecture.md:390-394), so this module and everything it imports
must stay free of Django app-registry/model imports.
"""

from collections.abc import Iterable, Sequence
from importlib import import_module

from atlas_plugin_api import PluginDescriptor


class MissingPluginDescriptorError(ImportError):
    """Raised when a `SELECTED_PLUGINS` entry has no module-level `PLUGIN`."""

    def __init__(self, module_path: str) -> None:
        super().__init__(f"{module_path!r} has no module-level `PLUGIN`")
        self.module_path = module_path


class InvalidPluginDescriptorError(ValueError):
    """Raised when a selected descriptor fails identity verification."""


class DuplicatePluginIdError(InvalidPluginDescriptorError):
    """Raised when two selected descriptors declare the same plugin `id`."""

    def __init__(self, plugin_id: str) -> None:
        super().__init__(
            f"More than one selected plugin declares id={plugin_id!r}",
        )
        self.plugin_id = plugin_id


def load_selected_descriptors(
    selected_plugins: Iterable[str],
) -> tuple[PluginDescriptor, ...]:
    """Import each `SELECTED_PLUGINS` module path and return its `PLUGIN`."""
    descriptors = []
    for module_path in selected_plugins:
        module = import_module(module_path)
        try:
            descriptors.append(module.PLUGIN)
        except AttributeError as exc:
            raise MissingPluginDescriptorError(module_path) from exc
    return tuple(descriptors)


def verify_selected_descriptors(
    descriptors: Iterable[PluginDescriptor],
) -> None:
    """Verify selected descriptors' static identities before `django.setup()`.

    Checks only what's decidable from the descriptors themselves — a
    non-empty `id`/`version`, and no two selected plugins sharing an `id`.
    Real compatibility-range verification (`compatibility` against actual
    platform/plugin-API versions) has no source of truth to check against
    yet, so it's deferred, as for cross-plugin
    validation generally.
    """
    seen_ids: set[str] = set()
    for descriptor in descriptors:
        if not descriptor.id or not descriptor.version:
            raise InvalidPluginDescriptorError(
                f"Plugin descriptor {descriptor!r} is missing an id or version",
            )
        if descriptor.id in seen_ids:
            raise DuplicatePluginIdError(descriptor.id)
        seen_ids.add(descriptor.id)


def resolve_installed_apps(
    descriptors: Iterable[PluginDescriptor],
    *,
    additional_apps: Sequence[str] = (),
) -> tuple[str, ...]:
    """Flatten selected descriptors' `django_apps` plus the non-plugin apps."""
    django_apps: list[str] = []
    for descriptor in descriptors:
        django_apps.extend(descriptor.django_apps)
    return (*django_apps, *additional_apps)
