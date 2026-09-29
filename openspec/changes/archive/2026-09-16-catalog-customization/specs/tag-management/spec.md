## MODIFIED Requirements

### Requirement: Tag colors section on the Settings page
The Settings area SHALL present the tag color table at its own nested route, `/settings/tags`, reachable from the Settings sub-navigation, distinct from any other Settings section, so that additional, unrelated settings sections can live at their own routes without implying they are also about tag colors.

#### Scenario: Tag colors has its own Settings route
- **WHEN** an admin opens `/settings/tags`
- **THEN** the tag color table renders directly, labeled as the "Tag colors" section

#### Scenario: Settings sub-navigation links to Tag colors
- **WHEN** an admin is anywhere within the Settings area
- **THEN** the sub-navigation includes a link to the "Tag colors" section
