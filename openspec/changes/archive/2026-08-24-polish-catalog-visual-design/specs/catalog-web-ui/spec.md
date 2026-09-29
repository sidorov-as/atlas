## MODIFIED Requirements

### Requirement: Entity list preview panel
System, Component, Resource, and API list pages SHALL open a right-side preview panel when a row is clicked, showing a summary of that entity with a link-through action to its full detail page, instead of navigating away immediately. The link-through action SHALL be a small icon-button in the panel's header row, next to the entity title, rather than a full-width button.

#### Scenario: Clicking a row opens the preview panel
- **WHEN** a user clicks a row in any of the four entity list pages
- **THEN** a right-side panel opens showing that entity's summary, and the underlying list remains visible

#### Scenario: Preview panel links through to the full detail page
- **WHEN** a user clicks the icon-button next to the entity title in the preview panel's header
- **THEN** they are navigated to that entity's full detail page

#### Scenario: Preview panel can be dismissed without navigating
- **WHEN** a user closes the preview panel (e.g. via a close control)
- **THEN** the panel closes, the user remains on the list page, and no navigation has occurred

### Requirement: Teams (Groups) pages
The Teams list and detail pages SHALL show each Group's members and the entities it owns. The Team detail page SHALL use the same two-column layout as System/Component/Resource/API detail pages: a center column with the (markdown-rendered) description followed by the Members and owned-entity sections, and a right rail listing the Group's `links` as clickable link-outs.

#### Scenario: Team detail shows members and owned entities
- **WHEN** a user opens a Team's detail page
- **THEN** it lists the Group's members and every entity whose `owner` is that Group, in the page's center column

#### Scenario: Team detail renders its description as markdown
- **WHEN** a user opens a Team's detail page and its description contains markdown formatting
- **THEN** the description renders as formatted content (e.g. bold, lists, headings), not raw markdown source

#### Scenario: Team detail shows its links in a right rail
- **WHEN** a user opens a Team's detail page and the Group has one or more configured links
- **THEN** those links appear as clickable link-outs in a right-side rail, matching the Links section shown on other entity detail pages

## ADDED Requirements

### Requirement: Consistent entity table width
Every table rendered via the shared entity table component SHALL fill the full width of its containing column, rather than shrinking to fit its content, so tables in adjacent or stacked sections of the same page render at consistent widths.

#### Scenario: Tables in different sections render at the same width
- **WHEN** a page shows two or more entity tables with different amounts of content (e.g. Team detail's Systems and Components sections)
- **THEN** both tables render at the full width of their containing column, not at a width determined by their own content
