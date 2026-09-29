## ADDED Requirements

### Requirement: Homepage shows entity-kind counts
The homepage SHALL display a count of catalog entities for each installed entity kind (Systems, Components, APIs, Resources, Teams), sourced from each kind's existing list endpoint, below the catalog identity and above the "About this catalog" section.

#### Scenario: Counts reflect the catalog's actual contents
- **WHEN** an authenticated user opens the homepage
- **THEN** each kind's count matches the total returned by that kind's own list endpoint at the same moment

#### Scenario: A kind with zero entities still shows its count
- **WHEN** an installed kind has no entities yet
- **THEN** its count displays as 0 rather than being omitted

### Requirement: Homepage shows an admin-editable "About this catalog" section
The homepage SHALL display a Markdown-rendered "About this catalog" section, backed by a singleton `CatalogHomeSettings` record. Any authenticated user SHALL be able to read it; only a superuser SHALL be able to edit it.

#### Scenario: Default content appears on a fresh deployment
- **WHEN** a deployment is freshly migrated with no further setup
- **THEN** the homepage's "About this catalog" section shows Atlas-appropriate default content, with no manual seed command required

#### Scenario: Admin edits the About section
- **WHEN** a superuser edits and saves the "About this catalog" content from Settings
- **THEN** the homepage reflects the updated Markdown for every user on their next view

#### Scenario: Non-admin cannot edit the About section
- **WHEN** an authenticated user who is not a superuser attempts to write to the "About this catalog" content directly via the API
- **THEN** the request is rejected

#### Scenario: About section supports plain Markdown only
- **WHEN** the "About this catalog" content is rendered
- **THEN** it renders as plain Markdown (headings, lists, links, emphasis) with no embedded diagrams, entity tables, or other custom embed syntax
