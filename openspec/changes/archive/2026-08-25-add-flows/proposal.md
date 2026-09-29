## Why

Teams can register Systems, Components, Resources, and APIs, but there's no way to document how those pieces cooperate over time to carry out a process (e.g. "checkout saga": place order → charge payment → on failure, refund; on success, ship). EventCatalog calls this a **Flow** — a narrated, ordered sequence of steps, each pointing at a real entity in the catalog, with branching for success/failure paths. Atlas has no equivalent, and the catalog's own C4-diagram machinery isn't a fit for it (that's a derived, auto-generated topology view of `dependsOn`/`providesAPI` relations — a Flow is hand-authored narrative content that happens to reference catalog entities, not a relation graph).

## What Changes

- Add a `Flow` model: belongs to exactly one home `System` (FK, required), holds a `steps` array (JSON) where each step has an id, title, markdown summary, an optional reference to a catalog entity (`component:name` / `resource:name` / etc., reusing the existing `kind:name` ref grammar), and a `next_step`/`next_steps` transition to other step ids.
- Steps form a **strict tree** in v1: a step id may be the target of at most one incoming transition (no branches rejoining a shared step). Enforced as a validation rule on save.
- Entity refs inside steps are validated against the catalog at save time (must resolve to a real entity) but are **not** stored as FK/M2M columns and do **not** feed the existing derived `Relation` table — Flows are deliberately outside the relations system.
- Add a `Flow` CRUD API (list/create/read/update/delete), filterable by `system` and by `system__owner` (team).
- Add a new **Flows** item to the left sidebar nav, a list page (search + System filter + Team filter, reusing the existing `FilterBar`), and a detail page.
- The detail page renders each flow as a left-to-right tree diagram, computed client-side from the `steps` JSON (no server-side rendering, no relation to the existing SVG diagram endpoint) using a new dependency, `@gravity-ui/graph`, plus a small hand-written tree-layout function (no layout library — the tree is guaranteed divergence-only). Editing is a raw JSON editor over `steps` with a live preview of the same rendering pipeline.

## Capabilities

### New Capabilities
- `flow-management`: `Flow` model, validation rules (entity-ref resolution, strict-tree transitions), CRUD API, sidebar nav entry, list page (search/System/Team filters), and detail page (JSON step editor + live left-to-right tree preview).

### Modified Capabilities
_None — Flows are additive and do not change the behavior of any existing capability (`entity-catalog`, `entity-relations`, `diagram-stub`, etc. are all unaffected)._

## Impact

- **Backend**: new `Flow` model + migration in `apps/catalog` (or a new app — see design.md), new serializer/viewset, new validation for step transitions and entity refs (reusing `apps/catalog/refs.py`).
- **Frontend**: new `FlowsListPage`, `FlowDetailPage`, a step-tree-layout utility, and a `@gravity-ui/graph`-based canvas component; one new npm dependency (`@gravity-ui/graph`); `AppShell.tsx` nav update.
- **No impact** on the C4 diagram pipeline, ingestion, or the derived `Relation` table.
