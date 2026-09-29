## ADDED Requirements

### Requirement: Tag color configuration
Admins SHALL be able to configure a color for any tag via a Settings page, backed by a `Tag` model exposed through an admin API.

#### Scenario: Admin sets a tag's color
- **WHEN** an admin opens the Settings page and sets a color for a tag
- **THEN** that color is persisted and used to render that tag everywhere it appears in the catalog

#### Scenario: Unconfigured tag falls back to a default color
- **WHEN** a tag exists on an entity but has no explicitly configured color
- **THEN** it renders with a default, neutral color instead of failing or appearing unstyled

#### Scenario: New tag automatically appears in the Settings page
- **WHEN** an entity is saved, manually or via `catalog-info.yaml` ingestion, with a tag string that has no existing `Tag` record
- **THEN** a `Tag` record is created for it with the default color, and it appears in the Settings page for an admin to recolor

### Requirement: Colored tag rendering
Every place tags are displayed on an entity SHALL render each tag as a Label using its configured background color.

#### Scenario: Entity detail page shows colored tags
- **WHEN** a user opens an entity's detail page and it has tags
- **THEN** each tag is rendered as a Label with its configured color as the background
