## MODIFIED Requirements

### Requirement: System Map is a dedicated nav destination
The `atlas.c4` plugin SHALL contribute its own "System Map" route and navigation item, rather than a homepage widget. The System Map page SHALL contain two tabs: Landscape, which renders the catalog-wide System Landscape diagram, and Views, which lists saved views and leads to their detail and editor pages. Landscape SHALL be the tab shown by default. When the catalog has zero System entities, the Landscape tab SHALL show an empty-state message instead of attempting to render the diagram.

#### Scenario: System Map renders the landscape diagram
- **WHEN** a logged-in user with `atlas.c4` installed opens the "System Map" nav item
- **THEN** the Landscape tab is shown with the System Landscape diagram and its pan, zoom, fit-to-viewport, SVG download, and PNG download controls

#### Scenario: System Map shows an empty state with no Systems
- **WHEN** a logged-in user opens "System Map" and the catalog has zero System entities
- **THEN** the Landscape tab shows a message explaining that System Map appears once the catalog has systems, instead of rendering a diagram

#### Scenario: System Map renders systems with no relationships
- **WHEN** the catalog has at least one System entity but no authored Architecture Relationships
- **THEN** the Landscape tab renders the diagram showing each System as an unconnected node, not the empty state

#### Scenario: Views is a second tab
- **WHEN** a logged-in user opens "System Map"
- **THEN** a Views tab is available next to Landscape, and selecting it shows the saved views list without changing the Landscape diagram or its controls

#### Scenario: A Views link opens the Views tab
- **WHEN** a user opens a System Map URL that identifies the Views tab
- **THEN** the page opens on the Views tab instead of Landscape

#### Scenario: Navigation item stays active on view pages
- **WHEN** a user is on a view detail or editor page
- **THEN** the System Map navigation item is shown as active
