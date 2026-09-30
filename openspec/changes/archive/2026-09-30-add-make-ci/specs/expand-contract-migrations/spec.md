## MODIFIED Requirements

### Requirement: Destructive migrations are blocked outside maintenance mode
A migration that drops a column or table, or narrows a field's nullability
without a default, SHALL be blocked unless the deployment explicitly opts
into a maintenance-mode override. This check SHALL run against a baseline
file committed to the repository, identifying migrations already known at
baseline-generation time, rather than against a diff computed from a git
ref (such as a base branch). The same check command and the same baseline
file SHALL be used both in CI and in any local invocation, so the two
cannot disagree because of environment differences such as an unfetched or
missing remote branch.

#### Scenario: A destructive migration is blocked
- **WHEN** a migration drops a column with no maintenance-mode override and
  is not present in the committed baseline
- **THEN** the check fails, identifying the destructive operation

#### Scenario: An explicitly marked maintenance-mode migration is allowed
- **WHEN** a migration is marked as an explicit maintenance-mode change with
  a justification
- **THEN** the check allows it despite containing a destructive operation

#### Scenario: A baselined migration does not re-trigger the check
- **WHEN** a migration's destructive operation is present in the committed
  baseline file
- **THEN** the check does not fail because of that operation, regardless of
  which branch or commit it's run against

#### Scenario: The check requires no git ref
- **WHEN** the check runs locally without network access or a fetched
  `origin/main`
- **THEN** it still runs to completion and produces the same verdict CI
  would produce for the same working tree and baseline file
