"""Static plugin descriptor.

`PluginDescriptor` carries a plugin's identity, version, compatibility
ranges, Django app list, and entry-point reference. It must be readable
without importing Django models or triggering `django.setup()`
(plugin-architecture.md:236) — this is what makes computing
`INSTALLED_APPS` from selected descriptors possible before Django starts.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from .authentication import AuthenticationProviderContribution
from .config import PluginConfigSchema

PLUGIN_ENTRY_POINT_GROUP = "atlas.plugins"
"""The `importlib.metadata` entry-point group a plugin distribution's wheel
declares its descriptor under, e.g.:

    [project.entry-points."atlas.plugins"]
    atlas.catalog = "server.apps.catalog.plugin:PLUGIN"

No distribution in this monorepo is packaged as a separate wheel yet,
so nothing currently
publishes entry points under this group — selected plugins are instead
imported directly by the dotted module path listed in `SELECTED_PLUGINS`.
The group name is declared now so real wheel packaging
has a stable target to match.
"""


@dataclass(frozen=True, slots=True)
class PluginDescriptor:
    """Static, Django-setup-independent metadata for one plugin.

    `entry_point` is a `module:attribute` reference — matching the
    `atlas.plugins` entry-point convention — pointing back at this same
    descriptor, e.g. `"server.apps.catalog.plugin:PLUGIN"`. It stays
    meaningful once plugins are discovered via `importlib.metadata` entry
    points instead of today's explicit `SELECTED_PLUGINS` list.
    """

    id: str
    version: str
    compatibility: Mapping[str, str]
    django_apps: tuple[str, ...]
    entry_point: str
    requires_plugins: Mapping[str, str] = field(default_factory=dict)
    """Other plugin ids this plugin declares a manifest dependency on, mapped to
    their required version range (`docs/plugin-architecture.md`'s `requires.plugins`,
    e.g. `{'atlas.standard-catalog': '>=2 <3'}`). Composition fails if a declared
    id isn't among the selected plugins (`composition._check_plugin_dependencies`).
    Defaults to empty so existing descriptors with no dependencies stay unchanged."""

    config_schema: type[PluginConfigSchema] | None = None
    """The plugin's own `PluginConfigSchema` subclass, if it declares one
    `atlas_composer.composition`
    validates a manifest's `plugins[].config` block against it; `None` for a
    plugin with no configuration, so every existing descriptor stays valid
    unchanged."""

    job_ids: tuple[str, ...] = ()
    """`django-apscheduler` job ids this plugin registers (e.g. via its own
    `register_jobs`), if any. The runtime
    entry-point-loading phase pauses these when the plugin is disabled and
    resumes them when active, by id, without this plugin needing its own
    disable/enable hook. Defaults to empty so every existing descriptor
    (and a plugin that schedules nothing) stays valid unchanged."""

    authentication_providers: tuple[AuthenticationProviderContribution, ...] = ()
    """Static authentication-provider contributions exposed before
    ``django.setup()``. Runtime implementations are registered separately
    through ``register_authentication_provider`` after application startup."""

    def __post_init__(self) -> None:
        provider_ids = [item.descriptor.id for item in self.authentication_providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError(
                f"plugin {self.id!r} declares duplicate authentication provider ids"
            )
