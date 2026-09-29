## Why

Catalog exploration currently has two usability gaps: list preview rails align inconsistently, and architecture interactions are only discoverable from their source entity. The homepage also lacks the organization-level context shown by catalog products such as EventCatalog, despite Atlas already having the data and C4 rendering foundation needed to provide it.

## What Changes

- Align the Team list preview rail with the entity-list table/preview pattern so all list pages present their heading before the table-and-rail content row.
- Show incoming as well as outgoing Architecture Relationships in entity Relations tabs, while preserving their direction, origin, and edit permissions.
- Update Atlas C4 diagram styling to use the approved rounded, semantic color scheme and relationship-line treatments from `local/diagram_colors.json`, without allowing free-form catalog tags to restyle diagrams.
- Add configurable catalog title and description settings and display them on the homepage above the catalog navigation cards.
- Add a homepage System Landscape C4 diagram that renders all catalog systems and explicitly related people, combining declared architecture interactions with derived cross-system relations.

## Capabilities

### New Capabilities
- `catalog-home-landscape`: Configurable homepage identity and a catalog-wide System Landscape diagram.

### Modified Capabilities
- `catalog-web-ui`: Normalize list preview-rail placement and expose incoming Architecture Relationships in detail-page Relations tabs.
- `architecture-relationships`: Make an entity's relationship listing/view include incoming relationships while keeping authored direction and source-based authorization.
- `catalog-c4-diagrams`: Adopt the approved rounded semantic style and generate/serve the catalog-wide System Landscape.

## Impact

- Frontend list, Relations, homepage, diagram-viewer, and settings UI components.
- Catalog relationship-list API and C4 payload/endpoint generation.
- Django configuration/persistence for homepage title and description.
- C4/PlantUML rendering contracts and their frontend/backend tests.
- Existing same-direction declared-over-derived edge precedence remains intentional and unchanged.
