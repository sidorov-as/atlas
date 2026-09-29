## ADDED Requirements

### Requirement: Linked Services reflects a deprecated operation's status
An Operation's Linked Services tab SHALL show a visible warning when the Operation itself is `deprecated` (via its manual override field), alongside (and independent of) the existing warning shown for a `removed` Operation.

#### Scenario: Linked Services warns for a deprecated operation
- **WHEN** a `deprecated` (but still `active`) Operation's Linked Services tab is viewed and it has linked Services
- **THEN** the tab displays a warning that the operation is deprecated, distinct from the removed-operation warning

#### Scenario: Deprecated and removed warnings are distinguishable
- **WHEN** an Operation is both `deprecated` and `removed`
- **THEN** its Linked Services tab shows both warnings, visually distinguished from one another
