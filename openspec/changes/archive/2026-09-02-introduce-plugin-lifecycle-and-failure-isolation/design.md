## Context

Changes 1-11 built identity, lifecycle service, registries, contribution contract, six-plus plugins, and the manifest/composer — but every one of them implicitly assumed "the plugin set for this build is fixed and everything in it works." `plugin-architecture.md`'s Migration and lifecycle section (560-591) and Failure model section (593-605) describe what has to be true across *changes* to that set and *degradation* within a running deployment. ADR 0008 ("preserve-plugin-data-on-removal") and ADR 0020 ("fail-composition-and-isolate-runtime-errors") are the corresponding decisions. This change is where those promises, referenced but deferred throughout the program (e.g. `extract-apis-plugin`'s design.md explicitly says "this is exactly the Unavailable Entity scenario `introduce-plugin-lifecycle-and-failure-isolation` formalizes... until that change lands, treat [it] as unsupported"), get built and tested for real.

## Goals / Non-Goals

**Goals:**
- Unavailable Entity behavior works for a real removed/disabled kind provider, verified against `atlas.apis` specifically (change 6 built the exact scenario this needs).
- Plugin `disable`/`remove`/`purge` are distinct, correctly-scoped operations; removal never reverses migrations or deletes data; purge does, after explicit confirmation.
- Every contribution type from changes 4, 7, 8 (tabs, widgets, facet editors) has error-boundary coverage; every plugin-owned endpoint (change 6, 7, 8, 9) returns a clean degraded response on internal failure rather than crashing.
- A migration linter blocks destructive Core/plugin migrations outside maintenance mode.
- A health/diagnostics endpoint reports per-plugin degraded status.

**Non-Goals:**
- Building a UI for an operator to trigger disable/remove/purge — these remain deployment-manifest/CLI operations (purge explicitly "a separate explicit operation," not a button), consistent with the whole program's no-runtime-plugin-management principle.
- Automatic data migration or cleanup heuristics when a plugin is removed — the system's job is to *not delete* and to represent gracefully, not to guess what an operator wants done with orphaned data. That's an operator decision, executed via purge when they make it.
- Retrofitting every plugin built in changes 5-10 with new functionality — this change only adds the lifecycle/failure-isolation *guarantees* around what already exists, verified by exercising it, not by adding product features to those plugins.

## Decisions

**Unavailable Entity is not a new model — it's a read-mode `EntityService` falls into when `EntityKindRegistry.resolve(kind)` returns "not found" (the typed result from change 2) for an existing `CatalogEntity` row.** The `CatalogEntity` row and its relations were never deleted (the kind's `*Details` row and migrations remain present per ADR 0008 unless purged); only the *handler* is absent. `EntityService.get`/`list` detect this and return the entity's core envelope (identity, common metadata, relations) with `spec: null` and an `unavailable: true` flag, rather than attempting to call a nonexistent handler's `serialize_details`.

**"Disabled" is a manifest/composition-time state (a plugin selected but flagged inactive), distinct from "removed" (a plugin simply absent from the manifest).** `plugin-architecture.md:582` lists both as separate lifecycle stages; disabled keeps the plugin's code loaded (so, e.g., its migrations still apply, its data stays queryable by direct admin access) but its contributions/registrations don't activate — useful for a maintenance-mode kill switch without a full redeploy-without-the-package. Implemented as a `disabled: true` flag per plugin entry in the manifest, checked at the same "load selected runtime entry points" phase from change 3, skipping registration for disabled plugins while still installing their Django app (so migrations run).

**`purge` is a management command (`manage.py purge_plugin <plugin_id>`), not an API endpoint or anything reachable without direct operator access to the running deployment.** It: (1) requires the plugin's code to still be installed (can't purge a plugin whose migrations/models are already gone — matches `plugin-architecture.md:589`), (2) reports the exact scope (row counts per table) before deleting, (3) requires explicit confirmation, (4) runs inside a transaction so a failure mid-purge doesn't leave partial deletion.

**The migration linter runs as a CI check parsing each new migration's operations**, flagging `RemoveField`, `DeleteModel`, `AlterField` narrowing nullability, and any operation Django's own `--check` flags as non-elidable-in-a-rolling-deploy, unless the PR is tagged as an explicit maintenance-mode migration (a marker the linter recognizes and allows through with a required justification comment). This is deliberately a lint, not a hard database-level block — a real maintenance-mode upgrade must still be possible, just never accidental.

