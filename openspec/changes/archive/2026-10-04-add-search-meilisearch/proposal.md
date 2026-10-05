## Why

The default search engine keeps the index in PostgreSQL, which is enough for modest catalogs but offers limited typo tolerance and relevance tuning. Operators with larger catalogs, or who want better matching, need a dedicated engine, and the engine contract is only proven when a second, genuinely different implementation passes the same tests. A dedicated engine also needs a separate service, which the distribution tooling cannot yet describe.

## What Changes

- A second engine adapter, shipped as its own optional plugin, that keeps the index in a Meilisearch instance. It is selected instead of the PostgreSQL adapter by naming it in the distribution manifest.
- It passes the same engine conformance suite as the PostgreSQL adapter and declares native highlighting and typo tolerance as capabilities.
- The distribution tooling learns that a plugin can require an external service: a plugin declares the service it needs, the composer records it in the lock, and generates the deployment inputs for it, or accepts an existing instance supplied by the operator.
- Connection settings and the access key are configured through the plugin's own namespaced configuration with secrets resolved centrally.
- Documentation for choosing and operating the engine, and for declaring required services.

Out of scope: running Meilisearch in the public demo deployment (the demo keeps the PostgreSQL adapter), multi-node or clustered engines, replacing the default engine, engine-specific search UI features, and migrating an existing index between engines (a rebuild recreates it).

## Capabilities

### New Capabilities
- `search-meilisearch-engine`: the adapter, its configuration, id handling, atomic replace, highlighting, typo tolerance and conformance.
- `deployment-required-services`: a plugin can declare an external service it requires, and the composer records it and generates deployment inputs or accepts an operator-provided instance.

### Modified Capabilities

## Impact

- New plugin package for the adapter; the default distribution manifest keeps the PostgreSQL adapter, with an example manifest showing the alternative.
- `composer`: new service declaration in plugin metadata, lock and generated deployment inputs.
- `docker-compose` and deployment documentation: an optional service definition used only when this plugin is selected.
- Documentation site: engine selection, operating the engine, declaring required services.
- Depends on the search core change.
