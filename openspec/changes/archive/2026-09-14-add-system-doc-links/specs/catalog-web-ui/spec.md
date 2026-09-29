## ADDED Requirements

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
