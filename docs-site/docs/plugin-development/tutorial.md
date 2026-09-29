---
title: Build your first plugin
description: Create, compose, test, run, and verify a minimal Atlas plugin.
audience:
  - plugin-author
page-type: tutorial
---

# Build your first plugin

This tutorial creates `atlas.hello-atlas`: a deliberately small full-stack
plugin. It contributes one page and navigation item, but owns no catalog data,
permission, configuration, or runtime registry. That keeps the first result
visible while showing the two declarations every full-stack plugin needs.

## Prerequisites and outcome

Start from a checkout that can run the [local development
guide](../getting-started/development.md). Read [Choose an extension
mechanism](choose-an-extension.md) first: this tutorial chooses a frontend
Contribution because it adds a page, not an Entity Kind or Facet.

If your plugin needs to attach data to an existing catalog entity, choose a
Facet instead. The [Database Schema architectural case
study](built-in/database-schema.md#decision-1-keep-schema-data-independent-of-the-resource-kind)
shows why that choice keeps plugin-owned data independent of the owning kind.

You will create the files in the checked-in [first-plugin example bundle][example].
Its Python descriptor and focused test are authoritative, source-backed
examples; the page quotes only the short declarations that the bundle owns.
At the end, composition accepts the selected plugin, its descriptor test
passes, and **Hello Atlas** is visible in the running application.

[example]: https://github.com/sidorov-as/atlas/tree/main/docs-site/examples/first-plugin

## 1. Create the two package declarations

Copy the bundle into your plugin workspace, preserving the backend Python
package and frontend source boundary. A real plugin package also needs normal
Python and npm package metadata so the build can install it; use
[Choose a plugin layout](plugin-layouts.md) for those package-level
responsibilities.

Create `backend/atlas_plugin_hello/plugin.py`:

```python
from atlas_plugin_api import PluginDescriptor

PLUGIN = PluginDescriptor(
    id="atlas.hello-atlas",
    version="0.1.0",
    compatibility={"atlasCore": ">=0.1 <1"},
    django_apps=(),
    entry_point="atlas_plugin_hello.plugin:PLUGIN",
)
```

The descriptor is static: it can be read before Django starts. This first
plugin has no models, routes, permissions, capabilities, or jobs, so it has no
`django_apps`, `requires_plugins`, or `register_runtime()` hook. Add those only
when the behavior needs their contract.

Create `frontend/src/index.ts`:

```typescript
import { defineFrontendPlugin, navItem, route, routeRef } from '@atlas/plugin-api'
import { HelloAtlasPage } from './HelloAtlasPage'

export const helloAtlasPlugin = defineFrontendPlugin({
  id: 'atlas.hello-atlas',
  contributions: [
    route({ id: 'atlas.hello-atlas.home', path: '/hello-atlas', component: HelloAtlasPage }),
    navItem({ id: 'atlas.hello-atlas.nav', title: 'Hello Atlas', route: routeRef('atlas.hello-atlas.home') }),
  ],
})
```

Then make `HelloAtlasPage` render a heading, for example
`<h1>Hello Atlas</h1>`. Contribution ids are globally unique in a distribution;
the composer rejects a duplicate id, duplicate route, or a route that conflicts
with Core. The frontend declaration is data at module load time. Do not mutate a
global registry or import a sibling plugin's source.

For a production-sized example of detail-page contributions, see [Decision 2
in the Database Schema case
study](built-in/database-schema.md#decision-2-target-contributions-by-capability-not-kind-name).
It has two tabs and makes their applicability a capability predicate rather
than a hard-coded `Resource` check.

## 2. Select it in a development distribution

Add backend and frontend artifacts under the same id and version in the
development manifest. `workspace` is the source type the checked-in composer
can resolve:

```yaml
plugins:
  - id: atlas.hello-atlas
    version: 0.1.0
    backend:
      package: atlas-plugin-hello-atlas
      source: workspace
    frontend:
      package: "@atlas/plugin-hello-atlas"
      source: workspace
```

Keep this entry next to the package paths that make the artifacts importable to
the composer and available to the frontend workspace. Do not add the tutorial
plugin to the checked-in default distribution: it is a learning fixture, not a
product feature.

Resolve and validate your manifest (replace the paths with your development
distribution; do not overwrite the checked-in default lock):

```shell
uv run --project composer atlas-compose resolve path/to/development-manifest.yaml -o /tmp/hello-atlas.lock.yaml
uv run --project composer atlas-compose validate path/to/development-manifest.yaml /tmp/hello-atlas.lock.yaml
```

Both commands should finish successfully. A missing package, identity/version
mismatch, duplicate route, or contribution-id collision is a
composition error; fix the declaration rather than bypassing validation. See
[Fix composition errors](../operating-atlas/composition-errors.md) for the
failure category and correction.

## 3. Test the backend declaration

The bundle test imports the exact descriptor file and asserts its composition
metadata. From `core/backend`, run:

```shell
poetry run pytest ../../docs-site/examples/first-plugin/first-plugin-backend/tests -q
poetry run ruff check ../../docs-site/examples/first-plugin/first-plugin-backend
poetry run ruff format --check ../../docs-site/examples/first-plugin/first-plugin-backend
```

The focused test, lint, and format checks should pass. Keep an equivalent
focused test in your plugin package; a descriptor that only appears
in prose cannot prove that it remains importable or names the right entry point.

## 4. Run and visibly verify it

Generate your development composition inputs from the validated lock, then
start Atlas with the [local development commands](../getting-started/development.md).
Open `http://localhost:5173/hello-atlas`, or select **Hello Atlas** in the
navigation. The page heading confirms that the selected frontend package was
composed, its route was accepted, and the running UI rendered its contribution.

If the page is absent, first check that the frontend artifact was selected and
the generated composition inputs were rebuilt. If the route fails to compose,
use the error's contribution or route id with the [composition-error guide](../operating-atlas/composition-errors.md).
If the backend cannot start, ensure the descriptor's package and entry point
are importable before changing application settings.

## What to add next

This plugin intentionally does not persist data or expose an API. Add an
[Entity Kind or Facet](entity-kinds-and-facets.md) only when the plugin owns
catalog data; use [Extension points and capabilities](extension-points.md) for
cross-plugin collaboration. The [Database Schema architectural case
study](built-in/database-schema.md) shows a real Facet plus capability-gated
detail-page contributions.
