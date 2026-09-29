## Context

`frontend/src/App.tsx` is a literal `<Routes>` tree with 20+ hard-coded `<Route>` elements. `frontend/src/components/AppShell.tsx` has a literal `NAV_ITEMS` array. `frontend/src/components/EntityDetailPage.tsx` is already a shared chrome component — it takes `tabs: DetailTab[]`, `railFields`, `links`, and renders header/tabs/rail — but its tab list is assembled by each `*DetailPage.tsx` caller inline (e.g. `SystemDetailPage.tsx` builds its own `DetailTab[]` array including a C4 tab), not contributed by anything a plugin could add to externally. This is exactly the gap `plugin-architecture.md`'s React architecture section (lines 332-380) describes: build-time-imported, declaratively-contributed routes/tabs/widgets around a canonical shell (ADR 0003, 0005, 0010, 0011, 0022).

This change proves the mechanism with a single in-tree "core" plugin module that wraps every existing page — it does not yet split System/Component/Resource/API/C4/Flows into separately built packages. That's `extract-standard-catalog-plugin` and later changes, which become real multi-plugin consumers of the contract this change establishes.

## Goals / Non-Goals

**Goals:**
- Plugin modules export an immutable contribution list; nothing mutates a global registry as an import side effect (ADR 0005).
- The host validates the full contribution set (id uniqueness, path conflicts, resolved `routeRef`s, core-reserved paths) before constructing the router.
- `EntityDetailShell` (built from `EntityDetailPage.tsx`) renders tabs/actions/banners from contributions, each in its own error boundary (ADR 0022, 0020 partially).
- Every current `catalog-web-ui` scenario keeps passing unchanged.

**Non-Goals:**
- Splitting frontend code into separately versioned npm packages — one workspace module, `@atlas/core-plugin` (or similar), holds every contribution in this change.
- Entity capabilities (`entitySupports('architecture.subject.v1')`) actually gating anything — `entitySupports()` is added as a typed helper now (so `extract-c4-plugin` doesn't have to invent it later) but this change's own contributions still use kind predicates, since no cross-kind capability exists yet.
- Multiple plugins' contributions being validated against each other for real conflicts — with one contributing module, conflict detection is exercised by unit tests seeding synthetic conflicting fixtures, not by real multi-plugin composition (that starts at `extract-apis-plugin`, the first change with two contributing modules).

## Decisions

**Contribution builders (`route`, `navItem`, `entityDetailTab`, `homeWidget`) are plain functions returning immutable data objects, not classes or hooks.** They're evaluated at module-import time as part of building the `contributions: [...]` array passed to `defineFrontendPlugin`, matching the example in `plugin-architecture.md:278-299`. No builder call is allowed to have a side effect (e.g. touching `window`, mutating a registry) — enforced by keeping them pure data constructors; validation and side-effecting registration both happen later, host-side.

**`routeRef(id)` is a lazy reference resolved only at validation time, not at contribution-declaration time.** This lets `navItem({ route: routeRef('atlas.apis.list') })` be declared before or after the route it points to is declared, and across module boundaries once multiple packages exist — matching `plugin-architecture.md:353-361`. Validation fails with an explicit "unresolved route reference" error, distinct from a generic crash.

**`EntityDetailShell` owns loading/unavailable/error/permission states; `entityDetailTab` contributions only provide their tab's `value`/`label`/`content`/`fullWidth`.** This is a rename/generalization of the existing `DetailTab` interface in `EntityDetailPage.tsx` — kept field-compatible so the existing per-kind tab components (`RelationsTab`, `DiagramTab`, etc.) don't need to change, only how their `DetailTab[]` array gets assembled (from static per-page code to resolved contributions).

**Each contribution's rendered output is wrapped in a local `ErrorBoundary` at the point the shell/router renders it, not by the contributing plugin itself.** Matches `plugin-architecture.md:380`/ADR 0020's "isolate runtime errors" principle — a plugin author shouldn't have to remember to add a boundary; the host guarantees it.

**The single "core" contributing module in this change lives at `frontend/src/plugins/core/index.ts`** (workspace-internal, not yet a separately published npm package), exporting one `defineFrontendPlugin({ id: 'atlas.core', contributions: [...] })` covering every existing route, nav item, and detail tab. Naming it distinctly from "the app" now avoids a rename churn when `extract-standard-catalog-plugin` peels System/Component/Resource/Team's contributions out of it into their own module.

## Risks / Trade-offs

- [Rewriting `App.tsx`'s route list and every `*DetailPage.tsx`'s tab assembly at once is a large, easy-to-regress diff] → Do it form-by-form: first make `App.tsx` route generation contribution-driven while every route still points at the exact same page components (no tab changes), verify, then convert one detail page's tabs to contributions at a time, running that kind's `catalog-web-ui` scenarios after each.
- [Validation logic itself needs test coverage before any real second plugin exists to exercise conflicts] → Add a dedicated `frontend-plugin-contributions` unit-test suite with synthetic fixture plugins (duplicate id, path conflict, unresolved `routeRef`, reserved core path) exercising the validator directly, independent of the real "core" module.
- [`EntityDetailShell`'s error-boundary wrapping could hide a tab's error in production while looking broken/blank] → Boundary fallback must render a visible, distinct "this section failed to load" state per tab/widget, not a blank div, so a failure is diagnosable from the UI alone.

## Migration Plan

1. Add the contribution-builder package, `defineFrontendPlugin`, and the validator with unit tests against synthetic fixtures only. No change to `App.tsx` yet.
2. Wrap every existing route as a `route(...)` contribution in `frontend/src/plugins/core/index.ts`; convert `App.tsx` to generate `<Routes>` from `installedFrontendPlugins = [corePlugin]`, keeping the exact same paths/components. Verify full frontend test suite + manual smoke test of every route.
3. Convert `AppShell.tsx`'s `NAV_ITEMS` into `navItem` contributions resolved via `routeRef`; verify sidebar behavior unchanged.
4. Build `EntityDetailShell` from `EntityDetailPage.tsx`, add tab/action/banner contribution rendering with error boundaries; convert one kind's detail page (start with Resource, the simplest: Overview + Relations only) to `entityDetailTab` contributions; verify against `catalog-web-ui` Resource scenarios.
5. Repeat step 4 for Component, System, API, Team, checking each kind's existing `catalog-web-ui` scenarios (including C4 tab full-width behavior, API Specification tab, Team's five tabs) after conversion.
6. Rollback: each step is a swap of "how a page is assembled" behind the same rendered output; revertible independently per step since no data or API shape changes.

## Open Questions

- Should `homeWidget` contributions exist yet if `HomePage.tsx`'s current content isn't itself pluggable content (no widget today, per the repo's `pages` list)? This change adds the typed `homeWidget()` builder and an empty `collection` extension point on `HomePage` so `extract-c4-plugin`'s landscape widget has somewhere to land, without back-filling any widget content now.
