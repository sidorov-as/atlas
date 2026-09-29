## MODIFIED Requirements

### Requirement: Flow diagram nodes are typed and colored by kind
Each step's node SHALL render styled according to its kind: a step whose `entity_ref` targets a `user` or `group` SHALL render as an Actor or Team node respectively, `component` as a Service node, `resource` as a Data node, `api` as an API node, and `system` as a System node, each using a fixed color drawn from the catalog's existing C4 diagram palette, alongside an icon and a kind label visually distinguished from the node's own title text. A step with a `query_ref` SHALL render as a Query node using a magnifier icon, colored by its snapshotted HTTP `method` using the same color mapping Endpoints use for method badges. A step with an `event_ref` SHALL render as an Event node using a lightning-bolt icon, colored by its snapshotted `direction` using the same color mapping Operations use for direction badges. A step with a `flow_ref` SHALL render as a Flow node using the same icon as the "Flows" sidebar navigation item, in a fixed color distinct from every other kind's color. A step with a `link_url` SHALL render as a Link node using a chain-link icon, in a fixed color distinct from every other kind's color, including Flow's. A step with no `entity_ref`, `query_ref`, `event_ref`, `flow_ref`, or `link_url` SHALL render as a plain Step node (optionally colored per its `label_theme`) unless it carries `external_label`, in which case it SHALL render as an External node using the catalog's fixed External color. A node's title, subtitle, and kind label SHALL show their full value in a tooltip when hovered, regardless of whether the displayed text is visually truncated. This styling SHALL apply identically on the read-only detail page and the edit page's canvas.

#### Scenario: Component-backed step renders as a colored Service node
- **WHEN** a step's `entity_ref` resolves to a Component
- **THEN** the step's node renders with the Service node's fixed color, a Service icon, and a Service type label visually distinct from the node's title

#### Scenario: Query step renders with a method-colored magnifier icon
- **WHEN** a step carries a `query_ref` with a snapshotted `method` of `GET`
- **THEN** the step's node renders as a Query node with a magnifier icon and the color Endpoints use for a `GET` method badge

#### Scenario: Event step renders with a direction-colored bolt icon
- **WHEN** a step carries an `event_ref` with a snapshotted `direction` of `send`
- **THEN** the step's node renders as an Event node with a lightning-bolt icon and the color Operations use for a `send` direction badge

#### Scenario: Flow step renders with the Flows nav icon
- **WHEN** a step carries a `flow_ref`
- **THEN** the step's node renders as a Flow node using the same icon as the "Flows" sidebar navigation item, in its fixed color

#### Scenario: Link step renders with a chain-link icon
- **WHEN** a step carries a `link_url`
- **THEN** the step's node renders as a Link node using a chain-link icon, in its own fixed color, distinct from Flow's

#### Scenario: Step without an entity_ref, query_ref, event_ref, flow_ref, or link_url renders as a plain Step node
- **WHEN** a step has no `entity_ref`, `query_ref`, `event_ref`, `flow_ref`, `link_url`, or `external_label`
- **THEN** the step's node renders as a Step node, colored per its `label_theme` if set, or with a neutral default otherwise

#### Scenario: Step with an external_label renders as an External node
- **WHEN** a step has an `external_label` and no `entity_ref`
- **THEN** the step's node renders as an External node using the catalog's fixed External color

#### Scenario: Diagram styling matches between detail page and edit canvas
- **WHEN** the same Flow is viewed on its read-only detail page and on its edit page's canvas
- **THEN** corresponding steps render with identical node type, color, and icon on both

#### Scenario: Hovering truncated node text shows its full value
- **WHEN** a user hovers a node whose title or subtitle is too long to display in full
- **THEN** a tooltip shows the complete, untruncated text
