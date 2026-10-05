## Context

Atlas is composed from plugins selected in a distribution manifest. Backend plugins expose static descriptors and a `register_runtime()` hook; shared contracts live in `atlas_plugin_api` (for example authentication providers register through that package with an `owner` id); frontend plugins declare typed contributions with extension-point cardinalities (`collection`, `singleton`, `keyed`) validated before the router is built. Plugins may not import each other's implementations.

Searchable content is heterogeneous. Catalog entities carry `name`, `description` and a plain-text `documentation` field. Other plugins hold their own models, and **read permissions differ per plugin**: some gate reads explicitly, some allow any signed-in user. No shared read-permission layer exists, so the system cannot assume one.

There is no task queue; periodic work runs on the core scheduler (previous change). `transaction.on_commit` is not used anywhere yet. Per-kind list pages already filter with `icontains`; that stays.

The search UI should resemble a command-palette style dialog opened from a search box.

## Goals / Non-Goals

**Goals:**
- Optional: absent plugin means absent feature, with no code path in other plugins failing.
- No engine named in contract or core code; engines are separate plugins and the search plugin uses exactly one of the registered ones; a fork can swap the engine adapter or the whole search plugin.
- Plugins decide what is searchable and authorize their own results.
- Ranking and snippets that behave the same regardless of engine, with engines able to improve on them.
- Near-real-time freshness with self-healing.
- Zero new infrastructure for the default setup.

**Non-Goals:**
- Sources beyond catalog entities (next change), another engine, deep links, analytics.
- Incremental sync from audit trails or timestamps.
- Guaranteeing identical relevance across engines.

## Decisions

### Decision 1: Three independent seams

`SearchSource` (per data-owning plugin), `SearchEngine` (index storage and ranking), and the HTTP response contract with the UI plugin. Each can be replaced without touching the other two.

Alternatives considered:
- **One provider interface per plugin that both indexes and queries** (federated live search). Needs no index, but ranking across heterogeneous sources has no common score, unindexable substring matching runs on every keystroke, and highlighting needs bespoke code per source.
- **Hard-wire one engine behind a service layer.** Simple, but violates the requirement that the engine be replaceable and a fork be cheap.
- **Client-side index.** Cannot honor per-plugin read permissions and goes stale.

The three-seam design costs more contract surface but is the only one that satisfies swappable engines and per-plugin authorization together.

### Decision 2: Contract and registries live in the Python plugin API, not in the search plugin

`SearchSource`, `SearchEngine`, `SearchDocument`, `SearchHit` and registration functions (`register_search_source(source, owner=...)`, `register_search_engine(engine, owner=...)`) live in `atlas_plugin_api`, following the authentication-provider pattern. Registering with no consumer installed is harmless.

Alternatives: the search plugin owns the registries (the ingestion extension-point pattern) — then every source plugin would have to declare a dependency on search and search would stop being optional; a core-owned registry reached through `server.*` imports — forbidden by plugin boundaries.

### Decision 3: Document model is flat and self-describing

A `SearchDocument` has a stable string `id` of the form `<kind>:<key>`, a `kind`, a `title`, a `body` of plain text, an optional `summary`, and an opaque `route` hint used to build the link. The id alone must be enough for the source to re-load the live object.

Alternatives: nested per-field documents (engine features differ, more surface); storing the full hit payload in the index (stale data and a permission leak risk).

### Decision 4: Never trust the index for freshness or permissions

The engine returns candidate ids, scores and optionally highlights. The search plugin groups candidate ids by owning source and calls `source.resolve(ids, actor)`, which loads live objects and applies that plugin's own permission checks, returning nothing for inaccessible or deleted ids. Results are built only from resolve output. To keep pages full the plugin over-fetches candidates and stops when enough resolved hits are collected; total counts are therefore approximate.

Alternatives: a shared permission layer (does not exist and would not fit all plugins); permission data in the index (stale, large, engine-specific); post-filtering without over-fetch (short pages).

### Decision 5: Snippets are produced by core by default, engines may override

When an engine reports it provides highlights, the search plugin uses them; otherwise it builds a snippet from the resolved hit's text around the first match. Same UX on any engine, and engines with native highlighting can opt in through a capability flag.

Alternatives: require every engine to highlight (raises the bar for adapters); never use engine highlights (wastes native capability).

### Decision 6: Indexing is outbox plus periodic reconcile

A source declares the models it watches and how a changed instance maps to document ids. The search plugin connects model signals for registered sources and, on commit, records the affected `(source, document id, operation)` in a pending table in the same database transaction as the write, de-duplicated. A short-interval job drains pending rows, loads documents from the source for those ids, and upserts or deletes through the engine. A longer-interval job rebuilds the entire index from all sources and replaces it, repairing anything signals miss (queryset updates and bulk operations do not emit signals) and engine downtime.

Alternatives considered:
- **Synchronous call to the engine from the request.** Couples request latency and success to the engine; a down engine would block or lose writes.
- **Triggering a scheduler job from the writer.** With a persistent job store the scheduler process does not notice jobs added from another process until its next wakeup, so it is unreliable across processes.
- **Timestamp or audit-trail cursors.** Several sources have no timestamps, and timestamps do not report deletions.
- **Full rebuild only.** Simplest and correct, but freshness equals the rebuild interval.

The outbox is transactional, survives engine outages, handles deletions, and needs only one declaration per source. The reconcile job makes the design self-healing.

### Decision 7: The engine is chosen at startup from registered engines, optionally pinned by config

