# catalog-web-ui Specification

## Purpose
The React (Gravity UI) web frontend for the catalog: list and detail pages for all entity kinds, Teams pages, manual-entity Add/Edit forms with a read-only banner for YAML-managed entities, and the Login page.

## Requirements

### Requirement: Systems list page
The Systems list page SHALL show a filterable, searchable, paginated table (Owner, Tags) with an "Add System" action.

#### Scenario: User filters and searches the list
- **WHEN** a logged-in user opens the Systems list and sets an Owner filter and a search query
- **THEN** the table shows only Systems matching both

### Requirement: Components list page
The Components list page SHALL show a filterable, searchable, paginated table (Owner, Lifecycle, Type, Tags) with an "Add Component" action, independent of any System's detail tabs.

#### Scenario: User filters and searches the list
- **WHEN** a logged-in user opens the Components list and sets an Owner filter and a search query
- **THEN** the table shows only Components matching both, regardless of which System they belong to

### Requirement: Resources list page
The Resources list page SHALL show a filterable, searchable, paginated table (Owner, Type, Tags) with an "Add Resource" action, independent of any System's detail tabs.

#### Scenario: User filters and searches the list
- **WHEN** a logged-in user opens the Resources list and sets an Owner filter and a search query
- **THEN** the table shows only Resources matching both, regardless of which System they belong to

### Requirement: APIs list page
The APIs list page SHALL show a filterable, searchable, paginated table (Owner, Type, Tags) with an "Add API" action, independent of any System's detail tabs.

#### Scenario: User filters and searches the list
- **WHEN** a logged-in user opens the APIs list and sets an Owner filter and a search query
- **THEN** the table shows only APIs matching both, regardless of which System they belong to

### Requirement: Entity detail pages
System, Component, Resource, and API SHALL each have a detail page with an Overview and Relations view; System and Component detail pages SHALL additionally show their C4 Diagram tab and (for System) Components/Resources/APIs/Docs tabs. System and Component C4 Diagram tabs SHALL render their diagram in a full-width viewer outside the normal right-rail layout. Overview SHALL render the entity's Markdown `documentation`, while its short `description` remains in the page header. An API with stored specification content SHALL additionally show a `Specification` tab containing the specification download action before its viewer or fallback state; an OpenAPI or AsyncAPI API SHALL render the matching viewer below that action, and a gRPC or GraphQL API SHALL show an unsupported-viewer message below it.

#### Scenario: System detail shows its tabs
- **WHEN** a user opens a System's detail page
- **THEN** it shows Overview, Components, Resources, APIs, Docs, Relations, and C4 Diagram tabs

#### Scenario: Component detail shows its tabs
- **WHEN** a user opens a Component's detail page
- **THEN** it shows Overview, Relations, and C4 Diagram (component view) tabs, but no Components/Resources/APIs/Docs tabs

#### Scenario: Resource detail shows only Overview and Relations
- **WHEN** a user opens a Resource's detail page
- **THEN** it shows only Overview and Relations tabs, with no C4 Diagram tab

#### Scenario: API detail shows Overview, Relations, and Specification for stored content
- **WHEN** a user opens an API with stored specification content
- **THEN** it shows Overview, Relations, and a Specification tab, with no C4 Diagram tab

#### Scenario: API Specification places download before viewer
- **WHEN** a user opens the Specification tab of an OpenAPI or AsyncAPI API with stored specification content
- **THEN** the download action appears before the matching specification viewer

#### Scenario: Unsupported API viewer preserves specification download
- **WHEN** a user opens the Specification tab of a gRPC or GraphQL API with stored specification content
- **THEN** the tab shows the download action and an explicit message that no embedded viewer is available

#### Scenario: C4 Diagram uses full available page width
- **WHEN** a user opens the C4 Diagram tab for a System or Component
- **THEN** the viewer occupies the detail page width that would otherwise be divided between the content column and right rail

### Requirement: Add/Edit forms for manual entities only
A manual entity's detail page SHALL show Add/Edit affordances; a YAML-managed entity's detail page SHALL show a read-only banner naming the backing repository instead. The add/edit forms for manual System, Component, Resource, and API entities SHALL place their Save/Cancel actions in a header row (title left, actions right) matching the action-row layout of that entity's own detail page. System and Resource forms SHALL keep a single-column body with the Markdown Documentation editor after their standard and kind-specific fields. Component and API forms SHALL split their body into an Overview tab (standard and kind-specific fields) and a Documentation tab (the Markdown editor alone, not width-constrained by the fields column).

