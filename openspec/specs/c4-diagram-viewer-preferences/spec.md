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
The viewer SHALL send its active rendering preferences when requesting the
displayed SVG or PNG and when requesting a downloadable image. A preference
change SHALL reload the displayed image and reset it to a fitting viewport
scale.

#### Scenario: Download matches the visible diagram configuration
- **WHEN** a user hides the legend and downloads the SVG
- **THEN** the download request includes the active legend setting and returns
  an image without the legend

### Requirement: Viewer refits when its viewport is resized
The C4 diagram viewer SHALL re-fit a loaded image when its viewport obtains a
new non-zero size, including when its detail-page tab becomes visible.

#### Scenario: Returning to a diagram tab refits the image
- **WHEN** a loaded diagram tab is hidden and later made visible at a different
  viewport size
- **THEN** the diagram is automatically centered and fitted to the new
  viewport without requiring the Fit to viewport control
