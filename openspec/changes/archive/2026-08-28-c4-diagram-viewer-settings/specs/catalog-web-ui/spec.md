## MODIFIED Requirements

### Requirement: Diagram viewer provides viewport controls, settings, and download
The System and Component C4 Diagram viewer SHALL provide pointer pan, Zoom in,
Zoom out, Fit to viewport, an image download action, and a lower-left Gear
settings control. The settings control SHALL let the user set the active C4
rendering preferences and SHALL not overlap the upper-right viewport controls.
The viewer SHALL show loading and rendering-failure states without leaving a
broken image element, and SHALL automatically fit a loaded image when its
viewport size changes.

#### Scenario: User fits a zoomed diagram
- **WHEN** a user changes the diagram scale and activates Fit to viewport
- **THEN** the diagram returns to a scale and position that fits its viewer
  bounds

#### Scenario: User downloads the visible diagram format
- **WHEN** a user activates the diagram download action
- **THEN** the browser requests the same diagram endpoint with download enabled
  and receives an image attachment

#### Scenario: User opens diagram settings
- **WHEN** a loaded C4 diagram user activates the lower-left Gear control
- **THEN** the viewer presents layout and display-preference controls while
  preserving access to pan, zoom, fit, and download actions

#### Scenario: A hidden tab becomes visible
- **WHEN** a loaded C4 diagram is shown after its viewer bounds changed while
  the tab was hidden
- **THEN** the image is fitted to the available viewer bounds automatically
