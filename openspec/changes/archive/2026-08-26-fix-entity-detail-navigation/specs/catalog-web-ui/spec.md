## MODIFIED Requirements

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

## ADDED Requirements

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
