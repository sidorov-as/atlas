## ADDED Requirements

### Requirement: Candidates may carry highlight match offsets
An engine that supplies highlights MAY return, with a candidate's plain-text highlight, the offsets of the query matches within that highlight as ordered `[start, end)` ranges counted in Unicode code points relative to the highlight text. The highlight text SHALL be final: the offsets SHALL stay valid without any further transformation of it. Offsets SHALL lie within the highlight text, SHALL be ordered by start, SHALL NOT overlap, and SHALL NOT be empty ranges. A candidate without offsets SHALL remain valid, and an engine that does not supply highlights SHALL NOT be required to return offsets.

#### Scenario: Engine supplies offsets
- **WHEN** an engine that supplies highlights returns a candidate with a highlight and match offsets
- **THEN** each offset range denotes a matched span of that highlight text

#### Scenario: Engine supplies no offsets
- **WHEN** an engine returns a candidate with a highlight and no offsets
- **THEN** the candidate is accepted and behaves as it did before offsets existed

#### Scenario: Invalid offsets
- **WHEN** a candidate carries offsets that are out of range, unordered, overlapping or empty
- **THEN** the candidate is rejected as invalid at construction
