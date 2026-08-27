---
title: Choose a plugin layout
description: Structure an Atlas plugin as a backend package, frontend package, or coordinated pair.
audience:
  - plugin-author
page-type: guide
---

# Choose a plugin layout

Atlas supports three package shapes. Choose the smallest shape that owns the
behavior you need. Backend functionality does not require a frontend package,
and a composed UI contribution does not require a backend package.

| Shape | Use it when | Required responsibility |
| --- | --- | --- |
| Backend-only | The plugin provides data, APIs, ingestion, a capability, an extension point, permissions, or scheduled work but no UI. | A Python package with a `PluginDescriptor`, Django apps and migrations where needed, and runtime registration for its backend contracts. |
| Frontend-only | The plugin contributes routes, navigation, tabs, or widgets without plugin-owned backend behavior. | A TypeScript package exporting one `defineFrontendPlugin()` declaration with its immutable contributions. |
| Full-stack | The user-facing feature needs plugin-owned backend behavior and UI. | Both packages, selected under the same plugin id and composed together; the frontend calls public HTTP APIs or public configuration, never backend Python modules. |

## Backend package

Place backend code under a Python package such as
`plugins/your-plugin/backend/atlas_plugin_your_plugin/`. Its `plugin.py`
exports a static `PluginDescriptor`:

```python
PLUGIN = PluginDescriptor(
    id='atlas.your-plugin',
    version='0.1.0',
    compatibility={'atlasCore': '>=0.1 <1'},
    django_apps=('atlas_plugin_your_plugin',),
    entry_point='atlas_plugin_your_plugin.plugin:PLUGIN',
    requires_plugins={'atlas.standard-catalog': '>=0.1 <1'},
)
```

The descriptor declares the plugin at composition time. It identifies the
plugin, states the Core compatibility range, supplies the Django applications,
identifies its entry point, and declares mandatory plugin dependencies. Add
`config_schema` only for typed plugin configuration and `job_ids` only for
plugin-owned scheduled jobs. A dependency listed in `requires_plugins` is
mandatory. Atlas has no separate optional-dependency declaration.

The backend owns its Django models, migrations, API routes, configuration
schema, and internal business logic. If it provides Entity Kinds, capabilities,
permissions, or implementations for a plugin-owned extension point, expose a
`register_runtime()` hook in the entry-point module. The hook runs after Django
setup for active plugins. It must not register anything as an import side
effect. A backend package with no runtime registration may omit the hook.

## Frontend package

Place frontend code under a TypeScript package such as
`plugins/your-plugin/frontend/`. Its entry module exports the one composed
plugin declaration:

```ts
export const yourPlugin = defineFrontendPlugin({
  id: 'atlas.your-plugin',
  contributions: [
    route({ id: 'atlas.your-plugin.home', path: '/your-plugin', component: YourPage }),
    navItem({ id: 'atlas.your-plugin.nav', title: 'Your plugin', route: routeRef('atlas.your-plugin.home') }),
  ],
})
```

The frontend owns its pages, components, contribution declarations, and tests.
It imports only the TypeScript plugin API and permitted core frontend
contracts. It does not import a sibling plugin's source. Contributions are data
declared at module load time. The composer detects duplicate ids and
conflicting routes when it builds the selected distribution.

When the frontend needs data, use the running Atlas HTTP API. When it needs
settings, read only the backend's explicit public configuration projection; a
secret reference or resolved secret is never a frontend value.

## Coordinating a full-stack plugin

Use the same plugin id and version/compatibility intent across the backend and
frontend package declarations selected by the distribution. Keep this boundary
clear:

- backend changes define API, authorization, persistence, and runtime
  contracts first;
- frontend changes define the route or other contribution and present API
  results; and
- composition, backend tests, and frontend tests verify the two packages in
  the selected distribution.

Do not use a full-stack layout just to share an implementation detail. A
frontend-only UI can use an existing public API. A backend-only plugin can
operate without a corresponding page.

## Verify the layout

Before moving to the tutorial, check that the distribution can identify every
selected package, required backend dependencies are declared, the frontend
exports its one plugin declaration when present, and no cross-package import
crosses a Core or sibling-plugin boundary. See [Assembling a
distribution](../configuration/distributions.md) for preflight and
[Extension points and capabilities](extension-points.md) for the contracts a
package may register.
