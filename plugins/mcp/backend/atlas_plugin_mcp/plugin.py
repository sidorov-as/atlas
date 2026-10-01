"""Static plugin descriptor for the MCP plugin.

`atlas.mcp` publishes a small, curated, MCP-tool-calling-shaped HTTP API
(`search_catalog`, `get_entity`, and — when `atlas.flows` is also
installed — `list_flows`/`get_flow`) authenticated by an Atlas Personal
Access Token (`atlas_plugin_api.auth.PATBearerAuth`), distinct from the
existing SPA-facing API (`mcp-plugin` spec). It has no frontend package —
this plugin exists purely so an external MCP transport process (this
change's own `mcp/` directory, outside composer entirely) has an Atlas HTTP
API to call over `httpx`; nothing in the SPA renders anything for it.

Backend-only, and optional in every distribution but the render
single-container demo (excluded there for the same "keep the free-tier
footprint small" reason `atlas.c4`'s remote-renderer config exists —
`deploy/render/manifest.yaml`'s own comments).

`atlas.flows` is a deliberate *optional, code-level* dependency, not a
manifest `requires_plugins` entry (mirrors `atlas.c4`'s own relationship to
`atlas.apis`, `plugin.py`'s docstring there): `requires_plugins` is always
mandatory in this codebase's composition (`composition._check_plugin_dependencies`
treats every entry that way), which would make the entire plugin —
including catalog tools that have nothing to do with Flow — uninstallable
in any distribution lacking `atlas.flows`. Flow tools instead simply aren't
registered when `atlas_plugin_flows` isn't installed
(`atlas_plugin_mcp.api.urls`, checked at router-build time via
`django.apps.apps.is_installed`, the same mechanism
`atlas_plugin_standard_catalog.kinds`/`atlas_plugin_flows.models` already
use for their own optional link to `atlas.apis`).
"""

from atlas_plugin_api import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="atlas.mcp",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=("atlas_plugin_mcp",),
    entry_point="atlas_plugin_mcp.plugin:PLUGIN",
)
