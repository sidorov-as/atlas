## Context

By the end of change 10, the repo has: `backend/server/apps/catalog` (core, shrunk by change 5), `backend/server/settings` (generates `INSTALLED_APPS` from `SELECTED_PLUGINS`, a Python list, since change 3), and six-plus plugin packages living under some ad hoc `plugins/` location each change created independently, all wired together with workspace/path dependencies and no real version numbers. `plugin-architecture.md`'s Repository and release model (lines 607-631) and Distribution and installation sections (491-559) specify the target: a real monorepo layout, a YAML manifest, a resolved lock file with integrity hashes, and a composer that's the *same* tool an external operator and this repo's own CI use to build the default distribution (ADR 0009, 0024, 0025).

## Goals / Non-Goals

**Goals:**
- The monorepo matches `plugin-architecture.md:611-627`'s layout exactly.
- A YAML manifest + generated lock file fully determines a build; nothing is fetched at container start.
- The composer performs every validation listed in `plugin-architecture.md:549-558`.
- Core, Plugin API, each Plugin Release, and the Default Distribution are independently versioned.
- CI enforces the import-boundary rules for both Python and TypeScript.
- The default distribution, built through the composer, passes every existing spec-scenario suite unchanged.

**Non-Goals:**
- A plugin marketplace, registry service, or any network call during artifact resolution beyond standard PyPI/npm package installation (ADR 0009's explicit non-goal, restated).
- Publishing any plugin to a *public* registry — private/internal registries or workspace-local artifacts are sufficient; "use standard artifact registries" doesn't require *this* program to actually publish publicly.
- Runtime plugin installation from a UI — explicitly out of scope for the whole program (`plugin-architecture.md`'s top-level Non-goals), restated here since the manifest/composer machinery might tempt someone to bolt on a "click to install" UI; don't.
- Stabilizing the Plugin API to `1.0` — it stays `0.x`/internal per ADR 0021; this change gives the contract packages a real home and real (still-internal) versioning, not a stability promise.

## Decisions

**The composer is a Python CLI tool**, invoked identically by CI building the default distribution and by a hypothetical external operator building their own. Python is a decided choice, not a placeholder: the composer needs to read Python package (wheel) metadata natively, generate Django settings, and integrate cleanly with `uv`/`pip`'s own dependency-resolution tooling — reaching for a different language would mean re-implementing or shelling out to Python tooling anyway for the backend half of every resolution. This is the literal architectural claim in `plugin-architecture.md:65`: "the official default distribution is one particular manifest and lock, not a special hard-coded build." Any composer logic that only runs for "this repo's own build" (as opposed to any manifest+lock pair) is a design smell to catch in review.

**Lock file resolution reuses each ecosystem's native lock mechanism where possible (`pip`/`uv` for Python, the frontend's existing package manager lockfile for npm) rather than inventing a third custom lock format from scratch.** The Atlas-level lock file (`plugin-architecture.md:529-543`) records the *logical* plugin→artifact→version→hash mapping; it can be a thin layer recording which native lock entries correspond to which logical plugin, rather than re-deriving hashes independently.

**Composition validation is layered on top of `introduce-plugin-registries`'s existing runtime validator (duplicate id, missing required dependency), adding purely static (pre-`django.setup()`, pre-frontend-build) checks: manifest/lock consistency, backend/frontend identity+version match, Core/Plugin API compatibility ranges, cyclic dependency detection, reserved-path/duplicate-route detection (extending change 4's frontend-only version to also see the full manifest-declared plugin set).** Static checks run first (fail fast, no need to even attempt `django.setup()` or a frontend build on a manifest that's already invalid); the existing runtime registry validator remains the last line of defense for anything only detectable once code actually runs.

**Plugin configuration schemas are Pydantic models (backend) / a matching TypeScript type (frontend, for the declared public projection only), validated by the composer against the manifest's `plugins[].config` block before any deployment starts, with `secret.fromEnv`-style references resolved by a central secret-resolution step that never writes the resolved value back into the lock file or any artifact the frontend bundle includes.** Matches `plugin-architecture.md:474-489` exactly; `atlas.auth.oidc`'s `clientSecret`/`issuer` config becomes this mechanism's first real, already-built consumer, migrated off whatever ad hoc settings it used when change 10 landed (before this change existed).

**Independent versioning uses semver ranges for compatibility (`atlasCore: ">=3.1 <4"`, `pluginApi: ">=0.8 <0.9"`) recorded in each plugin's static descriptor**, exactly as illustrated in `plugin-architecture.md:244-246`. The Default Distribution's own version (`2026.08`-style, calendar-ish per the illustrative example) is independent of Core's semver — the composer must not conflate "distribution version" with "core version" anywhere in its output.

## Risks / Trade-offs

- [Monorepo restructuring touches every file's import path across the whole codebase built so far] → This is the single riskiest change in the program purely by diff size; do it as a mechanical move (update import paths, no logic changes) verified by the full test suite passing identically before and after, kept as its own isolated step before any manifest/composer logic is added.
- [Building a composer is itself a non-trivial piece of software with its own bugs, and it's now load-bearing for every future deployment] → Give the composer its own test suite: unit tests for each validation rule (one synthetic-manifest fixture per failure mode listed in `plugin-architecture.md:549-558`), plus an end-to-end test building the default distribution's manifest+lock and asserting the generated `INSTALLED_APPS`/frontend module match expectations.
- [Six-plus plugins each independently versioned is a much larger compatibility-matrix surface than "everything moves together," which is what every prior change in this program has implicitly assumed] → Start every plugin at `0.1.0` with permissive compatibility ranges (`>=0.1 <1`) against Core's current version, tightening ranges only once a real breaking change forces the question — don't over-engineer version discipline before there's a second Core release to be compatible or incompatible with.
- [Secret-handling logic is security-sensitive and easy to get subtly wrong (a secret leaking into a log, the lock file, or a public bootstrap response)] → Add an explicit test asserting no configured secret value appears anywhere in the generated lock file, frontend bundle, or public config-projection response, exercised against `atlas.auth.oidc`'s `clientSecret` as the concrete case.

## Migration Plan

1. Move the repository into the `core/`, `plugin-api/`, `plugins/`, `distributions/default/` layout as a mechanical import-path-preserving restructuring; verify the full test suite passes identically before touching any manifest/composer logic.
2. Define the manifest and lock schemas; build the composer's resolution step (manifest → lock) without yet wiring it into the actual build.
3. Build the composer's generation step (lock → `INSTALLED_APPS` + frontend `installedFrontendPlugins` module); replace `SELECTED_PLUGINS`/the hand-edited frontend module with composer output for the default distribution.
4. Add the full composition-validation rule set with per-rule test fixtures.
5. Add plugin configuration schemas + secret resolution; migrate `atlas.auth.oidc` onto it.
6. Add CI import-boundary enforcement for Python and TypeScript across all plugins.
7. Build `distributions/default/` as a real manifest+lock; verify it builds via the composer and the resulting backend/frontend pass every existing spec-scenario suite end-to-end.
8. Rollback: step 1 (the monorepo move) should be validated exhaustively before any subsequent step lands, since reverting it after steps 2-7 have built on the new layout would be far more disruptive than reverting it alone.

## Resolved

- **Composer implementation language**: Python — decided (see Decisions above), resolving the corresponding item in `plugin-architecture.md`'s "Open implementation details."
- **Lock file storage**: checked into git per-distribution, alongside the manifest — matches "source-controlled configuration and a lock file" from the program's own Goals, and keeps `distributions/default/`'s lock reviewable in the same PR as a version bump, rather than needing a separate CI-artifact-inspection step to see what actually changed.
