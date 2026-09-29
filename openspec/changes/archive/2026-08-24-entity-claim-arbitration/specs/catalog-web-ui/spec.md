## ADDED Requirements

### Requirement: Blocked-by-conflict banner
An entity's detail page SHALL show a banner naming the repository that could not claim it when the entity is currently blocking that repository's YAML claim. This banner is visually distinct from the existing read-only "managed by `catalog-info.yaml` in `org/repo`" banner (`bootstrap-catalog-service`'s `catalog-web-ui` capability): the read-only banner is informational (this entity is YAML-managed), while the blocked-by-conflict banner is a warning that names an action the viewer can take (adopt the entity to resolve the conflict, if they're a member of its owner Group).

#### Scenario: Blocked entity shows a distinct warning banner
- **WHEN** a user opens the detail page of a manual entity that is currently blocking a YAML claim from repository `org/repo`
- **THEN** the page shows a warning-styled banner naming `org/repo`, distinct in style from the informational read-only banner shown on YAML-managed entities

#### Scenario: Entity with no active conflict shows neither banner
- **WHEN** a user opens the detail page of a manual entity with no active conflict
- **THEN** neither the blocked-by-conflict banner nor the read-only banner is shown, and Add/Edit affordances are available as usual
