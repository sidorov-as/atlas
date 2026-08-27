# Entity references

Fields that point to another Catalog Entity, including `owner`, `system`, `providesApis`,
`consumesApis`, `dependsOn`, `members`, and a relationship `target`, use a ref string instead of
a database ID. A ref is parsed as:

```
[kind:][namespace/]name
```

- `name` is the only required part.
- `namespace` defaults to `default`. In v1, namespaces cannot be set, and `metadata.name` cannot
  contain `/`.
- `kind` is optional wherever the field itself pins the expected kind (an `owner` field always
  resolves against `group`, regardless of whether the ref string includes `group:`). It is
  required only where a field can point to more than one kind.

Resolution matches `name` and `namespace` case-insensitively against the target kind. A
`CatalogEntity`'s `.ref` property always renders as `kind:name`, with the namespace omitted
because it is always `default`. A ref that does not exist or resolves to the wrong kind raises
`RefError`. Most fields are resolved at write time. For a relationship's `target`, only syntax is
checked immediately; reconciliation resolves the target later (see
[Life of an entity](life-of-an-entity.md#relationship-reconciliation)) so a target declared later
in the same ingestion run still resolves.

## Relation

A Relation is a derived, typed edge. It is never written directly or included in a
`catalog-info.yaml` field. Each kind's reference fields produce a fixed set of Relation rows
whenever that kind's details are saved:

| Subject kind | Predicate | Object kind | Mirror (on the object) |
| --- | --- | --- | --- |
| `system`, `component`, `resource`, `api` | `ownedBy` | `group` | `ownerOf` |
| `component`, `resource`, `api` | `partOf` | `system` | `hasPart` |
| `component` | `dependsOn` | `resource` | `dependencyOf` |
| `component` | `providesAPI` | `api` | `apiProvidedBy` |
| `component` | `consumesAPI` | `api` | `apiConsumedBy` |
| `group` | `hasMember` | `user` | `memberOf` |

Both directions are materialized as separate rows, so either endpoint can list its relations with
a single subject-or-object filter. Recompute is targeted: saving a `ComponentDetails` row, or
changing one of its M2M fields, deletes and reinserts only the rows owned by that Component as
subject. Other entities' relations are unchanged. Each kind's `*Details` model triggers this
through `post_save` and `m2m_changed` signals. A plugin calls the recompute function only through
the shared `atlas_plugin_api` entry point and never assembles a Relation row by hand.

## Architecture Relationship

An Architecture Relationship is authored rather than derived. A manifest's `spec.relationships`
block or a manual API call creates one. It carries:

- `source` / `target`: refs to any two Catalog Entities.
- `label`: required, freeform (e.g. `"Makes API calls to"`).
- `technology`: optional freeform (e.g. `"REST/HTTPS"`).
- `interactionKind`: one of `synchronous`, `asynchronous`, `data-access`, `manual` (default).
- `tags`: a list using the same tag vocabulary as the rest of the catalog.
- `origin`: `manual` or `yaml`, tracked per relationship rather than per entity. A manually
  created relationship and a YAML-declared one can coexist on the same entity. A YAML-origin row
  is read-only through the API and can only be changed by re-ingestion.

Only System, Component, Resource, and API entities can be a relationship's `source`; any kind can
be a `target`. Group and User entities cannot be sources. A `dependsOn` Relation and an
Architecture Relationship can describe the same two entities. The Architecture Relationship is
the authored record and carries a label, technology, and interaction kind. C4-style diagrams use
Architecture Relationships. The "Relations" list on an entity's detail page uses Relation rows.

## Reading an entity's relations

An entity's Relation rows are returned as `(predicate, target_ref, target_kind, target_id)`
tuples from that entity's point of view. Rendering either entity's page never requires querying
both a System's `hasPart` row and its Component's `partOf` mirror.
