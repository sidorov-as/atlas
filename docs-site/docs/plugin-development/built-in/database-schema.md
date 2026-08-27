# Database Schema architectural case study

`atlas.database-schema` is an optional full-stack plugin that requires
`atlas.standard-catalog`. It provides a deliberately narrow example of adding
data and UI to an existing catalog entity without changing that entity's
definition. Follow [Build your first plugin](../tutorial.md) for the minimal
route-and-navigation plugin first; return here when deciding whether a Facet
and entity-detail contributions fit your feature.

The product-facing behavior is documented in the [Database Schema feature
guide](../../features/database-schema.md). This page explains the architectural
choices behind it.

## Decision 1: keep schema data independent of the Resource kind

The plugin owns a `DatabaseSchema` Facet with a one-to-one record associated
with the catalog entity, not with Standard Catalog's `ResourceDetails` model.
The record holds the dialect, SQL input, parsed schema, and parse status. This
keeps the data independent of a frontend contribution and the Resource kind's
core details under the Standard Catalog plugin's ownership.

Choose this shape when an optional plugin owns an aspect of an existing entity.
Do not create a new Entity Kind merely to add such an aspect, and do not put
the plugin's fields in another plugin's details model. The focused endpoint
tests in `plugins/database-schema/backend/atlas_plugin_database_schema/tests/test_views.py`
cover creating the facet, parsing each supported dialect, conflicts, and its
absence before creation.

The Database Schema plugin registers no Entity Kind, capability, or permission
of its own. Standard Catalog declares `schema.host.v1` for Resources; schema
writes reuse the owning Resource's existing edit authority. Its descriptor
therefore declares the Standard Catalog dependency but has no runtime
registration hook.

## Decision 2: target contributions by capability, not kind name

The frontend contributes **Schema** and **ER Diagram** detail tabs. Both use
the `schema.host.v1` capability predicate, rather than `kind === 'Resource'`.
That makes the extension usable by a future kind that explicitly supports the
same contract, while keeping it hidden from entities that do not.

The contribution ids are namespaced under `atlas.database-schema`, and the ER
diagram tab requests full-width layout. The tab contract is tested in
`plugins/database-schema/frontend/src/entityDetailTabs/resource.test.ts`: it
checks both tabs appear for a capability-declaring entity, disappear without
the capability, and are not limited to a hard-coded kind.

Use this pattern when a contribution depends on a declared capability. Use a
kind-specific condition only when the contract genuinely belongs to that kind;
see [Choose an extension mechanism](../choose-an-extension.md) for the
selection guide.

## Decision 3: give plugin-owned data a plugin-owned API

The facet is served through the namespaced endpoint
`/api/plugins/atlas.database-schema/resources/<id>/schema/`, not generic
entity CRUD. The endpoint is included only when the optional plugin is
selected, and it creates, reads, or updates the facet independently of the
Resource's kind details. A missing facet is a normal `404` state for the tabs,
not evidence that the Resource is invalid.

This boundary is appropriate when a plugin owns the data lifecycle and schema.
It avoids extending a core endpoint with optional-plugin fields. See
[Extension points and capabilities](../extension-points.md) when the API must
collaborate with another plugin rather than own its own resource.

## Decision 4: preserve input when parsing fails

Saving SQL parses it synchronously for PostgreSQL, MySQL, or MS SQL. A
successful save stores structured data for the ER diagram; a failed parse
preserves the SQL input and records a failed parse state so the author can
correct it. The plugin does not connect to or execute against a live database.

For derived data, retain the user's source, make the derived state explicit,
and avoid silently discarding either. The
[feature guide](../../features/database-schema.md#limits-and-troubleshooting)
explains the user-facing recovery path.

## Decision 5: register a facet-writer instead of being imported

`register_runtime()` registers this plugin's `apply`/`clear` implementation into Ingestion's
`atlas.ingestion.facet_writers.v1` extension point under key `'database-schema'`, rather than
Ingestion importing this plugin directly. `apply` reuses the same `parse_schema()` the manual
editor already uses; `clear` removes the Facet. Both run in a second pass, after a Resource's own
entity fields are already upserted through the Entity Service — the Facet write still never goes
through the Resource kind handler (Decision 1 above still holds).

Resolving `'database-schema'` and finding nothing registered — this plugin isn't selected for the
distribution — is Ingestion's signal to skip the write entirely; there is no capability check,
because `schema.host.v1` describes what a kind *could* support, not whether this plugin is
currently active (a distribution selecting Standard Catalog without Database Schema would have the
capability declared but no table migrated for it). See [Ingestion: extension points it
publishes](ingestion.md#extension-points-it-publishes) for the other side.

Once a Resource is YAML-managed, its Facet also stops accepting manual writes through this
plugin's own `POST`/`PATCH` — a narrow, local check added to this controller alone (not a
generalized "facets are protected once YAML-managed" mechanism), since the central enforcement
every other kind of YAML-managed data relies on lives in the Entity Service, which this
plugin's endpoint never goes through by design (Decision 3). The check is unconditional on the
entity's `source_kind`, not on whether the current manifest declares `spec.databaseSchema` this
run: a Resource that becomes YAML-managed freezes its existing Facet immediately, even before its
manifest ever declares the field. See the [feature guide](../../features/database-schema.md#repository-managed-schemas)
for the operator-facing behavior.

Choose this shape — a keyed extension point the dependent plugin registers into, rather than the
owning plugin importing the dependent one — when an optional plugin needs to react to another
plugin's core pipeline without that pipeline acquiring hard-coded knowledge of an open-ended set of
optional consumers.

## What to reuse

- Choose a [Facet](../entity-kinds-and-facets.md) when your plugin owns an
  optional aspect of an existing entity.
- Register into another plugin's published extension point instead of being imported by it, so
  resolving your key and finding nothing registered stays a reliable "not selected" signal rather
  than a capability check.
- Gate [frontend contributions](../tutorial.md#1-create-the-two-package-declarations)
  with the capability contract they need.
- Give independently owned data a namespaced plugin API and focused tests.
- Keep product workflows in the [feature guide](../../features/database-schema.md),
  while this case study remains the explanation of the extension decisions.
