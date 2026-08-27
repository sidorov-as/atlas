"""Central plugin configuration resolution (`plugin-configuration-isolation`
spec).

The single place a plugin's manifest-declared config becomes the typed
object that plugin's own code reads (`plugin-configuration-isolation` spec:
"A plugin SHALL receive only its own validated, namespaced configuration
object; it SHALL NOT read global Django settings or environment variables
directly") — `settings/components/common.py` registers each configured
plugin here at settings-load time; plugin code reads its own resolved object
back through the public `atlas_plugin_api.get_plugin_config` boundary.

Secret resolution (`atlas_plugin_api.config.resolve_secrets`) runs here,
not in the composer: the composer only ever sees the manifest's raw
`fromEnv` reference (build time, no access to a real deployment's secret
environment); this registry resolves it once, in memory, against
`os.environ` at process startup — the resolved value is never written back
to a file, so it cannot reach the lock file, the frontend bundle, or the
generated backend/frontend composition modules (`atlas_composer.generate`
never sees a plugin's config at all).
"""

from atlas_plugin_api import (
    PluginConfigSchema,
    bind_plugin_config,
    resolve_secrets,
)


class PluginConfigRegistry:
    """The keyed collection of every configured plugin's resolved config."""

    def __init__(self, *, publish: bool = False) -> None:
        self._resolved: dict[str, PluginConfigSchema] = {}
        self._publish = publish

    def register(
        self,
        plugin_id: str,
        schema: type[PluginConfigSchema],
        raw: dict,
    ) -> PluginConfigSchema:
        """Validate `raw` (a manifest `plugins[].config` block) against
        `schema`, resolve any `fromEnv` secret reference it declares, and
        store the result under `plugin_id`. Returns the resolved config for
        callers that need it immediately."""
        parsed = schema.model_validate(raw)
        resolved = resolve_secrets(parsed)
        self._resolved[plugin_id] = resolved
        if self._publish:
            bind_plugin_config(plugin_id, resolved, owner="atlas.core")
        return resolved

    def get(self, plugin_id: str) -> PluginConfigSchema | None:
        return self._resolved.get(plugin_id)

    def public_bootstrap_config(self) -> dict[str, dict]:
        """Every registered plugin's public projection, keyed by plugin id
        — the public bootstrap configuration response
        (`plugin-configuration-isolation` spec: "no other configuration
        field SHALL be exposed to the frontend"). Never includes a field a
        plugin didn't explicitly declare in its schema's `PUBLIC_FIELDS`,
        and therefore never a secret value: `PluginConfigSchema.
        public_projection` itself refuses to include a secret-capable
        field."""
        return {
            plugin_id: config.public_projection()
            for plugin_id, config in self._resolved.items()
        }


registry = PluginConfigRegistry(publish=True)
"""Core's process-wide resolved configuration registry."""