#### Scenario: YAML-managed entity shows a banner, not an Edit button
- **WHEN** a user opens the detail page of an entity ingested from `org/repo`
- **THEN** the page shows "managed by `catalog-info.yaml` in `org/repo`" instead of an Edit button

#### Scenario: Add/Edit form actions sit in a top header row
- **WHEN** a user opens the create or edit form for a manual System, Component, Resource, or API
- **THEN** Save (or Create) and Cancel render in a header row above the form body, title on the left and the buttons on the right, matching the action-row layout used by that entity kind's own detail page

#### Scenario: System and Resource forms keep Documentation after their fields
- **WHEN** a user opens the create or edit form for a manual System or Resource
- **THEN** the Markdown Documentation editor follows its standard and kind-specific fields in the same single-column body, with no separate tab

#### Scenario: Component and API forms separate fields from Documentation
- **WHEN** a user opens the create or edit form for a manual Component or API
- **THEN** its Name, Title, Description, Tags, and kind-specific fields render under an Overview tab, and the Markdown Documentation editor renders alone under a separate Documentation tab that is not constrained to the fields column's width

### Requirement: Blocked-by-conflict banner
An entity's detail page SHALL show a banner naming the repository that could not claim it when the entity is currently blocking that repository's YAML claim. This banner is visually distinct from the existing read-only "managed by `catalog-info.yaml` in `org/repo`" banner (`bootstrap-catalog-service`'s `catalog-web-ui` capability): the read-only banner is informational (this entity is YAML-managed), while the blocked-by-conflict banner is a warning that names an action the viewer can take (adopt the entity to resolve the conflict, if they're a member of its owner Group).

#### Scenario: Blocked entity shows a distinct warning banner
- **WHEN** a user opens the detail page of a manual entity that is currently blocking a YAML claim from repository `org/repo`
- **THEN** the page shows a warning-styled banner naming `org/repo`, distinct in style from the informational read-only banner shown on YAML-managed entities

#### Scenario: Entity with no active conflict shows neither banner
- **WHEN** a user opens the detail page of a manual entity with no active conflict
- **THEN** neither the blocked-by-conflict banner nor the read-only banner is shown, and Add/Edit affordances are available as usual

### Requirement: Teams (Groups) pages
The Teams list and detail pages SHALL show each Group's members and the entities it owns. The Team detail page SHALL use the same shared detail-page chrome as System/Component/Resource/API detail pages (breadcrumb, header, tab bar, right rail), with Overview, Members, Systems, Components, Resources, and APIs tabs. The Overview tab SHALL show the (markdown-rendered) description. The right rail SHALL list the Group's `links` as clickable link-outs, matching the Links section shown on other entity detail pages. The Systems/Components/Resources/APIs tabs SHALL be paginated the same way as the top-level entity list pages.

#### Scenario: Team detail shows its tabs
- **WHEN** a user opens a Team's detail page
- **THEN** it shows Overview, Members, Systems, Components, Resources, and APIs tabs

#### Scenario: Team detail's Overview tab renders its description as markdown
- **WHEN** a user opens a Team's Overview tab and the Group's description contains markdown formatting
- **THEN** the description renders as formatted content (e.g. bold, lists, headings), not raw markdown source

#### Scenario: Team detail's Members tab lists the Group's members
- **WHEN** a user opens a Team's Members tab
- **THEN** it lists every member of that Group

#### Scenario: Team detail's owned-entity tabs list owned entities
- **WHEN** a user opens a Team's Systems, Components, Resources, or APIs tab
- **THEN** that tab lists every entity of that kind whose `owner` is that Group

#### Scenario: Team detail shows its links in a right rail
- **WHEN** a user opens a Team's detail page and the Group has one or more configured links
- **THEN** those links appear as clickable link-outs in a right-side rail, matching the Links section shown on other entity detail pages

#### Scenario: Team's owned-entity tables are paginated
- **WHEN** a Team owns more entities of one kind (e.g. Components) than fit on one page
- **THEN** that tab's table shows pagination controls, matching the top-level Components list page

