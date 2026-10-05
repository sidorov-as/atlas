## Context

The search core change introduces a source contract: each data-owning plugin registers a source that declares its document kinds, the models it watches, a mapping from a changed instance to document ids, document production (for ids or for everything), and a `resolve` that loads live objects and applies that plugin's read rules.

Three plugins hold the content to add:

- **Flows**: their own model with name, description, documentation and a JSON list of steps whose text may live in several keys. The model is stored under an existing catalog app label, so its migrations belong to that app's history. Flows belong to a system; reads are not gated beyond being signed in.
- **APIs**: endpoints and operations with their own models, summaries, operation ids, status (active or removed) and timestamps; reads are gated by explicit endpoint read permission.
- **Database schema**: a one-to-one facet on a catalog entity with raw SQL and a parsed JSON structure whose shape is internal and provisional, plus a parse status.

Flows and the facet have no timestamps. Search does not need them (indexing is driven by tracked changes plus a periodic rebuild), but audit and history in the admin do.

## Goals / Non-Goals

**Goals:**
- Make these three content types findable with the same dialog and API as entities.
- Keep each plugin's permission logic inside the plugin.
- Isolate flattening of JSON content into text in one small function per source so a shape change breaks one test, not search.
- Add audit timestamps with a safe migration.

**Non-Goals:**
- Deep links to steps, tables or columns.
- Indexing raw specifications.
- Using timestamps as an indexing cursor.
- Changes to the contract, engines or UI.

## Decisions

### Decision 1: One source per plugin, kinds per content type

Flows register one kind; APIs register two (endpoint and operation) from one source object; the schema plugin registers one. Document ids follow `<kind>:<key>`, using the model's stable key (UUID for endpoints and operations, primary key for flows, owning entity id for schemas).

Alternatives: a single generic "model-driven" source configured by field lists (cannot express per-plugin permission or JSON flattening, so each plugin would still need custom code); separate sources for endpoints and operations (two registrations for shared permission logic).

### Decision 2: Flatten JSON content into body text, whole-entity hits

Step text (title, summary, external label) and schema table and column names are flattened into the body. Hits link to the whole flow or schema view.

Alternatives considered: anchors to a step or table (requires stable anchors in the viewers and a richer document model; deferred); indexing serialized JSON (matches keys and syntax noise, bad snippets); indexing only top-level fields (misses the content users most often remember, such as node labels).

### Decision 3: Schema documents are keyed to the owning resource

The schema document id derives from the owning entity, its title is the owning resource's name, and its link goes to that resource's schema view. Because the title comes from another model, the source also watches the catalog entity and maps an entity change to its schema document if one exists.

Alternatives: title from a static string such as "Database schema" (every result looks identical in the dialog); no title, body only (poor ranking and display).

### Decision 4: Prefer parsed structure, degrade on failure

Table and column names come from the parsed structure when parsing succeeded. When parsing failed, the document keeps only its title and indexing carries on. Parsing the raw SQL again inside the source is avoided.

Alternatives: always tokenize raw SQL (fragile across dialects, indexes keywords and noise); skip failed schemas entirely (a schema would vanish from search for a formatting error).

### Decision 5: Authorization stays in each plugin

Each source's `resolve` calls that plugin's existing checks: endpoint and operation read permission for APIs, flow read rules plus owning-system access for flows, owning-resource access plus facet rules for schemas. No new permission model is introduced and none is shared.

### Decision 6: Live data for display, index only for matching

Hits display the owning API's name, the flow's system and similar context from live objects at resolve time. The index holds only text needed for matching, so renames of a parent do not require reindexing children (except where the parent's name is the document's own title, as for schemas).

### Decision 7: Audit timestamps are plain model fields

`created_at` with `auto_now_add` and `updated_at` with `auto_now`, shown read-only in the admin. The migration adds the columns with a default of the migration time for existing rows, then makes them non-null.

Alternatives: a separate history table (heavier, not requested); only `updated_at` (loses creation time for the audit view); making search depend on them (rejected; bulk operations bypass `auto_now`, so they cannot be trusted as a sync cursor).

## Risks / Trade-offs

- **Schema JSON shape is provisional** → flattening is isolated and covered by a test that fails loudly when the shape changes; failed or unexpected shapes degrade to title-only.
- **Admin timestamps can lag after bulk updates** (they do not set `auto_now`) → documented; not used for search correctness.
- **Existing rows get the migration time as creation time** → accepted; the real creation time is unknown.
- **Flow migration lives in the catalog app's history** → follow the existing practice for this model; verify the migration applies on a fresh database and an upgraded one.
- **Large schemas or flows create large bodies** → the contract's body-size bound applies; the schema source additionally keeps only table and column names, never the raw SQL.
- **Entity watchers add reindex work on every entity edit** → only the schema source watches entities, and it maps to at most one document.

## Migration Plan

1. Land timestamp migrations for flows and the schema facet and the admin display.
2. Register the three sources behind the existing runtime hooks.
3. Run a full rebuild so existing content is indexed; no manual data steps.
4. Rollback: unregister the sources by reverting; timestamp columns can remain.

