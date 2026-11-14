## MODIFIED Requirements

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
