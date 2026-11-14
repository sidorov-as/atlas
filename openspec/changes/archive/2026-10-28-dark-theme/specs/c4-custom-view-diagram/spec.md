## ADDED Requirements

### Requirement: Custom view diagrams accept an optional theme
The custom view preview endpoint and the saved-view diagram endpoint SHALL accept the same optional `theme` option (`light` or `dark`, default `light`) as the other C4 diagram endpoints, including for SVG, PNG, and download requests. A dark custom view diagram SHALL keep the same element types, tags, relationship styling, and legend entries as its light rendering, differing only in palette. The `theme` option SHALL NOT be part of a saved view's settings.

#### Scenario: Saved view renders in dark
- **WHEN** an authenticated user requests a saved view's diagram with `theme=dark`
- **THEN** the endpoint returns that view's diagram rendered with the dark palette

#### Scenario: Preview renders in dark
- **WHEN** an authenticated user requests a preview with valid settings and `theme=dark`
- **THEN** the endpoint returns the preview rendered with the dark palette

#### Scenario: Theme is not stored on the view
- **WHEN** a user saves a view while the UI is in dark mode
- **THEN** the stored view settings contain no theme value, and the same view renders light or dark according to each request

#### Scenario: Default stays light
- **WHEN** a custom view diagram is requested without `theme`
- **THEN** the response is identical to that before the option existed
