## MODIFIED Requirements

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

### Requirement: Teams (Groups) pages
The Teams list and detail pages SHALL show each Group's members and the entities it owns. The Team detail page SHALL use the same two-column layout as System/Component/Resource/API detail pages: a center column with the (markdown-rendered) description followed by the Members and owned-entity sections, and a right rail listing the Group's `links` as clickable link-outs. The owned-entity sections (Systems/Components/Resources/APIs) SHALL be paginated the same way as the top-level entity list pages.

#### Scenario: Team detail shows members and owned entities
- **WHEN** a user opens a Team's detail page
- **THEN** it lists the Group's members and every entity whose `owner` is that Group, in the page's center column

#### Scenario: Team detail renders its description as markdown
- **WHEN** a user opens a Team's detail page and its description contains markdown formatting
- **THEN** the description renders as formatted content (e.g. bold, lists, headings), not raw markdown source

#### Scenario: Team detail shows its links in a right rail
- **WHEN** a user opens a Team's detail page and the Group has one or more configured links
- **THEN** those links appear as clickable link-outs in a right-side rail, matching the Links section shown on other entity detail pages

#### Scenario: Team's owned-entity tables are paginated
- **WHEN** a Team owns more entities of one kind (e.g. Components) than fit on one page
- **THEN** that section's table shows pagination controls, matching the top-level Components list page

## ADDED Requirements

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
