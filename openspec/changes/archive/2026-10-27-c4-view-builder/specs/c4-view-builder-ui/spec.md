## ADDED Requirements

### Requirement: System Map has a Views tab with a paginated list of saved views
The System Map page SHALL provide a Views tab next to the Landscape tab. The tab SHALL follow the Flows list: a search bar above a paginated table with Name and Description columns, sortable by name in either direction (ascending by default). Selecting a row SHALL open the view detail page. For users who can write, the tab SHALL provide a Create view action and each row SHALL have Edit and Delete actions; Delete SHALL ask for confirmation. An empty list SHALL show a message explaining that no views exist yet.

#### Scenario: Opening the Views tab
- **WHEN** a user selects the Views tab
- **THEN** the page shows the first page of saved views with their name and description

#### Scenario: Pagination
- **WHEN** more views exist than fit on one page
- **THEN** the list offers paging controls and shows the requested page

#### Scenario: Search by name
- **WHEN** the user types in the search bar
- **THEN** the list returns to the first page and shows only views whose name matches

#### Scenario: Sort by name
- **WHEN** the user sorts the Name column descending
- **THEN** the list shows views in reverse name order starting from the first page

#### Scenario: Row actions
- **WHEN** a user who can write views the list
- **THEN** each row offers Edit, which opens the editor, and Delete

#### Scenario: Delete from the list
- **WHEN** the user presses Delete on a row and confirms
- **THEN** the view is deleted and the list refreshes without it

#### Scenario: Delete from the list can be cancelled
- **WHEN** the user presses Delete on a row and cancels the confirmation
- **THEN** the view is not deleted

#### Scenario: Empty list
- **WHEN** no views exist
- **THEN** the tab shows an empty-state message and, for users who can write, the Create view action

#### Scenario: Write actions are hidden without write access
- **WHEN** a read-only user opens the Views tab
- **THEN** the Create view action and the row Edit and Delete actions are not shown

### Requirement: View detail shows the diagram with Edit and Delete
The view detail page at `/system-map/views/:id` SHALL show the view name, its description when present, and its diagram in the existing diagram viewer with pan, zoom, fit to viewport, SVG export, PNG export, and viewer rendering preferences. Edit and Delete actions SHALL be available to users who can write. Delete SHALL ask for confirmation and, once confirmed, return to the Views list. Heading, legend, and exports SHALL refer to the saved view.

#### Scenario: Opening a view
- **WHEN** a user opens a saved view
- **THEN** the page shows its name, description, and rendered diagram

#### Scenario: Edit opens the editor
- **WHEN** a user presses Edit
- **THEN** the editor opens for that view with its saved values

#### Scenario: Delete asks for confirmation
- **WHEN** a user presses Delete and confirms
- **THEN** the view is deleted and the Views list is shown without it

#### Scenario: Delete can be cancelled
- **WHEN** a user presses Delete and cancels the confirmation
- **THEN** the view is not deleted

#### Scenario: Unknown view
- **WHEN** a user opens a view id that does not exist
- **THEN** the page shows a not-found message with a link back to the Views list

#### Scenario: Missing entity warning
- **WHEN** a saved view references an entity that no longer exists
- **THEN** the page does not show a partial diagram, names the missing entity, and links to Edit

#### Scenario: Write actions hidden without write access
- **WHEN** a read-only user opens a view
- **THEN** Edit and Delete are not shown

### Requirement: View editor has a collapsible settings panel on the right
The editor at `/system-map/views/new` and `/system-map/views/:id/edit` SHALL show the diagram preview with the View settings panel on the right of it. The panel SHALL be open by default and SHALL be collapsible with the same kind of toggle control as the flow editor; when collapsed, the preview SHALL use the freed width. On narrow screens the panel SHALL sit above the preview, and no control SHALL cause horizontal page scroll. Name (required) and description (optional) SHALL be edited at the top of the panel. **Save** SHALL store the view and open its detail page. A duplicate name reported by the server SHALL be shown on the Name field. Leaving the editor with unsaved changes SHALL ask for confirmation. Create and Edit SHALL be unavailable to users who cannot write.

#### Scenario: Panel is open by default
- **WHEN** a user opens the editor
- **THEN** the View settings panel is shown on the right of the preview

#### Scenario: Collapse and expand
- **WHEN** the user presses the panel toggle
- **THEN** the panel collapses, the preview uses the freed width, and the toggle expands it again

#### Scenario: Narrow viewport layout
- **WHEN** the viewport is too narrow for side-by-side panels
- **THEN** the panel is shown above the preview and the page does not scroll horizontally

#### Scenario: Saving a new view
- **WHEN** the user enters a name, builds a valid selection, and presses Save
- **THEN** the view is stored and its detail page opens

#### Scenario: Saving changes to an existing view
- **WHEN** the user edits a view and presses Save
- **THEN** the stored view is updated and its detail page opens

#### Scenario: Duplicate name
- **WHEN** the user saves a name that another view already uses, ignoring case
- **THEN** the error is shown on the Name field and the editor stays open

