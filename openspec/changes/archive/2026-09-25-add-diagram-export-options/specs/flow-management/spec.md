## ADDED Requirements

### Requirement: Read-only Flow diagram provides an Export control
A Flow's read-only detail page diagram SHALL provide an Export control offering an SVG/PNG format choice, a "Transparent background" checkbox, and a "Grid" checkbox, each defaulted to SVG format, transparent checked, and grid checked on every open, with none of the three persisting between exports or page loads. Activating Export SHALL download the diagram as it is currently laid out, honoring the selected format, background, and grid options, without altering the visible canvas at any point before, during, or after the export. This control SHALL render only on the read-only detail page's diagram; the edit page's canvas SHALL NOT render it.

#### Scenario: Opening the Export control shows default options
- **WHEN** a user activates the Export control on a Flow's read-only detail page
- **THEN** a popup opens offering an SVG/PNG format choice defaulted to SVG, a "Transparent background" checkbox defaulted to checked, and a "Grid" checkbox defaulted to checked

#### Scenario: Exporting the diagram with default options
- **WHEN** a user opens the Export control and activates the Export action without changing any option
- **THEN** the system downloads the current Flow diagram as an SVG file with a transparent background and the grid included

#### Scenario: Exporting with a white background and no grid
- **WHEN** a user unchecks "Transparent background" and unchecks "Grid" before activating Export
- **THEN** the downloaded file has a white background and omits the grid dots, in either SVG or PNG format

#### Scenario: Export options do not affect the live viewer
- **WHEN** a user unchecks "Grid" or "Transparent background" in the Export popup, with or without completing an export
- **THEN** the read-only detail page's on-screen canvas continues to show its grid and background unchanged throughout

#### Scenario: Export options reset on next open
- **WHEN** a user changes the format, transparency, or grid option, exports or closes the popup, and later reopens the Export control
- **THEN** the popup shows the default format (SVG), transparent background checked, and grid checked, regardless of the previous export's choices

#### Scenario: No Export control on the edit page canvas
- **WHEN** a user opens a Flow's edit page
- **THEN** its canvas shows no Export control
