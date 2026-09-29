## 1. System Architecture diagram and renderer contract

- [x] 1.1 Add a System Architecture scope builder that includes selected-System Components, APIs, Resources, directly related external endpoints, and deterministic explicit-over-derived edges.
- [x] 1.2 Extend diagram endpoint validation, URLs, and image/download responses for `system/{id}/?view=architecture` while retaining `system/context` behavior.
- [x] 1.3 Add closed Atlas PlantUML tag mappings for element roles and Architecture Relationship interaction kinds, top-down layout, and a visible semantic legend.
- [x] 1.4 Add backend tests for System Architecture scope, endpoint validation and formats, explicit edge precedence, top-down options, and fixed style tags.

## 2. Actor relationships and demo data

- [x] 2.1 Verify User and Group targets remain accepted by Architecture Relationship resolution and render explicit actor endpoints as People only.
- [x] 2.2 Extend the booking demo seed with idempotent explicit Architecture Relationships covering every interaction kind, an external dependency, and a User or Group actor.
- [x] 2.3 Add seed and C4 rendering tests proving the demo actor appears as a Person without ownership-derived actors.

## 3. System and relationship authoring UI

- [x] 3.1 Split the System C4 tab into clearly named full-width System Context and System Architecture tabs with correct generated image and download URLs.
- [x] 3.2 Replace Architecture Relationship Target ref text entry with a searchable typed catalog lookup restricted to System, Component, API, Resource, User, and Group records.
- [x] 3.3 Add frontend tests for both System diagram views, target lookup search/filtering, canonical target submission, and actor selection.

## 4. Verification

- [x] 4.1 Run targeted backend C4, architecture-relationship, and booking-demo tests; verify local PlantUML SVG generation for System Context, System Architecture, and Component Diagram.
- [x] 4.2 Run frontend unit tests, typecheck, lint, and production build; manually verify the System tabs and relationship target lookup in the development topology.
- [x] 4.3 Validate the OpenSpec change in strict mode and update artifacts for verification discoveries.
