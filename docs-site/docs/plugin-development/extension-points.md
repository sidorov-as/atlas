---
title: Frontend contributions
description: Add routes, navigation items, entity-detail tabs, and home widgets that compose safely into an Atlas distribution.
audience:
  - plugin-author
page-type: guide
---

# Frontend contributions

Use a frontend contribution when a plugin needs to add something visible to
Atlas: a route, a navigation item, an entity-detail tab, or a home-page
widget. A frontend-only plugin may contain only these declarations; a
full-stack plugin keeps its UI declaration beside its public HTTP API client.

## Audience, prerequisites, and outcome

This guide is for plugin authors whose distribution already selects a frontend
package. Choose a [plugin layout](plugin-layouts.md), use the current
`@atlas/plugin-api` workspace dependency, and identify the stable plugin id
your distribution composes. Declare one immutable `FrontendPlugin` that the
frontend composer can validate before creating the router and application
shell.

Contributions describe UI placement only. They do not create data, grant
access, or register a backend capability. Put authorization on the backend
action and use UI state only to avoid offering an action that cannot succeed.

## Declare one frontend plugin

Export one declaration from the package entry point. Keep the contribution
arrays close to their pages and components, then combine them in the entry
module as first-party plugins do:

```ts
import { defineFrontendPlugin } from '@atlas/plugin-api'
import { inventoryRoutes } from './routes'
import { inventoryNavItems } from './navItems'
import { inventoryTabs } from './entityDetailTabs'

export const inventoryPlugin = defineFrontendPlugin({
  id: 'atlas.inventory',
  contributions: [...inventoryRoutes, ...inventoryNavItems, ...inventoryTabs],
})
```

`defineFrontendPlugin()` and the builders below only declare contributions. Do
not mutate a shared registry, inspect the selected-plugin list, or perform
runtime registration when the module imports. The composed distribution is the
source of truth for which declarations are present.

## Add a route and navigation item

A route has a globally unique contribution id, a unique URL path, and a React
component. Routes are session-protected and rendered inside Atlas's navigation
shell by default. Set `public: true` only for a page that must deliberately
bypass both, such as the Core login page.

```ts
// routes.ts
import { route } from '@atlas/plugin-api'
import { InventoryPage } from './pages/InventoryPage'

export const inventoryRoutes = [
  route({
    id: 'atlas.inventory.items.list',
    path: '/inventory',
    component: InventoryPage,
  }),
]
```

Make a sidebar item point to a route id with `routeRef()`, rather than copying
the path. The reference is resolved during composition, so the route may be
declared in another module or appear later in the contribution array.

```ts
// navItems.ts
import { Cube } from '@gravity-ui/icons'
import { navItem, routeRef } from '@atlas/plugin-api'

export const inventoryNavItems = [
  navItem({
    id: 'atlas.inventory.nav.items',
    title: 'Inventory',
    icon: Cube,
    route: routeRef('atlas.inventory.items.list'),
  }),
]
```

Use an icon in the shape exported by `@gravity-ui/icons`. A navigation item
does not register a route and cannot target an unknown route id.

## Add an entity-detail tab

An entity-detail tab has a stable `value` for the tab selection, a reader
label, a predicate, and a component that receives the entity. The shell calls
`when(entity)` for the entity being viewed and renders only matching tabs.
Target a declared entity capability instead of a hard-coded kind id. Another
compatible kind can then participate without a frontend change.

```tsx
import { entityDetailTab, entitySupports } from '@atlas/plugin-api'
import { InventoryTab } from './InventoryTab'

export const inventoryTabs = [
  entityDetailTab({
    id: 'atlas.inventory.detail.stock',
    value: 'inventory-stock',
    label: 'Stock',
    when: entitySupports('inventory.subject.v1'),
    component: InventoryTab,
  }),
]
```

