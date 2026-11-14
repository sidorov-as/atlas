# c4-diagram-viewer-preferences Specification

## Purpose

Persist and apply per-view rendering preferences in the C4 diagram viewer.

## Requirements

### Requirement: C4 viewer exposes persisted per-view rendering preferences
The C4 diagram viewer SHALL expose a lower-left Gear settings control after a
diagram image is ready. The control SHALL let the user select Top-down,
Left-right, or Landscape layout and independently choose visibility of the
title, legend, selected-element `(selected)` label, person sprite, and
stereotypes. The viewer SHALL persist valid choices in browser local storage,
scoped by C4 diagram view, and restore them when that view is opened again.

#### Scenario: A layout choice is restored for the same diagram view
- **WHEN** a user selects Left-right layout on a Component Diagram and later
  opens another Component Diagram
- **THEN** the viewer restores Left-right as that Component Diagram view's
  active layout

#### Scenario: A preference does not leak to a different diagram view
- **WHEN** a user selects Landscape for a Component Diagram and opens a System
  Context Diagram with no saved Context preference
- **THEN** the Context Diagram uses the default Top-down layout

#### Scenario: Invalid saved preferences fall back safely
- **WHEN** browser storage contains an unknown layout or malformed preference
  value
- **THEN** the viewer uses the default rendering preferences without failing to
  render the diagram

### Requirement: Viewer image and download URLs use the active preferences
The viewer SHALL send its active rendering preferences and the active UI theme (`light` or `dark`, as resolved by the application) when requesting the
displayed SVG or PNG and when requesting a downloadable image. A preference
change or a UI theme change SHALL reload the displayed image and reset it to a fitting viewport
scale. The viewer SHALL NOT draw a fixed light backdrop behind the diagram; its background SHALL follow the active theme.

#### Scenario: Download matches the visible diagram configuration
- **WHEN** a user hides the legend and downloads the SVG
- **THEN** the download request includes the active legend setting and returns
  an image without the legend

#### Scenario: Download matches the visible theme
- **WHEN** a user views a diagram in the dark theme and downloads the SVG or PNG
- **THEN** the download request includes `theme=dark` and returns an image rendered with the dark palette

#### Scenario: Theme change reloads the diagram
- **WHEN** a user switches the UI theme while a diagram is displayed
- **THEN** the viewer requests the diagram again in the new theme and fits it to the viewport

#### Scenario: Viewer backdrop follows the theme
- **WHEN** a diagram is displayed in the dark theme
- **THEN** the viewer area has no white backdrop and blends with the dark page background

### Requirement: Viewer refits when its viewport is resized
The C4 diagram viewer SHALL re-fit a loaded image when its viewport obtains a
new non-zero size, including when its detail-page tab becomes visible.

#### Scenario: Returning to a diagram tab refits the image
- **WHEN** a loaded diagram tab is hidden and later made visible at a different
  viewport size
- **THEN** the diagram is automatically centered and fitted to the new
  viewport without requiring the Fit to viewport control