### Requirement: Related-entity table row navigation on detail pages
Every related-entity table shown within a detail page's tabs (a System's Components/Resources/APIs tabs, a Team's Systems/Components/Resources/APIs tabs) SHALL navigate to a row's full detail page on a fast second click on that row, using the same click-timing behavior already used by the top-level entity list pages.

#### Scenario: Double-clicking a row in a System's related-entity tab navigates to it
- **WHEN** a user clicks a row in a System's Components, Resources, or APIs tab, then clicks that same row again within the double-click window
- **THEN** they are navigated to that entity's full detail page

#### Scenario: Double-clicking a row in a Team's owned-entity tab navigates to it
- **WHEN** a user clicks a row in a Team's Systems, Components, Resources, or APIs tab, then clicks that same row again within the double-click window
- **THEN** they are navigated to that entity's full detail page

#### Scenario: A single click does not navigate away
- **WHEN** a user clicks a row in a related-entity table once
- **THEN** they remain on the current detail page; no navigation occurs

### Requirement: Relations tab rows link to their target entity
Each row of an entity's Relations tab (System/Component/Resource/API) SHALL link to the target entity's detail page, using the target's kind and id returned by the relations endpoint.

#### Scenario: Clicking a Relations tab row navigates to its target
- **WHEN** a user clicks a row in an entity's Relations tab
- **THEN** they are navigated to the detail page of the entity named in that row's Target column

### Requirement: Diagram viewer provides viewport controls, settings, and download
The System and Component C4 Diagram viewer SHALL provide pointer pan, Zoom in,
Zoom out, Fit to viewport, an image download action, and a lower-left Gear
settings control. The settings control SHALL let the user set the active C4
rendering preferences and SHALL not overlap the upper-right viewport controls.
The viewer SHALL show loading and rendering-failure states without leaving a
broken image element, and SHALL automatically fit a loaded image when its
viewport size changes.

#### Scenario: User fits a zoomed diagram
- **WHEN** a user changes the diagram scale and activates Fit to viewport
- **THEN** the diagram returns to a scale and position that fits its viewer bounds

#### Scenario: User downloads the visible diagram format
- **WHEN** a user activates the diagram download action
- **THEN** the browser requests the same diagram endpoint with download enabled and receives an image attachment

#### Scenario: User opens diagram settings
- **WHEN** a loaded C4 diagram user activates the lower-left Gear control
- **THEN** the viewer presents layout and display-preference controls while
  preserving access to pan, zoom, fit, and download actions

#### Scenario: A hidden tab becomes visible
- **WHEN** a loaded C4 diagram is shown after its viewer bounds changed while
  the tab was hidden
- **THEN** the image is fitted to the available viewer bounds automatically

### Requirement: Relations tab manages declared architecture relationships separately
The Relations tab SHALL show derived Catalog relations and declared Architecture Relationships in separate labeled sections. Its Architecture Relationships section SHALL show every declared relationship for which the current entity is either source or target, preserving the canonical directed source and target. A manual entity's Architecture Relationships section SHALL provide create, edit, and delete controls only for outgoing manual relationships whose source is that entity; YAML-origin relationships and incoming relationships SHALL be visibly read-only.

#### Scenario: Manual entity adds an outgoing architecture relationship
- **WHEN** a user with edit access opens a manual Component's Relations tab and creates an outgoing Architecture Relationship
- **THEN** the relationship appears in the Architecture Relationships section without changing the Catalog relations section

#### Scenario: Target entity sees an incoming architecture relationship
- **WHEN** a Component is the target of an Architecture Relationship from another Component
- **THEN** its Relations tab displays the relationship with its source and target direction and no edit or delete control

#### Scenario: YAML relationship is displayed as read-only
- **WHEN** a user views a YAML-managed entity's Architecture Relationships section
- **THEN** declared relationships are visible with their source, target, label, technology, interaction kind, and origin but no edit or delete control

### Requirement: Component's Provides/Consumes API links
A Component's detail page SHALL render each entry in its Provides API and Consumes API sections as a link to that API's detail page, instead of plain unlinkable text.

