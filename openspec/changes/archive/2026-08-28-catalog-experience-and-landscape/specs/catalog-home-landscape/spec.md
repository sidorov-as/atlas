## ADDED Requirements

### Requirement: Configured catalog identity is displayed on the homepage
The system SHALL expose the effective Django-configured catalog title and description to authenticated catalog clients. The homepage SHALL display that title and description above a divider, followed by the catalog navigation cards.

#### Scenario: Deployment overrides catalog identity
- **WHEN** a deployment sets the catalog title and description Django settings
- **THEN** an authenticated user opening the homepage sees those effective values above the catalog cards

#### Scenario: Catalog identity uses defaults
- **WHEN** no catalog title or description setting is overridden
- **THEN** the homepage displays the documented Atlas default title and description

### Requirement: Homepage renders a catalog-wide System Landscape
The homepage SHALL display a System Landscape section below its catalog navigation cards using the shared diagram viewer controls. The section SHALL describe the diagram as the relationships among catalog systems and explicitly interacting people.

#### Scenario: User explores the landscape
- **WHEN** an authenticated user opens the homepage
- **THEN** the System Landscape image provides pan, zoom, fit-to-viewport, SVG download, and PNG download controls
