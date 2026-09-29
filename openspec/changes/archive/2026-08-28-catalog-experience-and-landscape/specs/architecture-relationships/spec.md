## MODIFIED Requirements

### Requirement: Relations views distinguish catalog structure from architecture interactions
The relations API and UI SHALL expose derived Catalog Relations separately from Architecture Relationships. An Architecture Relationship listing for an entity SHALL include every relationship where that entity is the source or target and SHALL retain canonical source, target, direction, origin, target kind, id, and ref navigation. Write authorization and mutation SHALL remain tied to a manually managed source entity.

#### Scenario: Component has both kinds of relationships
- **WHEN** a Component has a derived `consumesAPI` relation and a declared architecture interaction
- **THEN** its Relations tab shows the derived relation in Catalog relations and the declared interaction in Architecture relationships

#### Scenario: Target lists an authored incoming interaction
- **WHEN** `component:customer-portal` declares an Architecture Relationship to `component:api-gateway`
- **THEN** the architecture-relationship listing for `component:api-gateway` includes that canonical directed relationship with `component:customer-portal` as its source

#### Scenario: Target cannot edit a manual incoming interaction
- **WHEN** an authorized user views a manual Architecture Relationship from the target entity's Relations tab
- **THEN** the API and UI do not allow that target entity to update or delete the relationship