#### Scenario: Clicking a Provides API entry navigates to that API
- **WHEN** a user clicks an API listed under a Component's Provides API section
- **THEN** they are navigated to that API's detail page

#### Scenario: Clicking a Consumes API entry navigates to that API
- **WHEN** a user clicks an API listed under a Component's Consumes API section
- **THEN** they are navigated to that API's detail page

### Requirement: Entity detail page rail links to Owner/System
Each System/Component/Resource/API detail page's right-rail Owner field, and System field where the kind has one, SHALL link to that entity's detail page, using the id returned by the entity response. A Resource with no System SHALL continue to show a plain dash, not a link.

#### Scenario: Clicking rail Owner link navigates to the owning Team
- **WHEN** a user clicks the Owner field in a System/Component/Resource/API detail page's rail
- **THEN** they are navigated to that Group's Team detail page

#### Scenario: Clicking rail System link navigates to the System
- **WHEN** a user clicks the System field in a Component/Resource/API detail page's rail
- **THEN** they are navigated to that System's detail page

#### Scenario: Resource with no System shows a plain dash
- **WHEN** a Resource has no `system` set
- **THEN** its rail's System field renders as a plain dash, not a link

### Requirement: Login page
An unauthenticated user SHALL be directed to a Login page backed by allauth headless. The credential-provider submit control's accessible name SHALL reflect whether the deployment offers exactly one credential provider (`Sign in`) or more than one (`Sign in with {provider.displayName}`).

#### Scenario: Unauthenticated visit redirects to login
- **WHEN** a user with no session opens any catalog page
- **THEN** they are redirected to the Login page

#### Scenario: Single local credential provider submit button
- **WHEN** a deployment offers exactly one credential provider and a user submits the login form
- **THEN** the submit control's accessible name is `Sign in`

### Requirement: Entity list preview panel
System, Component, Resource, API, and Team list pages SHALL render their heading and description before a shared table-and-preview content row. A right-side preview panel SHALL open when a row is clicked, showing a summary of that entity with a link-through action to its full detail page, instead of navigating away immediately. The link-through action SHALL be a small icon-button in the panel's header row, next to the entity title, rather than a full-width button. A second, fast click on a row that is already open in the preview panel SHALL additionally navigate to that entity's full detail page, without introducing any delay to the panel opening on the first click of any row.

#### Scenario: Clicking a row opens a table-aligned preview panel
- **WHEN** a user clicks a row in any of the five entity list pages (Systems, Components, Resources, APIs, Teams)
- **THEN** a right-side panel opens beside the table content, below the page heading and description, while the underlying list remains visible

#### Scenario: Preview panel links through to the full detail page
- **WHEN** a user clicks the icon-button next to the entity title in the preview panel's header
- **THEN** they are navigated to that entity's full detail page

#### Scenario: Preview panel can be dismissed without navigating
- **WHEN** a user closes the preview panel (e.g. via a close control)
- **THEN** the panel closes, the user remains on the list page, and no navigation has occurred

#### Scenario: A fast second click on the open row navigates to its detail page
- **WHEN** a user clicks a row, the preview panel opens for it, and the user clicks that same row again within the double-click window
- **THEN** they are navigated to that entity's full detail page

#### Scenario: The first click on any row is never delayed
- **WHEN** a user clicks a row for the first time
- **THEN** the preview panel opens immediately, with no debounce or waiting period to see whether a second click follows

### Requirement: Branded, collapsible navigation shell
The application SHALL show a sidebar with the Atlas logo and wordmark, an icon per navigation item, a collapse/expand control, and a Settings entry, on every authenticated page.

#### Scenario: Sidebar can be collapsed and expanded
- **WHEN** a user toggles the sidebar's collapse control
- **THEN** the sidebar collapses to icons-only, or expands back to icons and labels, consistently across all authenticated pages

#### Scenario: Settings entry is present
- **WHEN** a user views the sidebar
- **THEN** a "Settings" navigation entry is present alongside Systems/Components/Resources/APIs/Teams

### Requirement: Consistent entity table width
Every table rendered via the shared entity table component SHALL be capped at a maximum width, shrinking to fit its container when narrower than that cap, rather than always stretching to fill the full width of its containing column.

#### Scenario: A table narrower than the cap fits its column
- **WHEN** a table's containing column is narrower than the configured maximum width
- **THEN** the table renders at the column's width, same as before