#### Scenario: Name is required
- **WHEN** the Name field is empty
- **THEN** Save is disabled or reports that the name is required

#### Scenario: Leaving with unsaved changes
- **WHEN** the user has unsaved changes and tries to leave the editor
- **THEN** the page asks for confirmation before discarding them

#### Scenario: Write routes need write access
- **WHEN** a read-only user opens the editor URL
- **THEN** the editor is not shown

### Requirement: View settings expose level, selection, entity types, and relationships
The View settings panel SHALL provide: a Level switch (Systems or Components); a Selection dropdown (Selected entities only or Neighborhood); an entity multi-select; for Neighborhood mode, depth as a positive integer with an Unlimited option and a relationship direction (Both, Outgoing, Incoming); entity-type checkboxes; and a Relationships dropdown (Declared only or Declared plus derived). The entity-type checkboxes SHALL be Components, Resources, APIs, and Actors at the Components level, and Actors only at the Systems level. The panel SHALL NOT provide a layout control, curve selection, or Merge or Simplified options. Layout and other display options SHALL come from the existing diagram viewer preferences.

#### Scenario: Initial draft of a new view
- **WHEN** a user opens the editor for a new view without a prefill
- **THEN** the draft is the Systems level, Selected entities only mode, declared only relationships, and no entities, and the preview shows an instruction to select entities

#### Scenario: Neighborhood controls appear only in Neighborhood mode
- **WHEN** the user switches Selection to Neighborhood
- **THEN** the panel shows root entities, depth with Unlimited, and relationship direction, and in Selected entities only mode it does not

#### Scenario: Systems level shows only the Actors type
- **WHEN** the Level is Systems
- **THEN** the entity-type block contains only the Actors checkbox

#### Scenario: Switching Selection keeps the chosen entities
- **WHEN** the user switches between Selected entities only and Neighborhood
- **THEN** the chosen entities remain, serving as the full set in one mode and as roots in the other

#### Scenario: Unlimited depth disables the number field
- **WHEN** the user enables Unlimited
- **THEN** the numeric depth field is disabled

### Requirement: Level changes clear incompatible selections
Changing the Level SHALL remove from the draft every selected entity that is not selectable at the new level and SHALL show the notice "Selection cleared for the new level" when any entity was removed. The currently applied preview SHALL remain displayed until the next Apply.

#### Scenario: Switching from Components to Systems clears Components
- **WHEN** the draft contains Components and the user switches the Level to Systems
- **THEN** the Components are removed, the notice is shown, and the previously applied preview stays visible

### Requirement: Entity-type checkboxes constrain neighbors and selection
In Neighborhood mode the entity-type checkboxes SHALL restrict which types are added as neighbors, and explicitly chosen roots SHALL stay visible regardless. In Selected entities only mode the checkboxes SHALL restrict which types can be chosen; disabling a type that already has chosen entities SHALL be blocked with the hint "Remove selected entities of this type first".

#### Scenario: Disabling a type with chosen entities is blocked
- **WHEN** Selected entities only mode contains a chosen Resource and the user tries to uncheck Resources
- **THEN** the checkbox stays checked and the hint is shown

#### Scenario: Unchecking a type in Neighborhood mode
- **WHEN** the user unchecks APIs in Neighborhood mode
- **THEN** APIs are not added as neighbors after the next Apply, while a chosen API root remains visible

### Requirement: Entity picker searches within the selected level
The entity multi-select SHALL search by name and display name, SHALL show the entity kind and its System (when it has one) in each result, SHALL be limited to the selectable kinds of the chosen level and enabled entity types, SHALL NOT allow the same entity to be chosen twice, and SHALL store stable entity identifiers. Chosen entities SHALL be listed as compact rows with a kind icon, the name, and a remove button, and the heading SHALL show the count. The picker SHALL work without the optional search plugin. Actors SHALL be offered when the Actors type is enabled.

#### Scenario: Results show kind and System
- **WHEN** the user searches at the Components level
- **THEN** each result shows its kind and, if it has one, its System

#### Scenario: An entity cannot be chosen twice
- **WHEN** an entity is already chosen
- **THEN** it is not offered again as a new selection

#### Scenario: Actors can be chosen
- **WHEN** the Actors type is enabled and the user searches for an actor
- **THEN** the actor is offered and can be chosen as a root or selection member

#### Scenario: Empty selection guidance
- **WHEN** no entities are chosen
- **THEN** the panel shows "Select at least one entity to build a view." and Apply view and Save are disabled

### Requirement: Draft settings are previewed explicitly and saved separately
The panel SHALL hold draft values separately from the applied preview. Changing a field SHALL NOT render a diagram. **Apply view** SHALL send the whole draft to the preview, show a loading state, and make the draft the applied preview after success; it SHALL be disabled while the draft is invalid or a request is running. Apply view SHALL NOT store anything and SHALL NOT change the URL. **Save** SHALL store the current draft, whether or not it has been applied. When the draft and the applied preview differ, the preview SHALL show "Unapplied changes. Apply your changes to update the diagram." **Reset** SHALL return the draft to the values the editor opened with (the stored view, or the prefill) without applying it.

