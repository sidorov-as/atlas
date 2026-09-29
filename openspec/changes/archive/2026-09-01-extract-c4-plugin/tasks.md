## 1. Entity capabilities

- [x] 1.1 Add `provides: list[str]` to `EntityKindHandler` registration; declare `architecture.subject.v1` for `system` and `component`, and `architecture.actor.v1` for `group` and `actor`.
- [x] 1.2 Serialize registered capabilities to the frontend bootstrap payload.
- [x] 1.3 Implement `entitySupports(capability)` for real against the served capability list.
- [x] 1.4 Run `entitySupports('architecture.subject.v1')`/`entitySupports('architecture.actor.v1')` alongside the existing hard-coded C4-tab/Person-rendering kind checks in a non-blocking assertion; confirm they agree before removing the old checks.

## 2. Scaffold and move backend

- [x] 2.1 Create `plugins/c4/backend/` declaring manifest dependencies on `atlas.standard-catalog` (required) and `atlas.apis` (optional).
- [x] 2.2 Move PlantUML rendering and diagram endpoints to `/api/plugins/atlas.c4/...`; update every frontend reference to the old `/api/diagrams/...` paths.
- [x] 2.2.1 Generalize the diagram builder's Person-rendering check from a hard-coded `kind in ('user', 'group')` test to `entitySupports('architecture.actor.v1')`.
- [x] 2.3 Move viewer-preference storage.
- [x] 2.4 Register the `atlas.c4.diagram.read` permission and a minimal `AlwaysAllowIfAuthenticated` policy evaluator; gate diagram endpoints on it.

## 3. Move frontend and add the widget

- [x] 3.1 Create `plugins/c4/frontend/`; move the C4 Diagram and System Architecture tab contributions, gated by `entitySupports('architecture.subject.v1')`.
- [x] 3.2 Move diagram viewer components (pan/zoom/settings/download) and viewer-preference UI.
- [x] 3.3 Add the home widget contribution rendering the System Landscape.

## 4. Verify

- [x] 4.1 Run `catalog-c4-diagrams`, `system-architecture-diagram`, and `c4-diagram-viewer-preferences` scenarios against the moved code.
- [x] 4.2 Compose a distribution without `atlas.c4`; verify no diagram endpoints, tabs, or widget appear, and Standard Catalog's own pages are unaffected.
- [x] 4.3 Remove the old in-core diagram endpoints, PlantUML packaging, and hard-coded kind checks.