An engine adapter is its own plugin and registers its engine, with its plugin id as `owner`, in `register_runtime()`; disabled plugins do not register. At startup the search plugin chooses: no engines registered fails ("an engine plugin is required"); one engine is used, unless the optional `engine` setting names a different plugin, which fails; several engines use the one whose owner equals `engine`, or fail listing all of them when it is unset. The composer checks only an explicit `engine`: a selected, non-disabled plugin with that id must exist. No descriptor field marks a plugin as an engine, so the other errors surface at startup, before the process accepts traffic.

Alternatives: a descriptor flag or `provides` field (static check at build time, but a contract surface for a single plugin type); engine entry points (installed is not selected, and an adapter still has to be a selected plugin for its app and migrations); search in core with a manifest block (loses optionality and the swappable search plugin); engines as modules inside the search plugin (forks and out-of-tree adapters are harder, and the adapter's secrets and infrastructure cannot be scoped to it).

### Decision 8: Postgres engine stores a flat index table with a full-text vector

The adapter owns one table keyed by document id with `kind`, `title`, `body` and a generated full-text search vector with a GIN index; title matches outweigh body matches. It supports `replace_all` by a transactional swap and reports `snippets=False` initially so core builds snippets, keeping behaviour portable.

Alternatives: trigram-only matching (poor ranking, no stemming); using each source's own tables directly (reintroduces federation); a materialized view per source (hard to keep generic, tied to schema).

### Decision 9: Search UI is a single-occupant shell contribution

A new frontend contribution type occupies a singleton extension point rendered by the application shell. If no plugin contributes it the shell renders nothing extra. The search frontend plugin supplies the search box and dialog, which calls only the HTTP contract. A fork replaces the UI by contributing its own component.

Alternatives: a nav item that routes to a search page only (cannot give the dialog behaviour); core-owned search UI hard-wired in the shell (not optional); a generic slot system (more surface than one use needs).

### Decision 10: Catalog source lives with the catalog, not the search plugin

The catalog registers a source for entities in its own `register_runtime()`. The search plugin imports no catalog models. Each data owner keeps its searchable fields, watched models and permission logic next to its data.

### Decision 11: Default intervals, configurable, with a first-run rebuild

The drain job runs every 10 seconds and the rebuild job every 6 hours, both configurable in the search plugin's own configuration. When the engine's index is empty and sources hold documents (first enablement, engine switch, lost data), the rebuild runs once at scheduler start instead of waiting for its interval.

Alternatives: shorter drain interval (more idle queries for little gain); longer rebuild interval (bulk-operation drift lingers); no first-run rebuild (an operator who enables search sees empty results for up to six hours).

### Decision 12: The keyboard shortcut belongs to the search contribution

The search component registers and removes its own shortcut. Core has no shortcut registry.

Alternatives: a core shortcut registry (a new subsystem for one consumer, worth revisiting when a second plugin needs shortcuts); no shortcut (the dialog is much slower to reach).

### Decision 13: Document body size is capped in the contract

The contract bounds `body` to a maximum size (about 100 KB of text), truncated at a word boundary with a logged warning; a source may truncate earlier. The limit is configurable.

Alternatives: per-source caps (a forked source or adapter could index megabytes); no cap (huge SQL or documentation bloats the index and vectors).

### Decision 14: Scheduler-less deployments use a prebuilt index

The public demo runs as one small container with no scheduler; its catalog is seeded at image build time and reset on every restart. The rebuild is exposed as a management command that works without a scheduler, and the demo image runs it at build time right after seeding. Search works from the first request. Edits made while no scheduler runs stay in the pending table and are not searchable until the next restart; status reports the backlog and the UI may show a stale-index notice.

Alternatives: exclude search from the demo (the demo would not show the feature); run the scheduler as an extra process in the container (memory is tight on the free plan, to be measured separately); an inline drain mode for the request path (extra code and tests only for the demo, and contrary to keeping the engine out of the request path).

## Risks / Trade-offs

- **Demo edits are not searchable until restart** → accepted for the demo; status and the stale-index notice make it visible instead of silent; revisit with a memory measurement if it looks broken.
- **Image builds fail if new plugin sources are not copied** → explicit tasks for every image and for the demo build, and a check that a distribution not selecting search still builds.
- **A missing or ambiguous engine is detected at startup, not at build** → accepted; the process exits before serving traffic with a message naming the engines found, and an explicit `engine` is checked by the composer.

- **Pending table grows when the scheduler is down** → coalescing by document id bounds growth to the number of documents; the status endpoint exposes the oldest pending age so operators notice; the UI can show a stale-index notice.
- **Over-fetch makes totals approximate and pages occasionally short** → documented; acceptable at catalog scale.
- **Signals do not fire for bulk operations** → covered by reconcile; documented in the algorithm page.
- **Reconcile cost on large catalogs** → full rebuild is acceptable for expected sizes (thousands of documents); reconcile interval is configurable.
- **Contract surface is committed early** → internal 0.x contract package; two adapters will exercise it before stabilizing, which is why the second engine ships in the same release.
- **Postgres full-text language configuration** → one configurable text-search configuration with a sensible default; documented limits for non-default languages.
- **Authorization leaks through scores or counts** → results are built only from resolve output; counts are never derived from unresolved candidates.

## Migration Plan

1. Land the contract and registries in the plugin API with no consumer.
2. Add the search plugin, the Postgres engine plugin and the shell contribution, then register the catalog source.
3. Add the plugins to the default distribution manifest and lock; run migrations; the first reconcile builds the index.
4. Rollback: remove the plugins from the manifest. Tables remain unused; no data in existing tables changed.