`fullWidth: true` is available for canvas-like or editor-like tab content that
must use the shell's full width; ordinary tabs retain the detail page's right
rail. A predicate controls applicability, not authorization. If a tab reads or
changes protected data, its backend endpoint still performs the permission
check. When the backend reports an entity as unavailable, Atlas does not show
kind-specific tabs.

## Add a home widget

Use a home widget for a small, independent item on the Atlas home page:

```tsx
import { homeWidget } from '@atlas/plugin-api'
import { InventorySummaryWidget } from './InventorySummaryWidget'

export const inventoryHomeWidgets = [
  homeWidget({
    id: 'atlas.inventory.home.summary',
    component: InventorySummaryWidget,
  }),
]
```

Widgets receive no contribution-specific configuration. Fetch only public API
data, render loading and failure states locally, and do not assume that another
optional plugin is selected. If the widget depends on another plugin's data,
give the backend a public contract and make its unavailable response renderable.

## Cardinality and ownership

Atlas currently exposes four frontend contribution types. Each is a
**collection** extension point: selected plugins may contribute many routes,
navigation items, entity-detail tabs, and home widgets. There are currently no
singleton or keyed frontend contribution types in `@atlas/plugin-api`.

| Type | Required fields | What composition validates |
| --- | --- | --- |
| `route` | `id`, `path`, `component` | global id and path uniqueness; non-Core plugins cannot use `/`, `/login`, or `/settings` |
| `navItem` | `id`, `title`, `route` | global id uniqueness and that its `routeRef` resolves to a selected route |
| `entityDetailTab` | `id`, `value`, `label`, `when`, `component` | global id uniqueness; `when` is evaluated by the detail shell |
| `homeWidget` | `id`, `component` | global id uniqueness |

The declaring plugin owns its id namespace. Use a durable, plugin-prefixed id
such as `atlas.inventory.detail.stock`; do not reuse ids to replace a Core or
sibling contribution. The current API does not provide an ordering,
disablement, replacement, or wrapping hook for another plugin's contribution.

## Verify composition and fix collisions

Frontend composition runs over every selected plugin before Atlas constructs
the router. It collects all detected violations and throws a
`CompositionError`, so a bad distribution does not partially render.

| Failure | Cause | Corrective action |
| --- | --- | --- |
| Duplicate contribution id | Two selected contributions use the same `id`, even when their types differ. | Rename one id inside its owner namespace. |
| Conflicting route path | Two routes claim the same `path`. | Assign a distinct plugin-owned path. |
| Core-reserved route | A non-Core plugin claims `/`, `/login`, or `/settings`. | Choose a non-reserved path; only `atlas.core` owns those paths. |
| Unresolved navigation route | A `navItem` refers to a route id absent from the selected contribution set. | Correct the `routeRef` id or include the route in the same selected distribution. |

Run the TypeScript composition tests after altering a declaration:

```shell
pnpm --dir core/frontend test -- ../../plugin-api/typescript/src/compose.test.ts
```

Then run the frontend's normal typecheck and test commands for the package you
changed. Distribution assembly and its preflight are documented in [Assembling
a distribution](../configuration/distributions.md); use that workflow when a
new plugin package must be selected.

## Common failures and next steps

- A tab never appears: confirm `when()` returns true for the entity payload's
  `capabilities`, and confirm the entity is not unavailable.
- A menu item is missing or composition fails: verify the exact route id passed
  to `routeRef()`, rather than only the URL path.
- A control is hidden or disabled but the API still rejects it: this is
  expected unless the principal has the required backend permission; follow
  [Permissions](../concepts/permissions.md) when adding the protected action.
- A widget fails because an optional service is absent: render an unavailable
  state and design the backend collaboration through the relevant
  public contract.

For a tab capability, read [Entity kinds and facets](entity-kinds-and-facets.md).
For a complete composed example, read [Build your first plugin](tutorial.md).
The [plugin contract reference](reference.md) lists the exact TypeScript types.
For backend capabilities, extension points, and direct contracts, see
[Backend collaboration](backend-collaboration.md).
