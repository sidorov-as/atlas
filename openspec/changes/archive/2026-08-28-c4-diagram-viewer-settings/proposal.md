## Why

The fixed C4 rendering configuration is not equally useful for every diagram: a
top-down layout may waste space, while legends, titles, the selected-component
suffix, and person decorations can obscure the architecture being examined.
The viewer also fails to re-fit when its tab becomes visible or its container
resizes, leaving some diagrams unnecessarily small.

## What Changes

- Add a settings control, anchored at the lower-left of every C4 diagram
  viewer, for choosing a supported PlantUML layout and visibility options.
- Persist each user's display choices locally in the browser so they are
  restored for future diagram views without changing catalog data.
- Pass the active rendering choices to the diagram image and download URLs;
  make the diagram endpoint validate and apply them when building PlantUML
  payloads.
- Allow title, legend, selected-component label, person sprite, and stereotype
  visibility to be independently configured. The selected component remains
  visually highlighted even when its `(selected)` label is hidden.
- Refit an already-loaded diagram when its viewport changes size, including
  after opening or switching back to a detail-page tab.

## Capabilities

### New Capabilities

- `c4-diagram-viewer-preferences`: Local, per-diagram-view rendering
  preferences and their settings-control experience.

### Modified Capabilities

- `catalog-c4-diagrams`: Generated diagram rendering gains validated
  per-request layout and display options instead of a fixed top-down, titled,
  legend-visible rendering.
- `catalog-web-ui`: The C4 viewer gains a settings control and automatic
  fit-to-viewport on viewport-size changes.

## Impact

- Frontend: `DiagramTab`, diagram URL helpers, and viewer tests; uses existing
  Gravity UI controls and icons.
- Backend: diagram query schema, controllers, C4 payload builders, and diagram
  rendering tests.
- Browser storage: new versioned localStorage preference key; no database
  migration or catalog-entity change.
- Existing diagram URLs remain valid and retain the current visual defaults
  when no new options are supplied.
