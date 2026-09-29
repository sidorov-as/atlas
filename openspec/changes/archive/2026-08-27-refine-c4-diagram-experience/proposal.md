## Why

The current System C4 tab is correctly a System Context diagram, but its generic name makes users expect to see the selected System's internal components and resources. The generated diagrams also need a consistent, readable visual language and relationship authoring must make User and Group actors discoverable without hand-writing catalog refs.

## What Changes

- Add a System Architecture diagram alongside the existing System Context view, showing the selected System's components, APIs, and resources without mixing abstraction levels in the context view.
- Render C4 diagrams top-down with stable Atlas PlantUML tags, legend entries, element styling, and interaction-kind relationship styling.
- Extend the booking demo with explicit Architecture Relationships, including a User or Group actor rendered as a C4 Person.
- Replace the free-text Architecture Relationship target field with a searchable catalog-reference lookup covering Systems, Components, APIs, Resources, Users, and Groups.

## Capabilities

### New Capabilities

- `system-architecture-diagram`: System-scoped C4 view for internal components, APIs, resources, and explicit interactions.

### Modified Capabilities

- `catalog-c4-diagrams`: Add the System Architecture image endpoint and stable top-down PlantUML visual contract while retaining System Context semantics.
- `catalog-web-ui`: Expose separate System Context and System Architecture views and provide a target-ref lookup for Architecture Relationship authoring.
- `architecture-relationships`: Support actor endpoints as discoverable authoring targets and demonstrate them in booking seed data.

## Impact

- Backend C4 scope builders, image API validation, PlantUML payload options, demo seed command, and rendering tests.
- Frontend System detail tabs, diagram URLs/types, Architecture Relationship form, shared reference lookup, and frontend tests.
- No schema migration or external rendering service is required.
