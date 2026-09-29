## MODIFIED Requirements

### Requirement: Reading a Flow surfaces live status of entity_ref-targeted entities

When a Flow is read (list or detail), for each step carrying a non-empty `entity_ref` that resolves to any of the six entity-backed kinds (Actor, Team, System, Component, Resource, or API), the response SHALL additionally include that entity's current `title`, `description`, `status` (`active`/`removed`), and `deprecated` flag, resolved at read time — mirroring the existing live-status surfacing already provided for `query_ref`/`event_ref` steps in the `flow-query-event-steps` capability. `title`/`description` SHALL always be included whenever the reference resolves (rendering depends on them directly, not only as diagnostic information), independent of whether `status`/`deprecated` indicate anything noteworthy. This SHALL NOT modify the step's stored `entity_ref`, and SHALL NOT modify or derive from any `title`/`summary` stored on the step itself. When the referenced entity no longer resolves at all (e.g. it was purged), the read SHALL still succeed, presenting the step without a live status (including without `title`/`description`) rather than failing the Flow read.

#### Scenario: Reading a Flow reports a removed entity's current status

- **WHEN** a Flow containing a step whose `entity_ref` resolves to a Component with `status: removed` is read
- **THEN** the response includes that step's stored `entity_ref` unchanged, plus the Component's current `status: removed`

#### Scenario: Reading a Flow reports a deprecated entity's current status

- **WHEN** a Flow containing a step whose `entity_ref` resolves to a Component with `deprecated: true` is read
- **THEN** the response includes `deprecated: true` for that step's target

#### Scenario: A removed entity_ref target does not invalidate an existing Flow's reference

- **WHEN** an entity referenced by an existing Flow step's `entity_ref` becomes `removed` after the Flow was saved
- **THEN** the Flow continues to resolve and read successfully, showing the live `removed` status rather than rejecting the read

#### Scenario: Reading a Flow whose entity_ref target no longer resolves at all does not fail the read

- **WHEN** a Flow containing a step whose `entity_ref` no longer resolves to any entity (e.g. it was purged) is read
- **THEN** the read succeeds, the step's stored `entity_ref` is presented, and no live status — including no `title`/`description` — is included for that step

#### Scenario: Reading a Flow always includes an entity's live title and description

- **WHEN** a Flow containing a step whose `entity_ref` resolves to an active, non-deprecated System with `title: "Billing System"` and `description: "Owns invoicing"` is read
- **THEN** the response includes `title: "Billing System"` and `description: "Owns invoicing"` for that step, alongside its `status`/`deprecated`

#### Scenario: Live status is reported uniformly for all six entity-backed kinds

- **WHEN** a Flow containing steps whose `entity_ref` resolve one each to an Actor and a Team is read
- **THEN** the response includes live `title`/`description`/`status`/`deprecated` for both steps, the same as it would for a Component, Resource, API, or System
