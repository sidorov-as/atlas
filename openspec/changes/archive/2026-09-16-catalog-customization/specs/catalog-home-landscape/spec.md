## REMOVED Requirements

### Requirement: Configured catalog identity is displayed on the homepage
The system SHALL expose the effective Django-configured catalog title and description to authenticated catalog clients. The homepage SHALL display that title and description above a divider, followed by the catalog navigation cards.

#### Scenario: Deployment overrides catalog identity
- **WHEN** a deployment sets the catalog title and description Django settings
- **THEN** an authenticated user opening the homepage sees those effective values above the catalog cards

#### Scenario: Catalog identity uses defaults
- **WHEN** no catalog title or description setting is overridden
- **THEN** the homepage displays the documented Atlas default title and description

**Reason**: Catalog identity is no longer backend-configured. `CatalogConfigurationController` and the `CATALOG_TITLE`/`CATALOG_DESCRIPTION` Django settings are removed entirely.
**Migration**: See the new `catalog-branding` capability — identity now comes from the committed `core/frontend/src/atlas.config.ts` file, read directly by the frontend.

### Requirement: Homepage renders a catalog-wide System Landscape
The homepage SHALL display a System Landscape section below its catalog navigation cards using the shared diagram viewer controls. The section SHALL describe the diagram as the relationships among catalog systems and explicitly interacting people.

#### Scenario: User explores the landscape
- **WHEN** an authenticated user opens the homepage
- **THEN** the System Landscape image provides pan, zoom, fit-to-viewport, SVG download, and PNG download controls

**Reason**: The System Landscape diagram is heavy and unrelated to "home"; it moves to its own dedicated destination.
**Migration**: See the `c4-plugin` capability's new "System Map" nav destination — the same diagram viewer and controls now live at their own route rather than on the homepage.