**Capability-call unavailability (`ApiOperationsV1`-shaped contracts) returns a typed `CapabilityResult[T] = Ok(T) | Unavailable | Error(reason)` rather than raising, or returning `None`**, so a consumer can't accidentally treat "the capability's plugin isn't installed" the same as "the capability call succeeded with an empty result" — a real distinction `extract-apis-plugin`'s "providesApis is inert without the APIs plugin" requirement already needs but didn't have a formal typed shape for until now.

## Risks / Trade-offs

- [Retrofitting Unavailable Entity handling into `EntityService`'s read paths, built in change 2 long before this concept existed, risks subtly changing normal (kind-present) read behavior] → Add the "not found" branch as a clearly separate code path (early return before the normal handler-invoking path), with a dedicated test suite exercising both branches from the same `EntityService.get` call, not a shared code path with conditionals threaded through the normal case.
- [Verifying against six-plus real plugins built over ten prior changes means this change's test matrix is large] → Prioritize `atlas.apis` (Unavailable Entity, since Component's `providesApis` already anticipated this) and `atlas.database-schema` (purge, since a facet's independent lifecycle is exactly what purge needs to prove) as the two required verification targets; treat `atlas.c4`/`atlas.ingestion`/auth-provider removal as secondary spot-checks rather than requiring the same depth of testing for all six.
- [A migration linter that's too strict blocks legitimate migrations; too loose defeats the purpose] → Start with the narrow, unambiguous destructive-operation list above (drop column/table, narrow nullability) rather than a broader heuristic; expand the linter's rule set only in response to a real incident it should have caught, not preemptively.
- [Purge is genuinely destructive tooling built once and rarely exercised, which is exactly the kind of code path most likely to have an undiscovered bug when finally used in anger] → Require a dry-run mode (`--dry-run` reporting scope without deleting) as the default, with actual deletion requiring an explicit `--confirm` flag, and test purge against a plugin with real cross-referenced data (`atlas.database-schema`'s facets, which reference `CatalogEntity` directly) as the acceptance case, not a synthetic empty-plugin fixture.

## Migration Plan

1. Add the `CapabilityResult[T]` typed-result shape; retrofit `extract-apis-plugin`'s `providesApis`/`consumesApis` resolution and any other existing capability-shaped call site to use it.
2. Add Unavailable Entity handling to `EntityService.get`/`list`; add the generic frontend "unavailable entity" detail-page rendering; verify by deselecting `atlas.apis` with existing API entities present and confirming they degrade correctly with relationships intact.
3. Add the `disabled` manifest flag and wire it into the runtime-entry-point-loading phase; verify a disabled plugin's migrations still apply but its contributions don't register.
4. Build the `purge_plugin` management command with dry-run/confirm modes; verify against `atlas.database-schema` (purge deletes facet data; the Resource itself is unaffected).
5. Add the migration linter to CI; verify it blocks a synthetic destructive migration and allows an explicitly-marked maintenance-mode one.
6. Audit every contribution type (change 4's tabs/nav/routes, change 7's home widget, change 8's facet editor) for error-boundary coverage; add a health/diagnostics endpoint reporting per-plugin status.
7. Full-program verification pass: deselect each of `atlas.apis`, `atlas.c4`, `atlas.database-schema`, `atlas.ingestion` in turn against the composed default distribution and confirm each degrades per its own change's documented expectations.
8. Rollback: each mechanism (Unavailable Entity, disable, purge, linter, error boundaries) is additive and independently revertible; none changes existing normal-operation behavior when every plugin is present and active, which is the state every prior change's spec-scenario suite already verifies.

## Resolved

- **Do disabled plugins' background jobs keep running?**: no, they pause. Both of this program's periodic-job plugins (`atlas.ingestion`'s discovery loop, `atlas.apis`'s spec refresh) are scheduled via `django-apscheduler`, whose `pause_job`/`resume_job` API maps directly onto the disable/re-enable transition — the "disabled" step in the runtime-entry-point-loading phase (task 3.1) calls `pause_job` for every job id the plugin registered, and reselecting/re-enabling calls `resume_job`. This is a mechanical consequence of the apscheduler decision, not separate new logic: disabled means "not contributing," and a background job silently writing data nobody can see or act on would be a surprising exception to that.
