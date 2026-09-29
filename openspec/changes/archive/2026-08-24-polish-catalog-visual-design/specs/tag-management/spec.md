## MODIFIED Requirements

### Requirement: Tag color configuration
Admins SHALL be able to configure a tag's color by choosing one preset from a fixed palette on the Settings page, backed by a `Tag` model exposed through an admin API. Arbitrary color values (e.g. an open color picker) are not accepted.

#### Scenario: Admin sets a tag's color
- **WHEN** an admin opens the Settings page and selects a palette preset for a tag
- **THEN** that preset is persisted and used to render that tag everywhere it appears in the catalog

#### Scenario: Unconfigured tag falls back to a default color
- **WHEN** a tag exists on an entity but has no explicitly configured color
- **THEN** it renders with a default, neutral preset instead of failing or appearing unstyled

#### Scenario: New tag automatically appears in the Settings page
- **WHEN** an entity is saved, manually or via `catalog-info.yaml` ingestion, with a tag string that has no existing `Tag` record
- **THEN** a `Tag` record is created for it with the default preset, and it appears in the Settings page for an admin to recolor

#### Scenario: Admin cannot set an arbitrary, non-palette color
- **WHEN** an admin attempts to set a tag's color to a value outside the fixed palette (e.g. via a direct API request)
- **THEN** the request is rejected and the tag's color is unchanged

### Requirement: Colored tag rendering
Every place tags are displayed on an entity SHALL render each tag as a Label using its configured preset's background color paired with that same preset's text color, guaranteeing readable contrast regardless of which preset is chosen.

#### Scenario: Entity detail page shows colored tags
- **WHEN** a user opens an entity's detail page and it has tags
- **THEN** each tag is rendered as a Label with its configured preset's background color and matching, readable text color

#### Scenario: Tag text remains readable on every preset
- **WHEN** a tag is rendered with any preset from the fixed palette, in either light or dark theme
- **THEN** the tag's text color has sufficient contrast against its background to be readable
