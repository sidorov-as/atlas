# Assembling a distribution

## Prerequisites and outcome

You need a source-controlled manifest, the repository checkout that resolves
workspace artifacts, and a private runtime environment for secrets. Atlas
validates the lock, generates backend and frontend composition inputs, and
builds an immutable image. Plugin selection is fixed at build time.

Beyond environment variables, an operator also chooses *which plugins* are part of an Atlas
installation. That choice is a Distribution: a versioned, reproducible selection of core, the
Plugin API, and specific Plugin Releases that is built and deployed as one Atlas installation.
Atlas ships its official default distribution this way. A manifest and lock
define the build.

## The deployment manifest

An operator names plugin artifacts explicitly, from standard Python and npm registries (or, for
Atlas's own monorepo build, from its own workspace packages):

```yaml
distribution:
  id: company.atlas
  version: 2026.08

core:
  version: 3.2.0

plugins:
  - id: atlas.standard-catalog
    version: 2.3.1
    backend:
      package: atlas-plugin-standard-catalog
      source: python-private
    frontend:
      package: "@atlas/plugin-standard-catalog"
      source: npm-private

  - id: atlas.apis
    version: 1.4.2
    backend:
      package: atlas-plugin-apis
      source: python-private
    frontend:
      package: "@atlas/plugin-apis"
      source: npm-private

auth:
  providers:
    - id: atlas.auth.local
      signup: disabled
      principalProvisioning: preprovisioned
      actorProvisioning: manual
  default: atlas.auth.local
```

Plugins are not installed from a marketplace at runtime. The manifest is a
source-controlled file, and composition happens at build time before Atlas
starts. The current resolver implements `workspace` sources for this monorepo.
Schema-accepted registry source names do not mean this checkout can resolve them.
Authentication selection is part of the same manifest. Provider entries carry
Core-owned provisioning and reconciliation policy. Connection settings and
secret references remain in the owning plugin's namespaced `config`.

## The distribution lock

A composer tool resolves a manifest's declared artifacts to exact versions and integrity hashes:

```yaml
distribution: company.atlas@2026.08
core: 3.2.0

plugins:
  atlas.apis@1.4.2:
    backend:
      package: atlas-plugin-apis
      version: 1.4.2
      hash: sha256:example
    frontend:
      package: "@atlas/plugin-apis"
      version: 1.4.2
      integrity: sha512-example
```

Containers do not download anything when they start. The manifest and lock are
inputs to a reproducible backend and frontend image build. The same composer
builds Atlas's official distribution for CI.

## Assemble and verify

1. Add, remove, or configure plugin entries in your manifest. A plugin can be
   backend-only or frontend-only, but it must declare at least one artifact.
2. Put a secret in an environment variable and use a `fromEnv` reference in
   plugin configuration; do not write a literal secret to the manifest or lock.
3. Resolve and validate the manifest before generating or building:

   ```shell
   uv run --project composer atlas-compose resolve distributions/default/manifest.yaml -o distributions/default/lock.yaml
   uv run --project composer atlas-compose validate distributions/default/manifest.yaml distributions/default/lock.yaml
   ```

4. Generate composition modules only from the validated lock. Do not edit the
   checked-in generated modules by hand. Build and start the supported
   topology, then verify `/healthz/plugins/` reports expected plugin states.
5. Verify `/healthz/auth/providers/`, the public login configuration, closed
   signup, one protected API call, one denied action, and logout.

See [composition errors](../operating-atlas/composition-errors.md) for each
preflight failure and [plugin lifecycle](../operating-atlas/plugin-lifecycle.md)
to distinguish disablement, removal, reinstallation, and retained data.

## What gets rejected before it ships

The build preflight rejects a manifest/lock pair with:

- mismatched backend/frontend plugin identities or versions;
- an incompatible core or Plugin API version range;
- a missing required plugin, capability, or extension point;
- a cyclic plugin dependency graph;
- a duplicate Entity Kind, Facet, permission, contribution, capability, or route id;
- a conflicting or reserved route path;
- invalid non-secret configuration;
- an empty, duplicate, missing, incompatible, or wrongly defaulted
  authentication provider selection;
- a provider flow/policy mismatch or invalid finite lifetime; or
- a forbidden package dependency edge.

## Atlas's own default distribution

Atlas's default distribution selects every first-party plugin. Standard Catalog
is required; APIs, C4, Database Schema, and Ingestion are optional. The
distribution resolves against the monorepo's packages, not a published registry:

```yaml
distribution:
  id: atlas.default
  version: "2026.09"

core:
  version: 0.1.0

plugins:
  - id: atlas.standard-catalog
    version: 0.1.0
    backend: { package: atlas-plugin-standard-catalog, source: workspace }
    frontend: { package: "@atlas/plugin-standard-catalog", source: workspace }
  # ...atlas.apis, atlas.c4, atlas.database-schema, atlas.ingestion, same shape
```

Removing an optional plugin from a manifest and rebuilding does not reverse its
migrations or delete its data. Entities it previously owned become read-only
Unavailable Entities, preserving their identity and relationships. A later
distribution can reinstall the same plugin against that data.

The official distribution explicitly selects `atlas.auth.local`, keeps signup
closed, and uses conservative preprovisioned/manual policy. Provider installation
alone never enables login. Use the [authentication selection guide](../operating-atlas/authentication.md)
before changing the default or adding fallback.
