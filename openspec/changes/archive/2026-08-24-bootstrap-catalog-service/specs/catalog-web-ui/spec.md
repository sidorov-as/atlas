## ADDED Requirements

### Requirement: Systems list page
The Systems list page SHALL show a filterable, searchable table (Owner, Lifecycle, Type) with an "Add System" action.

#### Scenario: User filters and searches the list
- **WHEN** a logged-in user opens the Systems list and sets an Owner filter and a search query
- **THEN** the table shows only Systems matching both

### Requirement: Components list page
The Components list page SHALL show a filterable, searchable table (Owner, Lifecycle, Type) with an "Add Component" action, independent of any System's detail tabs.

#### Scenario: User filters and searches the list
- **WHEN** a logged-in user opens the Components list and sets an Owner filter and a search query
- **THEN** the table shows only Components matching both, regardless of which System they belong to

### Requirement: Resources list page
The Resources list page SHALL show a filterable, searchable table (Owner, Lifecycle, Type) with an "Add Resource" action, independent of any System's detail tabs.

#### Scenario: User filters and searches the list
- **WHEN** a logged-in user opens the Resources list and sets an Owner filter and a search query
- **THEN** the table shows only Resources matching both, regardless of which System they belong to

### Requirement: APIs list page
The APIs list page SHALL show a filterable, searchable table (Owner, Lifecycle, Type) with an "Add API" action, independent of any System's detail tabs.

#### Scenario: User filters and searches the list
- **WHEN** a logged-in user opens the APIs list and sets an Owner filter and a search query
- **THEN** the table shows only APIs matching both, regardless of which System they belong to

### Requirement: Entity detail pages
System, Component, Resource, and API SHALL each have a detail page with an Overview and Relations view; System and Component detail pages SHALL additionally show their C4 Diagram tab and (for System) Components/Resources/APIs/Docs tabs.

#### Scenario: System detail shows its tabs
- **WHEN** a user opens a System's detail page
- **THEN** it shows Overview, Components, Resources, APIs, Docs, Relations, and C4 Diagram tabs

#### Scenario: Component detail shows its tabs
- **WHEN** a user opens a Component's detail page
- **THEN** it shows Overview, Relations, and C4 Diagram (component view) tabs, but no Components/Resources/APIs/Docs tabs

#### Scenario: Resource or API detail shows only Overview and Relations
- **WHEN** a user opens a Resource's or an API's detail page
- **THEN** it shows only Overview and Relations tabs, with no C4 Diagram tab

### Requirement: Add/Edit forms for manual entities only
A manual entity's detail page SHALL show Add/Edit affordances; a YAML-managed entity's detail page SHALL show a read-only banner naming the backing repository instead.

#### Scenario: YAML-managed entity shows a banner, not an Edit button
- **WHEN** a user opens the detail page of an entity ingested from `org/repo`
- **THEN** the page shows "managed by `catalog-info.yaml` in `org/repo`" instead of an Edit button

### Requirement: Teams (Groups) pages
The Teams list and detail pages SHALL show each Group's members and the entities it owns.

#### Scenario: Team detail shows members and owned entities
- **WHEN** a user opens a Team's detail page
- **THEN** it lists the Group's members and every entity whose `owner` is that Group

### Requirement: Login page
An unauthenticated user SHALL be directed to a Login page backed by allauth headless.

#### Scenario: Unauthenticated visit redirects to login
- **WHEN** a user with no session opens any catalog page
- **THEN** they are redirected to the Login page
