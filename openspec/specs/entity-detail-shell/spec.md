# entity-detail-shell Specification

## Purpose
A core-owned, canonical `EntityDetailShell` renders every Entity Kind's detail page from that kind's tab contributions plus any applicable cross-kind tab, action, and banner contributions. The shell provides shared loading, unavailable, error, and permission-denied states, and isolates each contribution in its own error boundary, so a failing tab, action, or banner cannot crash the page or other contributions rendered alongside it.

## Requirements

### Requirement: Core owns the canonical entity detail shell
Every Entity Kind's canonical detail page SHALL render through one core-owned `EntityDetailShell`, composed from that kind's tab contributions plus any cross-kind tab, action, and banner contributions that apply to it.

#### Scenario: A kind-owned tab renders inside the shell
- **WHEN** an Entity Kind contributes an `entityDetailTab`
- **THEN** that tab renders inside `EntityDetailShell` using the shell's shared header, rail, and tab-bar chrome

### Requirement: Shared loading, unavailable, error, and permission states
`EntityDetailShell` SHALL provide shared loading, unavailable, error, and permission-denied states so individual tab/action contributions do not each reimplement them.

#### Scenario: A permission-denied entity shows the shared state
- **WHEN** a user without read permission opens an entity's detail page
- **THEN** the shell shows its shared permission-denied state rather than a blank or partially-rendered page

### Requirement: Each contribution is isolated in its own error boundary
A failing tab, action, or banner contribution SHALL NOT crash the shell or any other contribution rendered on the same page.

#### Scenario: One broken tab does not break the page
- **WHEN** one entity-detail tab's content throws during render
- **THEN** that tab shows a visible failed-to-load state while the rest of the detail page, including its other tabs, remains usable

### Requirement: Custom routes may bypass the canonical shell
A plugin MAY register a fully custom route for a specialized full-screen experience, but the canonical per-entity detail URL for a registered kind SHALL always use `EntityDetailShell`.

#### Scenario: A custom full-screen route exists alongside the canonical page
- **WHEN** a plugin declares a custom route for a full-screen editor
- **THEN** that route renders its own content outside `EntityDetailShell`, while the entity's canonical detail URL still renders through the shell

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