#### Scenario: A table in a wide column does not exceed the cap
- **WHEN** a table's containing column is wider than the configured maximum width (e.g. on a wide viewport with no preview panel open)
- **THEN** the table renders at the maximum width, not the full column width

### Requirement: Colored Type and Lifecycle badges
Every entity table SHALL render a Component's, Resource's, or API's `type`, and a Component's `lifecycle`, as a colored badge rather than plain text, using a fixed color per value. Lifecycle badges SHALL use traffic-light semantics: `production` renders as a success (green) badge, `experimental` as a warning (yellow) badge, and `deprecated` as an unknown (gray) badge. Systems have no `type` or `lifecycle` field and are unaffected. Resources and APIs have a `type` but no `lifecycle`.

#### Scenario: Component's type and lifecycle render as colored badges
- **WHEN** a user views the Components list table
- **THEN** each row's Type and Lifecycle values render as colored badges, not plain text

#### Scenario: Production lifecycle renders as a success badge
- **WHEN** a Component's lifecycle is `production`
- **THEN** its Lifecycle badge renders with the success (green) color

#### Scenario: Experimental lifecycle renders as a warning badge
- **WHEN** a Component's lifecycle is `experimental`
- **THEN** its Lifecycle badge renders with the warning (yellow) color

#### Scenario: Deprecated lifecycle renders as an unknown badge
- **WHEN** a Component's lifecycle is `deprecated`
- **THEN** its Lifecycle badge renders with the unknown (gray) color

#### Scenario: Resource's and API's type render as colored badges
- **WHEN** a user views the Resources or APIs list table
- **THEN** each row's Type value renders as a colored badge, not plain text

### Requirement: Tag column and tag filtering in entity tables
Every table rendered via the shared entity table component (the four entity list pages and the Team/System owned-entity sub-tables) SHALL show each row's tags as colored Labels in a Tags column, matching how tags render on the entity's detail page. Each such table SHALL offer a multi-select tag filter that narrows the table to entities carrying **any** of the selected tags.

#### Scenario: Entity table shows a Tags column
- **WHEN** a user views any entity list table for an entity that has one or more tags
- **THEN** those tags render as colored Labels in a Tags column, using the same colors as the entity's detail page

#### Scenario: Filtering by multiple tags matches any of them
- **WHEN** a user selects two tags in a table's tag filter
- **THEN** the table shows entities carrying at least one of the selected tags, not only entities carrying both

#### Scenario: Owned-entity tables also support tag filtering
- **WHEN** a user views a Team's or System's owned-entity table
- **THEN** the same Tags column and multi-select tag filter are available as on the top-level list pages

### Requirement: Entity table pagination
Every table rendered via the shared entity table component SHALL show pagination controls (previous/next, numbered pages, a jump-to-page input, and an items-per-page selector) when its result set spans more than one page. Changing any filter (search, Owner, Type, Lifecycle, or Tags) SHALL reset the table back to its first page.

#### Scenario: Table shows pagination controls
- **WHEN** a table's filtered result set contains more items than the current page size
- **THEN** the table shows pagination controls below its rows, including numbered pages and an items-per-page selector

#### Scenario: Changing the page size updates the visible rows
- **WHEN** a user changes the items-per-page selector
- **THEN** the table re-renders with the new number of rows per page, starting from page 1

#### Scenario: Changing a filter returns to the first page
- **WHEN** a user is viewing page 3 of a table and changes the search query or any filter
- **THEN** the table returns to page 1 showing results for the new filter

### Requirement: Row-level Edit and Remove actions
Every row in the Systems, Components, Resources, APIs, and Teams list tables SHALL offer a context-actions control with exactly two entries: Edit and Remove. For Systems, Components, Resources, and APIs, this control SHALL be omitted entirely on rows for YAML-managed (non-manual) entities, matching the same manual/YAML-managed distinction already used to show or hide Add/Edit affordances on those entities' detail pages. Team rows SHALL always show the control, since Teams cannot be YAML-managed.

#### Scenario: Manual entity row shows Edit and Remove
- **WHEN** a user views a list row for a manually-managed System, Component, Resource, or API
- **THEN** its context-actions control offers exactly two entries: Edit and Remove

