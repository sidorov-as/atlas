---
title: Entity kinds and facets
description: Model first-class catalog records and plugin-owned data attached to existing entities without bypassing Atlas lifecycle rules.
audience:
  - plugin-author
page-type: guide
---

# Entity kinds & facets

Adding new catalog data to Atlas means choosing between two mechanisms: a new **Entity Kind**, if
you're registering an entirely new category of catalog record, or a **Facet**, if you're
attaching optional structured data to a kind that already exists. Make this choice early because
it determines the data model and API shape.

## Before you begin

- Start with [Choose an extension mechanism](choose-an-extension.md) if the
  boundary is not clear yet.
- A backend plugin package, its descriptor, and a selected distribution are
  required; see [Plugin layouts](plugin-layouts.md) and [Build your first
  plugin](tutorial.md).
- Use an Entity Kind only when the record has its own catalog identity. A
  Facet is not a shortcut for adding a second kind-specific details table.

The plugin owns its data and validation. Core keeps the common entity envelope,
authorization, transactions, audit history, and lifecycle consistent across every kind.

## Choose the ownership boundary

| Need | Use | Plugin owns | Core or existing kind owns |
| --- | --- | --- | --- |
| A record that can be named, linked to, discovered, and managed independently | **Entity Kind** | Its `*Details` model, `spec` schema, serialization, kind-specific validation, and declared capabilities | `CatalogEntity` identity, common metadata, relations, permissions checks, audit records, and lifecycle transaction |
| Optional structured data meaningful only for an existing entity | **Facet** | The facet model, namespaced API and UI, its validation, migrations, and deletion behavior | The attached entity's identity, kind `spec`, and primary lifecycle |
| A new visual or behavior for compatible kinds without new persisted data | **Contribution gated by a capability** | Its contribution and capability requirement | The kind's declared capabilities and the detail shell |

Do not put one plugin's optional data in another plugin's details model and do
not import a sibling plugin's model to reach it. The [Database Schema feature
guide](../features/database-schema.md) is the concrete Facet example: it owns
schema data keyed to `CatalogEntity` and targets compatible Resources through
`schema.host.v1`.

## Entity Kind Handler

A plugin registers an Entity Kind by implementing the `EntityKindHandler` protocol and
registering an instance against its `kind_id`:

```python
@runtime_checkable
class EntityKindHandler(Protocol):
    kind_id: str
    spec_schema: type[BaseModel]
    provides: list[str]

    def create_details(self, entity: CatalogEntity, spec: BaseModel) -> None: ...
    def update_details(self, entity: CatalogEntity, spec: BaseModel) -> None: ...
    def serialize_details(self, entity: CatalogEntity) -> BaseModel: ...
    def validate_delete(self, entity: CatalogEntity) -> None: ...
    def is_deprecated(self, entity: CatalogEntity) -> bool: ...
```

The Entity Service is the only caller of these methods. It owns the transaction and audit record
around every create, update, and delete. A handler handles only the kind-specific part:
it persists `spec` fields to its own `*Details` row, serializes them for reads, and
raising `ValidateDeleteError` from `validate_delete` to veto a delete that would leave the catalog
inconsistent. `is_deprecated` is a read-only, cosmetic indication for entities
that reference this kind; it does not change the entity's lifecycle status. A
handler never opens its own transaction and never talks to another kind's table
directly.

### Lifecycle hooks and their boundaries

| Hook | Called by | Handler responsibility | Do not do here |
| --- | --- | --- | --- |
| `create_details` | Core after it saves the common entity | Create the plugin-owned details row from a validated `spec` | Re-authorize, re-save common metadata, or start a transaction |
| `update_details` | Core when a `spec` patch is supplied | Apply only fields in `spec.model_fields_set` and save the details row | Treat omitted fields as values to clear |
| `serialize_details` | Core on an available entity read | Return the public `spec` model | Leak private database fields or resolve another plugin's internals |
| `validate_delete` | Core inside the delete transaction | Reject a deletion that would make plugin-owned or declared relationships inconsistent | Delete other plugins' data, or rely only on a later database error |
| `is_deprecated` | Core while serializing relationships | Report a kind-owned cosmetic lifecycle flag, or `False` when none exists | Change `entity.status` or use it as an authorization decision |

Core executes the complete create, update, and delete path: it validates the
common envelope, checks the central policy, resolves the handler, wraps the
write and audit record in one transaction, and then invokes the relevant hook.
For a patch, `update_details` must preserve fields absent from
`model_fields_set`; that is the API's partial-update contract.

`update_details` receives a partial `spec`. Treat it as a patch and only touch the fields
present in `spec.model_fields_set`, matching the wire API's partial-update semantics.

### Declaring what a kind provides

`provides` is a list of capability ids your kind supports, independent of any particular
consumer. A kind with nothing to declare sets `provides = []`. A diagramming
plugin can then target "every kind that represents an architectural subject" instead of hard-coding kind
ids: Standard Catalog's `system` and `component` kinds both declare `architecture.subject.v1`,
and the C4 plugin's diagram tab is gated on that capability rather than on
`kind === 'system' or kind === 'component'`.

### Registering the handler

```python
def register_runtime() -> None:
    from atlas_plugin_yourplugin.kinds import register_your_kinds

    register_your_kinds(owner=PLUGIN.id)
```

Registration happens in `register_runtime()`, called once during the shared runtime
entry-point-loading phase, after Django itself has finished setting up, never at import time. A
second handler trying to claim an already-registered `kind_id` fails composition, naming both the
existing owner and the conflicting registration.

Declare only stable, semantic capability ids in `provides`. Consumers should
target the capability, not your `kind_id`, so a later compatible kind can join
the same workflow without changing the consumer. Read [Backend
collaboration](backend-collaboration.md) before publishing a capability
consumed by another plugin.

