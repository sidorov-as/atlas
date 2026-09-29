## MODIFIED Requirements

### Requirement: Administrative and custom mutation controls obey read-only
All installed core/plugin write controls and pure mutation routes SHALL obey isReadOnly, including relationship editors, System Docs document-link authoring, tags, configuration/settings, and user-triggered mutation jobs. Mixed read/write pages SHALL preserve allowed read content while hiding mutation controls. Pure mutation routes SHALL redirect to a safe read destination. This SHALL apply even when isAdmin is true and SHALL not alter per-entity YAML provenance rules.

#### Scenario: Read-only administrator opens settings
- **WHEN** a read-only account with ordinary permission to view settings opens a mixed settings page
- **THEN** permitted read content remains visible but editing, saving, and mutation-trigger controls are absent

#### Scenario: Menu contains read and write actions
- **WHEN** a read-only user opens an action menu with navigation/export and mutation entries
- **THEN** permitted read actions remain and mutation entries are hidden

#### Scenario: Read-only user opens a manually managed System's Docs tab
- **WHEN** a read-only user opens the Docs tab for a System that would otherwise allow document-link authoring
- **THEN** document links, search, pagination, opening links, and copying URLs remain available
- **AND** the Add, edit, remove, and document-link authoring dialog controls are absent