#### Scenario: YAML-managed entity row shows no actions control
- **WHEN** a user views a list row for a System, Component, Resource, or API ingested from a YAML source
- **THEN** no context-actions control is shown for that row

#### Scenario: Team row always shows Edit and Remove
- **WHEN** a user views a row in the Teams list table
- **THEN** its context-actions control offers exactly two entries: Edit and Remove, regardless of that Team's origin

#### Scenario: Activating a row action does not also open the preview panel
- **WHEN** a user clicks Edit or Remove in a row's context-actions control
- **THEN** only that action's handler runs; the row's preview-panel-opening click behavior does not also fire

### Requirement: System detail distinguishes Context and System Architecture views
The System detail page SHALL expose separately named C4 System Context and System Architecture tabs, each rendered full width through the reusable diagram viewer.

#### Scenario: User opens System Architecture
- **WHEN** a user selects the System Architecture tab for a System
- **THEN** the viewer requests that System's `architecture` diagram endpoint rather than its context endpoint

### Requirement: Architecture Relationship target selection is searchable and typed
The create and edit form for an outgoing manual Architecture Relationship SHALL provide a searchable target-ref lookup limited to System, Component, API, Resource, User, and Group catalog records. It SHALL submit the selected canonical ref and display the target kind to the user.

#### Scenario: User selects an actor target
- **WHEN** an editor searches for a catalog User in the target lookup and selects it
- **THEN** the form submits that User's canonical ref as the Architecture Relationship target

