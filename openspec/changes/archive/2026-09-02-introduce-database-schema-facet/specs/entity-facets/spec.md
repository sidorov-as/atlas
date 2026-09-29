## ADDED Requirements

### Requirement: A Facet attaches to core identity, not to a kind's own table
A plugin-owned Facet SHALL be a `OneToOne` model keyed by `CatalogEntity.id`, never a field added to core or to another plugin's kind-details table.

#### Scenario: A facet exists independent of the owning kind's details model
- **WHEN** a plugin attaches a Facet to an entity
- **THEN** the Facet's storage references `CatalogEntity.id` directly, with no foreign key into the entity kind's own details table

### Requirement: Facet data outlives a view contribution
Removing a view contribution that renders a Facet SHALL NOT delete or alter the Facet's underlying data.

#### Scenario: Removing the view leaves the facet intact
- **WHEN** the plugin contribution that renders a Facet as a view is removed from a distribution
- **THEN** the Facet's stored data remains unchanged and is available again if the view contribution is reinstated

### Requirement: A Facet has its own lifecycle, separate from the entity's core lifecycle
Creating, updating, or deleting a Facet SHALL NOT go through the core Entity Service's kind-lifecycle transaction; it SHALL use an endpoint owned by the Facet's providing plugin.

#### Scenario: Facet write does not invoke the entity's kind handler
- **WHEN** a Facet is created or updated on an entity
- **THEN** the entity's own `EntityKindHandler.update_details` is not invoked as part of that write

### Requirement: An entity's core lifecycle is unaffected by its facets
Deleting or updating a facet-bearing entity's core/kind data SHALL succeed independent of that entity's attached facets, and vice versa.

#### Scenario: Deleting an entity with an attached facet
- **WHEN** an entity carrying a Facet is deleted through the Entity Service
- **THEN** the deletion is not blocked by the presence of the Facet
