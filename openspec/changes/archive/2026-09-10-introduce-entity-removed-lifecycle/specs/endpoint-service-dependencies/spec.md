## ADDED Requirements

### Requirement: Linked Services reflects a deprecated endpoint's status
An Endpoint's Linked Services tab and consumers graph SHALL show a visible warning when the Endpoint itself is `deprecated`, alongside (and independent of) the existing warning shown for a `removed` Endpoint, so a consumer of a still-active-but-deprecated Endpoint sees the same signal an Endpoint's own detail page already shows.

#### Scenario: Linked Services warns for a deprecated endpoint
- **WHEN** a `deprecated` (but still `active`) Endpoint's Linked Services tab is viewed and it has linked Services
- **THEN** the tab displays a warning that the endpoint is deprecated, distinct from the removed-endpoint warning

#### Scenario: Deprecated and removed warnings are distinguishable
- **WHEN** an Endpoint is both `deprecated` and `removed`
- **THEN** its Linked Services tab shows both warnings, visually distinguished from one another
