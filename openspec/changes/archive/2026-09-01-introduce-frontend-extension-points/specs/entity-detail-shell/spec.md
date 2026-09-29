## ADDED Requirements

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