## Facets

A Facet is optional, structured data owned by a plugin and attached to an existing entity. It has
its own model and lifecycle, independent of the owning kind's details row. The
Database Schema plugin's parsed schema is a Facet on `resource` entities: it's keyed on the
`CatalogEntity` itself, not on `resource`'s own details model, specifically so that the Facet's
data outlives any particular view that renders it, and so the kind's own details table never
needs to know the Facet exists.

The owning plugin must expose and authorize its Facet through its own
namespaced API. A missing Facet is a normal absence of optional data, not a
reason to make the base entity unavailable. Give the Facet its own migrations
and tests; define how it is removed when the attached entity is permanently
deleted, and keep that behavior within the owning plugin's data model.

Choose a Facet over a new Entity Kind when the data:

- only makes sense attached to an entity that already has its own identity and lifecycle, and
- doesn't need its own create/update/delete authorization semantics distinct from the entity it's
  attached to.

If instead you're modeling something that has its own identity, needs its own lifecycle, and
should show up as a first-class catalog record in its own right, register a new Entity Kind
instead.

## Make deletion safe

`validate_delete` is the handler's final semantic check before Core deletes an
entity. It runs inside the same transaction as the audit record and database
delete. Raise `ValidateDeleteError` with an actionable explanation when a
delete would leave a relationship, plugin-owned record, or supported workflow
inconsistent. Database `PROTECT` constraints remain a backstop; they do not
replace a clear domain-level error.

Keep the validation narrow and owned:

- check constraints belonging to your kind or a declared public extension
  contract;
- use a public guard or capability when another plugin must participate, rather
  than importing that plugin's models;
- make the error name the blocking references or the corrective action; and
- test both the rejected delete and the allowed delete.

Removal and revival are separate lifecycle actions. They change the common
entity status and preserve its data; the kind handler's `validate_delete` is
for permanent deletion and also acts as a structural backstop during Purge.
For the user-facing lifecycle distinction, see [Manage an entity
lifecycle](../using-atlas/manage-entity-lifecycle.md) and the canonical
[life-of-an-entity concept](../concepts/life-of-an-entity.md).

## Unavailable Entities

If a plugin providing an Entity Kind is later removed from a distribution, its entities become
Unavailable Entities: read-only, with their identity and relationships
preserved, but with no Entity Kind Handler currently registered to serve their kind-specific
details. Reinstalling a compatible plugin later restores full behavior against the same
underlying data. See [Preserving data on removal](../concepts/principles.md#removing-a-plugin-is-reversible-by-default).

On a read, Core returns the entity with `spec=None` and `unavailable=True`; it
does not call a missing handler. Updates and deletes reject with
`EntityUnavailableError`, because Core cannot safely validate kind-specific
data without its provider. This is distinct from a newly requested unknown
kind, which is rejected at creation time. Never work around this boundary by
writing the details model directly. Reinstall or re-enable a compatible plugin,
then verify the restored `spec` and relationships before resuming work.

Facets do not make their host unavailable when their plugin is absent: the
entity remains served by its Entity Kind. Its optional Facet route or
contribution simply is not available until the Facet plugin is selected again.

## Focused tests

Test the public contract at the narrowest useful level before composing a full
distribution:

1. Unit-test the handler's create, patch, serialization, capability declaration,
   deletion veto, and `is_deprecated` behavior. Keep these tests next to the
   plugin that owns the handler.
2. Add an Entity Service test for the actual lifecycle boundary: permissions,
   audit behavior, failed `ValidateDeleteError`, and a successful delete where
   applicable.
3. For a Facet, test its migrations, namespaced API authorization, absence,
   and cleanup behavior independently of the host kind.
4. Simulate an absent handler with a registry that omits the kind. Assert that
   reads preserve identity and relations with `spec=None`, writes are rejected,
   and restoring the handler makes the details readable again.

The checked-in contract and Core regression suites are useful baselines:

```shell
cd core/backend
uv run pytest \
  ../../plugin-api/python/atlas_plugin_api/tests/test_kinds.py \
  server/apps/catalog/tests/test_entity_kind_registry.py \
  server/apps/catalog/tests/test_entity_service.py \
  server/apps/catalog/tests/test_unavailable_entity.py -q
```

Run the focused tests for your plugin as well. Before merging a distribution
change, run composition preflight so duplicate kind ids and missing runtime
registration fail before deployment.

## Verification and common failures

After starting the composed distribution, create or read one entity of the new
kind and confirm its `spec`, capabilities, and detail view. For a Facet, verify
that the base entity still reads without optional data and that the Facet is
visible only when its plugin and capability gate apply.

| Symptom | Likely cause | Safe correction |
| --- | --- | --- |
| Composition reports a duplicate kind id | Two selected plugins registered the same `kind_id` | Give the new kind a unique id or remove the conflicting selection; do not overwrite the registry |
| A field disappears on PATCH | `update_details` replaced the whole model | Update only fields in `spec.model_fields_set` |
| Delete reaches a database constraint error | The handler omitted a semantic deletion guard | Add a narrow `validate_delete` check that raises `ValidateDeleteError` |
| `spec` is `null` and the entity is read-only | The kind provider is not active | Restore a compatible plugin; do not write its details table directly |
| A tab appears for the wrong kind | The contribution tested a kind name rather than a capability | Declare a semantic capability and gate the contribution with it |

## Next steps

- Use [Backend collaboration](backend-collaboration.md) when another
  plugin needs to target or collaborate with your kind.
- See the [Database Schema case study](built-in/database-schema.md) for a
  Facet with capability-gated UI.
- Use the [plugin contract reference](reference.md) for the exact published
  Python and TypeScript surfaces.