### Requirement: Borderless entity table framing
Every table rendered via the shared entity table component SHALL render without a border or rounded-corner frame around the table itself. Where a page shows more than one such table in the same column (e.g. a Team's owned-entity sections), the tables SHALL be visually separated by spacing and their existing section subheadings, not by a card boundary around each table.

#### Scenario: A single table has no border or rounded corners
- **WHEN** a user views any entity list, detail-page sub-table, or reference table in the catalog
- **THEN** no border or rounded-corner frame is drawn around the table

#### Scenario: Stacked tables on the same page are separated by spacing, not boxes
- **WHEN** a page shows multiple tables in the same column, one after another
- **THEN** each is preceded by its own section subheading and separated by spacing from the one before it, with no card boundary drawn around any individual table

### Requirement: System Docs tab browses document links
The System Docs tab SHALL obtain links from the System document-links API and
render a searchable, paginated table with Title, Description, and Link
columns. Link SHALL contain icon-only external-open and copy actions; external
open SHALL use safe new-tab attributes, and copy SHALL use `Copy` then show
`CopyCheck` after success or visible failure feedback. Each row SHALL expose
Edit and Remove through `g-table__actions`.

A manual System SHALL show an Add button beside `Search documentation`; it
opens a modal for title, description, URL, and type. The same modal SHALL edit
an existing row. Add, edit, and remove SHALL submit the complete ordered
`metadata.links` array through the System PATCH API, require a URL, and reject
duplicate URLs. A YAML-managed System SHALL expose no add, edit, or remove
controls. The System create/edit form SHALL not expose a document-link editor.
An empty result without an active search SHALL display `No docs linked`.

#### Scenario: User searches and pages through documentation
- **WHEN** a user enters text in the Docs search field and selects a later
  result page
- **THEN** the table shows the matching links for that page and the search and
  page state are represented in the URL

#### Scenario: Manual owner manages document links from Docs
- **WHEN** an authorized owner adds, edits, or removes a document link in the
  Docs tab
- **THEN** the System PATCH request contains the resulting complete ordered
  link list and the table reloads with that result

#### Scenario: YAML-managed System has no Docs mutation controls
- **WHEN** a user opens a YAML-managed System Docs tab
- **THEN** the read-only source banner is shown and no Add, Edit, or Remove
  controls are available

### Requirement: Systems preview panel includes a bounded documentation section
When a System row is selected on `/systems`, its preview panel SHALL request
and display at most the first five document links in a Documentation section.
The section SHALL not render for a System with no links. When additional links
exist, the panel SHALL show `More (count)` that opens the selected System's
Docs tab.

#### Scenario: Preview shows a bounded link list
- **WHEN** a selected System has seven document links
- **THEN** its preview lists five links and shows `More (7)`

#### Scenario: Preview More opens full Docs
- **WHEN** a user activates `More (7)` in a System preview
- **THEN** they navigate to that System's detail page with its Docs tab active

### Requirement: Write affordances are hidden for a read-only session
When the current session is flagged read-only (`/api/me/`'s `isReadOnly`), the frontend SHALL hide every write affordance this capability otherwise shows to an authenticated user, on top of (not instead of) the existing manual/YAML-managed distinction: the "Add <Kind>" action on the Systems, Components, Resources, and APIs list pages; the write entries in row-level context menus on the Systems, Components, Resources, APIs, and Teams list tables; the Edit/Remove/Revive/Purge action row on every entity detail page; and the Add/Edit forms themselves, whose routes SHALL redirect away a read-only session that navigates to them directly, the same "UI guard, not the security boundary" way `AdminProtected` already redirects a non-admin away from `/settings/*`. This is a UX affordance only — the backend write-permission check (catalog-auth spec's read-only override) remains the actual boundary regardless of what the frontend shows.

#### Scenario: Read-only session sees no Add action
- **WHEN** a read-only session opens the Systems, Components, Resources, or APIs list page
- **THEN** the "Add <Kind>" action is not shown

#### Scenario: Read-only session sees no row-level actions control
- **WHEN** a read-only session views a row on the Systems, Components, Resources, APIs, or Teams list table
- **THEN** no write action is shown for that row; menus containing permitted read/export/navigation actions retain those entries, regardless of manual/YAML-managed origin

#### Scenario: Read-only session sees no detail-page write actions
- **WHEN** a read-only session opens the detail page of any entity
- **THEN** no Edit, Remove, Revive, or Purge action is shown

#### Scenario: Read-only session is redirected away from a create or edit URL
- **WHEN** a read-only session navigates directly to a create or edit form URL for any entity kind
- **THEN** they are redirected away without seeing the form

#### Scenario: UI gating is not the security boundary
- **WHEN** a read-only session's client calls a write endpoint directly, bypassing the UI
- **THEN** the backend rejects the request regardless of what the frontend would have shown

#### Scenario: Non-read-only session is unaffected
- **WHEN** an authenticated session that is not flagged read-only opens any list or detail page
- **THEN** every write affordance this capability already defines renders exactly as it does today

### Requirement: Account access presentation refreshes safely
The current-user endpoint SHALL expose isReadOnly from current persisted state. The frontend SHALL refresh access state on session initialization/login, focus or visibility return, entry to a mutation route, and after a write-denied response. While required access state is unknown or failed to load, write controls/forms SHALL not be presented as authorized. Stale UI SHALL not defeat backend denial; no real-time push requirement is introduced.

#### Scenario: Open form becomes read-only
- **WHEN** an operator flags the account while its form is already open and submission is denied
- **THEN** the frontend refreshes access state, reports the denial, and prevents continued writable interaction without falsely claiming the submission succeeded

#### Scenario: Write route is loading access state
- **WHEN** the current access state has not loaded successfully
- **THEN** the mutation form is not rendered as available

### Requirement: Administrative and custom mutation controls obey read-only
All installed core/plugin write controls and pure mutation routes SHALL obey isReadOnly, including relationship editors, System Docs document-link authoring, tags, configuration/settings, and user-triggered mutation jobs. Mixed read/write pages SHALL preserve allowed read content while hiding mutation controls. Pure mutation routes SHALL redirect to a safe read destination. This SHALL apply even when isAdmin is true and SHALL not alter per-entity YAML provenance rules.

#### Scenario: Read-only administrator opens settings
- **WHEN** a read-only account with ordinary permission to view settings opens a mixed settings page
- **THEN** permitted read content remains visible but editing, saving, and mutation-trigger controls are absent

#### Scenario: Menu contains read and write actions
- **WHEN** a read-only user opens an action menu with navigation/export and mutation entries
- **THEN** permitted read actions remain and mutation entries are hidden

#### Scenario: Read-only user opens a manually managed System's Docs tab
- **WHEN** a read-only user opens the Docs tab for a System that would otherwise allow document-link authoring
- **THEN** document links, search, pagination, opening links, and copying URLs remain available
- **AND** the Add, edit, remove, and document-link authoring dialog controls are absent
