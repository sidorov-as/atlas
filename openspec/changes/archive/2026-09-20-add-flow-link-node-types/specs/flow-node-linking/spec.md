## ADDED Requirements

### Requirement: Step supports Flow and Link kinds referencing another Flow or an external URL

A Flow step MAY carry a `flow_ref` (an integer id referencing another Flow) or a `link_url` (a string) in place of `entity_ref`/`external_label`/`query_ref`/`event_ref`. A step SHALL carry at most one of `entity_ref`, `external_label`, `query_ref`, `event_ref`, `flow_ref`, and `link_url`; a step violating this SHALL be rejected on save. On every save, a non-empty `flow_ref` SHALL resolve to an existing Flow; a `flow_ref` that does not resolve SHALL cause the save to be rejected. A `flow_ref` referencing the same Flow the step belongs to is permitted — a Flow node linking to its own Flow is not rejected, and no cycle check is performed across `flow_ref` targets (a Flow node is a navigation link, not an embedded sub-flow). On every save, a non-empty `link_url` SHALL be a well-formed absolute URL using the `http` or `https` scheme; a `link_url` that is not, including one using any other scheme, SHALL cause the save to be rejected. Unlike `entity_ref`/`query_ref`/`event_ref`, a step carrying `flow_ref` SHALL NOT carry a custom `title` or `summary` — the same rule already applied to those ref-backed kinds. A step carrying `link_url` MAY carry its own `title` and/or `summary`, the same as a step with no reference at all.

#### Scenario: Step with a resolvable flow_ref saves successfully

- **WHEN** a Flow is saved with a step whose `flow_ref` resolves to an existing Flow
- **THEN** the Flow is persisted with that step's `flow_ref` intact

#### Scenario: Step with a link_url saves successfully

- **WHEN** a Flow is saved with a step whose `link_url` is `https://example.com/runbook`
- **THEN** the Flow is persisted with that step's `link_url` intact

#### Scenario: flow_ref and link_url are mutually exclusive with entity_ref, external_label, query_ref, event_ref, and each other

- **WHEN** a Flow is saved with a step that carries more than one of `entity_ref`, `external_label`, `query_ref`, `event_ref`, `flow_ref`, and `link_url`
- **THEN** the save is rejected

#### Scenario: A flow_ref that does not resolve is rejected

- **WHEN** a Flow is saved with a step whose `flow_ref` does not resolve to any existing Flow
- **THEN** the save is rejected and no Flow data is persisted or updated

#### Scenario: A Flow node may reference its own Flow

- **WHEN** a Flow is saved with a step whose `flow_ref` is that same Flow's own id
- **THEN** the save succeeds

#### Scenario: A link_url with a disallowed scheme is rejected

- **WHEN** a Flow is saved with a step whose `link_url` is `javascript:alert(1)`
- **THEN** the save is rejected

#### Scenario: A link_url that is not a well-formed absolute URL is rejected

- **WHEN** a Flow is saved with a step whose `link_url` is `not a url`
- **THEN** the save is rejected

#### Scenario: A flow_ref step with a non-empty title is rejected

- **WHEN** a Flow is saved with a step whose `flow_ref` is non-empty and whose `title` is also non-empty
- **THEN** the save is rejected

#### Scenario: A link_url step may carry its own title and summary

- **WHEN** a Flow is saved with a step whose `link_url` is non-empty and whose `title` and `summary` are also non-empty
- **THEN** the save succeeds, and both the `title` and `summary` are persisted as given

### Requirement: Reading a Flow surfaces live status of flow_ref-targeted Flows

When a Flow is read (list or detail), for each step carrying a non-empty `flow_ref`, the response SHALL additionally include the target Flow's current `name` and `description`, resolved at read time. This SHALL NOT modify the step's stored `flow_ref`. When the referenced Flow no longer resolves (e.g. it was deleted), the read SHALL still succeed, presenting the step's stored `flow_ref` without a live `name`/`description` rather than failing the Flow read.

#### Scenario: Reading a Flow reports a flow_ref target's current name and description

- **WHEN** a Flow containing a step whose `flow_ref` resolves to a Flow with `name: "Checkout"` and `description: "Cart to payment"` is read
- **THEN** the response includes `name: "Checkout"` and `description: "Cart to payment"` for that step

#### Scenario: Reading a Flow whose flow_ref target no longer resolves does not fail the read

- **WHEN** a Flow containing a step whose `flow_ref` no longer resolves to any Flow (e.g. it was deleted) is read
- **THEN** the read succeeds, the step's stored `flow_ref` is presented, and no live `name`/`description` is included for that step
