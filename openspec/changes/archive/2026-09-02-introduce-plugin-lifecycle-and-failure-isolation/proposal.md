## Why

Every prior change in this program has treated "a plugin is installed and enabled" as the only state. Real operation needs the full lifecycle `plugin-architecture.md` specifies — `installed → active → disabled → removed → explicitly purged` — so an operator can, for example, deselect `atlas.database-schema` in next quarter's distribution without silently deleting every Resource's schema data, or safely run a rolling deployment across a plugin version bump (ADR 0008, 0019). It also needs the runtime failure-isolation model (ADR 0020) that every earlier change's error-boundary/typed-unavailable-response mentions assumed would eventually be formalized: a broken plugin contribution must degrade, not crash the whole app. This is deliberately the *last* change in the program because it's the one most naturally validated by exercising it against every plugin already built — removing `atlas.apis`, `atlas.c4`, and `atlas.database-schema` in turn and confirming each degrades correctly is a much stronger test than writing this mechanism against a hypothetical single plugin up front.

## What Changes

- Add the Catalog Entity **Unavailable Entity** state: when an entity's kind provider (`EntityKindHandler`) isn't currently registered, `EntityService`'s read paths return a generic, read-only representation (identity, relationships, common metadata) instead of erroring; write paths reject cleanly. Wire this into `entity-kind-registry`'s "unknown kind" lookup result from change 2.
- Add plugin lifecycle states (`installed`, `active`, `disabled`, `removed`) tracked per plugin in the manifest/composition state from change 11; `disabled` suppresses contributions while keeping code and data; `removed` (absent from a manifest) never triggers a reverse migration or data deletion.
- Add an explicit, separate `purge` operation: a destructive, plugin-code-still-installed operation that validates dependent-data scope before deleting a plugin's tables/rows — never triggered implicitly by removal.
- Formalize expand/contract migration discipline as an enforced (not just documented) constraint: a migration linter blocking destructive changes (dropped column/table, non-nullable-without-default addition) outside an explicit maintenance-mode override, applied to Core and every plugin.
- Add runtime failure isolation for every "was it different last time" list `plugin-architecture.md` calls out: confirm every frontend contribution already has an error boundary (change 4); add typed unavailable/error results to every capability call (`ApiOperationsV1`-shaped contracts from change 6/7); make every plugin-owned endpoint (spec facet CRUD, diagram rendering, ingestion) return a clean `503`-equivalent rather than crash on internal failure; add a health/diagnostics endpoint reporting per-plugin degraded status.
- Verification: deselect `atlas.apis` with existing API entities present and confirm they become Unavailable Entities with intact relationships; deselect `atlas.c4`/`atlas.database-schema` and confirm the same for their respective data; purge `atlas.database-schema` and confirm it actually deletes facet data (the one case removal must not).

## Capabilities

### New Capabilities
- `plugin-lifecycle`: a plugin moves through `installed → active → disabled → removed → explicitly purged`; disabling suppresses contributions without touching code or data; removal never reverses migrations or deletes data; purge is a separate explicit operation performed with the plugin's code still installed, validating scope before deleting.
- `unavailable-entity`: a Catalog Entity whose kind provider isn't currently active is read-only, retains its identity and relationships, and is represented generically rather than causing an error.
- `runtime-failure-isolation`: a failing frontend contribution, plugin endpoint, capability call, or background job is isolated to its own unit (error boundary, typed unavailable response, retry/dead-letter, `503`-equivalent) without crashing the application shell or unrelated requests; health diagnostics surface per-plugin degraded status.
- `expand-contract-migrations`: a plugin's (and Core's) migrations follow enforced expand/contract discipline across a rolling deployment; a destructive migration is blocked by a linter unless the deployment explicitly opts into maintenance mode.

## Impact

- **Backend**: `EntityService` read paths gain Unavailable Entity handling; composition state (from change 11's manifest/lock) gains lifecycle tracking; a migration linter runs in CI; a health/diagnostics endpoint is added.
- **Frontend**: confirm/extend error-boundary coverage from change 4 to every contribution type added by later changes (home widgets, C4 tabs, facet editors); add a generic "this section is unavailable" rendering for an Unavailable Entity's detail page.
- **Verification-heavy, low new-surface-area**: most of this change's work is proving guarantees against the six-plus plugins already built rather than adding large new subsystems — the exception is the migration linter and purge operation, which are genuinely new tooling.
- **Closes the program**: after this change, every architectural principle in `plugin-architecture.md` has a corresponding implemented, tested guarantee; no further change in this sequence is implied by the source documents.
