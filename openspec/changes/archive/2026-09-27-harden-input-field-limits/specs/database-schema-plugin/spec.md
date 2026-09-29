## MODIFIED Requirements

### Requirement: Resource may carry a Database Schema facet
A Resource entity SHALL be able to carry a `DatabaseSchema` Facet storing a user-selected `dialect` (PostgreSQL, MySQL, or MS SQL), `source_sql`, a tbls-compatible parsed schema structure, and a parse status. The dialect SHALL be selectable on the same Schema tab where `source_sql` is edited, and saved together with it. `source_sql` SHALL be bounded to a fixed maximum length.

#### Scenario: Attaching a schema to a Resource
- **WHEN** a user selects a dialect and attaches `source_sql` to a Resource
- **THEN** the facet stores the SQL, the selected dialect, and the parsed schema structure

#### Scenario: Selecting a non-default dialect
- **WHEN** a user selects MySQL or MS SQL as the dialect before saving `source_sql`
- **THEN** the facet parses the SQL using that dialect and stores the result

#### Scenario: Oversized source_sql is rejected
- **WHEN** a user attempts to save `source_sql` longer than its declared maximum length
- **THEN** the request is rejected with a validation error and the facet's stored `source_sql` is unchanged
