# Domain glossary

Atlas is an extensible software catalog that an operator assembles for a particular deployment.
The terms below have specific meanings in Atlas documentation.

## Catalog model

**Catalog Entity**
: A globally identified catalog record whose common identity and metadata are independent of its
  kind-specific details.

**Entity Kind**
: A registered category of Catalog Entity that defines its kind-specific meaning and details while
  retaining the entity's identity. Standard Catalog registers `system`, `component`,
  `resource`, `group`, and `actor`; the APIs plugin registers `api`.

**Entity Kind Handler**
: The plugin-supplied implementation of an Entity Kind's create, update, and delete behavior. It
  persists and serializes kind-specific fields, and vetoes a delete that would leave the
  catalog inconsistent.

**Entity Service**
: The single transactional path for authorizing, validating, resolving the Entity Kind Handler,
  persisting, and auditing every change to a Catalog Entity. No other code path may create,
  update, or delete one.

**Entity Intent**
: A proposed state for a Catalog Entity submitted by an ingestion pipeline for validation and
  reconciliation through the Entity Service.

**Unavailable Entity**
: A read-only Catalog Entity whose Entity Kind Handler is not registered, for example because its
  owning plugin was removed from the distribution. Its identity and relationships are preserved.

**Facet**
: An optional structured aspect of a Catalog Entity, owned by a plugin, with a lifecycle separate
  from the owning Entity Kind's details. The Database Schema plugin's ER data is a Facet on
  `resource` entities rather than a field of the `resource` kind.

**Relation**
: A derived, typed edge between two Catalog Entities, such as `ownedBy`, `partOf`, `dependsOn`,
  `providesAPI`, `consumesAPI`, or `hasMember`. Relations are recomputed from entity fields and
  cannot be written directly. They differ from Architecture Relationships.

**Architecture Relationship**
: A directed, user-authored interaction between two Catalog Entities. It has a label, optional
  technology and interaction kind, and a manual or YAML origin. It is populated by a manifest's
  `relationships:` block or created manually; it is not derived or regenerated from entity
  specifications.

**Removed**
: A Catalog Entity's soft-decommissioned status. Its row, kind details, and existing relations
  remain intact, and its name remains reserved. Removed entities are hidden from default list and
  search views. See
  [Removed, Revive, and Purge](life-of-an-entity.md#removed-revive-and-purge).

**Revive**
: The action that returns a Removed entity to `active`, preserving its id, relations, and audit
  history. It does not create a new entity or restore one by name.

**Purge**
: The explicit, permission-gated destructive action available only from Removed. It permanently
  deletes a Catalog Entity's row and frees its name for a new entity with a
  new id. Blocked by any still-active reference to it.

**Purge Grant**
: A permission that an owner Group's admins assign to a specific member, or that a member holds
  through global-admin status. It authorizes that member to Purge entities owned by the Group,
  including
  `source_kind=yaml` ones.

## Ingestion and arbitration

**Entity Claim**
: The association between a Catalog Entity's ref and the Source Kind (`manual` or `yaml`) that
  controls its fields. For `yaml`, it also identifies the registered repository.

**Claim Arbitration**
: The check an ingestion run performs, before submitting an Entity Intent, deciding whether a
  ref's existing claim yields to, rejects, or is overwritten by an incoming YAML claim.

**Conflict Record**
: A persisted record of a rejected ingestion claim, including its repository, ref, and reason. It
  remains visible on the blocked entity and in the admin even if the blocking repository is later
  deleted.

**Adoption**
: The one-way conversion, by a permitted user, of a manual entity's claim to `source_kind=yaml`
  for a named repository. A YAML claim cannot be adopted back to manual.

## Plugin composition

**Plugin**
: A trusted, operator-selected extension in an Atlas deployment that contributes capabilities
  through supported extension points. Plugins are deployment code. They are neither sandboxed nor
  installable from the running application.

**Plugin Release**
: One versioned delivery unit whose optional backend and frontend artifacts are installed and
  verified together.

**Extension Point**
: A named, typed point where core or a plugin declares that other plugins may contribute an
  implementation, such as a route, tab, widget, or Entity Kind, without directly mutating a shared
  registry. Every extension point declares one of three cardinalities: a `collection` (many
  contributions, like detail tabs), a `singleton` (exactly one selected implementation), or
  `keyed` (many contributions distinguished by a unique key, like Entity Kinds).

**Contribution**
: The immutable declaration a plugin exports into an Extension Point, such as a route, detail tab,
  or home widget. Plugins export contributions as data at module-import time and never mutate a
  registry as an import side effect.

**Capability**
: A named, versioned service contract that one plugin publishes and another resolves by id rather
  than by importing the provider's models or internals. A missing required capability makes
  composition fail. A missing optional capability makes its dependent contributions inapplicable.

**Distribution**
: A versioned, reproducible selection of core, the Plugin API, and specific Plugin Releases that
  an operator builds and deploys as one Atlas installation.

**Deployment Manifest**
: The operator-authored, source-controlled file that names the Plugin Releases and registry
  sources that compose a Distribution.

**Distribution Lock**
: The composer-generated record of exact resolved artifact versions for a
  Distribution's manifest; integrity comes from `uv.lock` and `package-lock.json`. It is used only to build reproducible images; containers do not
  download anything when they start.

**Composer**
: The build-time tool that resolves a Deployment Manifest into a Distribution Lock and generates
  the backend and frontend composition for the selected Plugin Releases.

## People and access

**Operator**
: The party that assembles, configures, and deploys an Atlas installation, including the selected
  plugins.

**Actor**
: A Catalog Entity representing a person. It can be referenced by catalog relationships whether or
  not that person can log in to Atlas.

**Principal**
: The login identity for a person or system. An Actor can optionally link to one Principal, but
  they are distinct records with distinct lifecycles.

**Policy Evaluator**
: The distribution-selected singleton implementation that decides whether a Principal holds a
  permission on a resource. The default is built-in role-based access control; an external policy
  engine is another option.
