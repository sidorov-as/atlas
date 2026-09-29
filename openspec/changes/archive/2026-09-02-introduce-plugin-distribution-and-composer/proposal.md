## Why

Every change so far selects plugins via an internal Python list (`SELECTED_PLUGINS`, `installedFrontendPlugins`) that a developer edits directly in the monorepo. By this point there are six real plugins (Standard Catalog, APIs, C4, Database Schema, Ingestion, Auth-local, Auth-OIDC) plus Core plus two Plugin API contract packages — `plugin-architecture.md` requires this be assembled from a source-controlled deployment manifest and a resolved lock file, built by a composer that generates `INSTALLED_APPS` and the frontend's `installedFrontendPlugins` module, with no plugin registry service and nothing downloaded at container start (ADR 0002, 0007, 0009, 0021, 0024, 0025). This is also the point where the plugin/contract-package internal-vs-published-artifact distinction stops being simulated (workspace path deps) and needs the real monorepo/package/versioning shape, since six plugins is enough for the "everything in one giant Python list" approach to have become the actual bottleneck.

## What Changes

- Restructure the monorepo into `atlas/{core,plugin-api,plugins,distributions}` per `plugin-architecture.md:611-627`: `core/{backend,frontend}`, `plugin-api/{python,typescript}` (the `atlas-plugin-api-python`/`@atlas/plugin-api` contract packages, formalizing what changes 2-4 built ad hoc), `plugins/{standard-catalog,apis,c4,database-schema,ingestion,auth-local,auth-oidc}`, `distributions/default/`.
- Define the YAML deployment manifest schema (`distribution.id/version`, `core.version`, `plugins[].{id,version,backend.package/source,frontend.package/source}`, `auth.providers/default`, `ui.disable/order`) per `plugin-architecture.md:493-523`.
- Build the composer: resolves manifest → lock file (exact versions + hashes/integrity per `plugin-architecture.md:525-543`) → generates `INSTALLED_APPS` and the frontend `installedFrontendPlugins` module → runs composition validation (extending `introduce-plugin-registries`'s validator with the full list from `plugin-architecture.md:549-558`: mismatched backend/frontend identity or version, incompatible Core/Plugin API ranges, missing required plugins/capabilities/extension points, cyclic dependencies, duplicate ids, conflicting/reserved paths, invalid config, forbidden dependency edges).
- Add CI import-boundary enforcement (Python and TypeScript): plugin → plugin-api allowed; plugin → core internals forbidden; plugin → another plugin's implementation forbidden except via a declared contract package; generalizing the pairwise checks changes 5-10 each added ad hoc into one enforced rule.
- Add independent versioning: Core, Plugin API contracts, each Plugin Release, and the Default Distribution each get their own version number connected by compatibility ranges, replacing the implicit "everything in the monorepo is one version" state every prior change has been in.
- Add typed, namespaced plugin configuration with public/secret separation (`plugin-architecture.md:473-489`) — `atlas.auth.oidc`'s `clientSecret`/`issuer` config from change 10 becomes the first real consumer, moved off whatever ad hoc Django settings it used during that change.
- Build the default distribution (`distributions/default/`) as one particular manifest+lock selecting every first-party plugin from this program, built through the same composer an external operator would use — no longer a special hard-coded build.

## Capabilities

### New Capabilities
- `deployment-manifest-and-lock`: an operator declares plugin selection, versions, and artifact sources in a source-controlled YAML manifest; a composer resolves it to a lock file recording exact versions and integrity hashes; nothing is downloaded when a container starts; a reproducible build starts from manifest + lock alone.
- `composition-validation`: the composer rejects, before any deployment accepts traffic, mismatched backend/frontend plugin identity or version, incompatible Core/Plugin API ranges, missing required plugins/capabilities/extension points, cyclic dependencies, duplicate ids, conflicting or reserved route paths, invalid non-secret configuration, and forbidden package dependency edges.
- `plugin-configuration-isolation`: each plugin declares a typed, namespaced configuration schema; it receives only its own validated config object; secrets are resolved centrally and never appear in the manifest, lock, frontend bundle, or public bootstrap response.

## Impact

- **Repository structure**: full monorepo reorganization (`core/`, `plugin-api/`, `plugins/`, `distributions/default/`) — the single largest non-functional (no behavior change) diff in this whole program.
- **Backend/Frontend**: `SELECTED_PLUGINS`/`installedFrontendPlugins` (Python list / hand-edited module from changes 3-4) are replaced by composer-generated equivalents; every plugin from changes 5-10 gets a real `PluginDescriptor`/manifest entry with its own version.
- **CI**: new import-boundary checks, new composer-driven build step for the default distribution.
- **No product-behavior spec is modified** — every capability listed above is new infrastructure; the default distribution must still pass every existing spec-scenario suite end-to-end once composed.
- **Dependents**: `introduce-plugin-lifecycle-and-failure-isolation` builds disable/remove/purge on top of the manifest/lock this change establishes.
