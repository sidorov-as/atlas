## ADDED Requirements

### Requirement: Detail URLs can select an applicable tab
The canonical Entity Detail Shell SHALL use a `tab` URL query parameter to
select an applicable contributed tab. It SHALL update the parameter when a
user changes tabs and SHALL fall back to the first applicable tab when the
parameter is absent or does not name an applicable tab.

#### Scenario: Direct link opens the Docs tab
- **WHEN** a user opens `/systems/{id}?tab=docs`
- **THEN** the System detail page renders with the Docs tab active

#### Scenario: Invalid tab parameter falls back safely
- **WHEN** a user opens a detail URL whose `tab` parameter does not identify
  an applicable tab
- **THEN** the first applicable tab is active and the detail page remains
  usable