#### Scenario: Editing does not render
- **WHEN** the user changes the depth
- **THEN** no diagram request is made and the unapplied-changes notice appears

#### Scenario: Apply renders the preview and stores nothing
- **WHEN** the user presses Apply view with a valid draft
- **THEN** a loading state is shown, the preview is rendered, and no view is created or changed

#### Scenario: Save stores the draft
- **WHEN** the user has unapplied changes and presses Save
- **THEN** the draft, not the older applied preview, is stored

#### Scenario: Reset changes the draft only
- **WHEN** the user presses Reset
- **THEN** the form returns to the values the editor opened with and the applied preview is unchanged until Apply

### Requirement: Opening the builder from an Architecture tab prefills a root
The System Architecture tab and the Component Architecture tab SHALL provide an "Open in view builder" action that links to `/system-map/views/new?root=<entity id>`. The editor SHALL derive the level from the entity (the Systems level for a System, the Components level for a Component), select the entity as a Neighborhood root, use depth 1, direction Both, declared only relationships, and all entity types enabled, and SHALL render the preview immediately. Nothing SHALL be stored until the user saves. An unknown or unsupported `root` SHALL open the editor with the default draft and a message.

#### Scenario: System preset
- **WHEN** a user presses "Open in view builder" on a System's Architecture tab
- **THEN** the new-view editor opens at the Systems level in Neighborhood mode with that System as root, depth 1, direction Both, and the preview is rendered

#### Scenario: Component preset
- **WHEN** a user presses "Open in view builder" on a Component's Architecture tab
- **THEN** the new-view editor opens at the Components level in Neighborhood mode with that Component as root, depth 1, direction Both, with Components, Resources, APIs, and Actors enabled, and the preview is rendered

#### Scenario: Nothing is stored by opening the builder
- **WHEN** a user opens the builder from an Architecture tab and leaves without saving
- **THEN** no view is created

#### Scenario: Unknown root
- **WHEN** the `root` parameter names an entity that does not exist or cannot be a root
- **THEN** the editor opens with the default draft and a message that the entity could not be used

### Requirement: Preview and detail headings and exports reflect the displayed diagram
The editor preview heading SHALL be computed from the applied preview: "<Entity title> dependencies" for a single chosen entity, "Selected architecture" for several, and "Custom view" when none is applied. The detail page SHALL use the view name as its heading. The viewer SHALL reuse the existing pan, zoom, and fit to viewport controls. SVG and PNG export SHALL be available on the detail page for the saved view, using the active viewer rendering preferences, and SHALL NOT be offered for an unsaved draft in the editor. There SHALL be no Copy link control; a view is shared by its detail page address.

#### Scenario: Single-entity heading in the editor
- **WHEN** a preview with one chosen entity named Booking API is applied
- **THEN** the heading reads "Booking API dependencies"

#### Scenario: Export belongs to the saved view
- **WHEN** a user opens the editor for a new view
- **THEN** SVG and PNG export are not offered until the view is saved and its detail page is opened

#### Scenario: No Copy link
- **WHEN** a user opens the editor or the detail page
- **THEN** there is no Copy link button

### Requirement: Builder handles loading, empty results, and failures
While a preview or a saved view diagram is rendering, the viewer SHALL show a loading indicator and Apply SHALL be disabled. A response to a superseded request SHALL NOT replace the result of a newer request. When a preview fails, the previous successful preview SHALL stay visible together with a message stating that the new settings were not applied; a rendering failure SHALL offer Retry; a node-limit failure SHALL tell the user to reduce depth or the selection and SHALL show the limit and the resulting count from the error. An unknown or removed entity SHALL be reported next to the selection, named, with an option to remove it, and SHALL NOT be dropped silently. A result with nodes but no relationships SHALL simply show the nodes.

#### Scenario: Stale response is ignored
- **WHEN** a user applies a preview and applies another before the first response arrives
- **THEN** only the second response updates the preview

#### Scenario: Failure keeps the previous preview
- **WHEN** a new Apply fails after an earlier success
- **THEN** the earlier preview stays visible and a message states that the new settings were not applied

#### Scenario: Node limit message
- **WHEN** a request exceeds the node limit
- **THEN** the message states the limit and the resulting count and suggests reducing depth or selection

#### Scenario: Missing entity in the editor
- **WHEN** a user opens the editor for a view that references a removed entity
- **THEN** the missing entity is named beside the selection with a way to remove it, and the view can be saved after removal

### Requirement: Builder controls are accessible and follow the application theme
Every field SHALL have an accessible name, icon-only buttons (including the panel toggle and remove buttons) SHALL have a tooltip and `aria-label`, and the builder SHALL use the application's existing components and support the active theme, including a dark theme where the application provides one. The interface language SHALL be English.

#### Scenario: Icon buttons are labelled
- **WHEN** the editor renders the panel toggle, remove buttons, and viewer toolbar buttons
- **THEN** each has an accessible name and a tooltip
