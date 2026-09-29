## 1. Catalog configuration and homepage

- [x] 1.1 Add documented `CATALOG_TITLE` and `CATALOG_DESCRIPTION` Django settings with safe defaults.
- [x] 1.2 Add an authenticated read-only catalog-configuration API schema, controller, and route, with backend tests for defaults and overrides.
- [x] 1.3 Add frontend configuration client/types and render the configured title and description, divider, and existing catalog cards on the homepage.

## 2. Relation participation and list layout

- [x] 2.1 Extend Architecture Relationship list serialization/querying to return canonical directed relationships in which the requested entity is either source or target, with backend tests.
- [x] 2.2 Update RelationsTab to display source/target direction and restrict mutation controls to outgoing manual relationships of the current source entity; add frontend coverage for incoming and YAML rows.
- [x] 2.3 Restructure EntityListPage so its heading, description, filters, and alerts precede the table-and-preview flex row; align Teams to the same layout and update list-page tests.

## 3. C4 landscape and visual system

- [x] 3.1 Replace minimal Atlas C4 tag definitions with the approved fixed rounded semantic element and relationship styles, including complete legend metadata and payload tests.
- [x] 3.2 Implement the catalog-wide System Landscape payload builder: all systems, explicit actors only, system endpoint mapping, deterministic ordering, and declared-over-derived directed edge precedence.
- [x] 3.3 Add an unscoped landscape diagram endpoint with SVG/PNG/download handling and backend rendering tests, preserving existing diagram routes.
- [x] 3.4 Add a homepage landscape section using the shared DiagramViewer and test loading, error, and download URL behavior.

## 4. Verification and documentation

- [x] 4.1 Update API/OpenAPI documentation and deployment configuration documentation for the catalog identity and landscape endpoints.
- [x] 4.2 Run targeted backend and frontend test suites, lint/type checks, and C4 rendering validation; resolve regressions.
