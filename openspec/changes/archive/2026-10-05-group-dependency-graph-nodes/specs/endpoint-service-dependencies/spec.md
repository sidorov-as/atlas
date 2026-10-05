## ADDED Requirements

### Requirement: The Service summary carries its system
The Service summary returned with an Endpoint's linked Services and consumers SHALL include the Service's system reference, id and display name, or null when the Service has none.

#### Scenario: Service with a system
- **WHEN** a linked Service belongs to the system "core"
- **THEN** its summary carries that system's reference, id and name

#### Scenario: Service without a system
- **WHEN** a linked Service has no system
- **THEN** its system fields are null

### Requirement: The Service summary tolerates a Service without an owner
The Service summary returned with an Endpoint's linked Services and consumers SHALL carry null team reference, id and name for a Service that has no owner, instead of failing the request.

#### Scenario: Service without an owner
- **WHEN** a linked Service has no owner
- **THEN** the response succeeds and its team fields are null

### Requirement: The consumers data can be grouped by team or system
The Endpoint consumers API SHALL accept `group_by` with the value `team` or `system`. With `group_by` and without `group_id`, the response SHALL include `groups`, one entry per team or system that holds at least two Services matching `search`, each with its id, name and the number of matching Services, ordered by name; the Services list SHALL then contain only matching Services not in any listed group (those without a team or system for the grouping, and those alone in their group), paginated as before, and `count` SHALL still be the total of all matching Services (grouped ones included) while `servicesCount` SHALL give the size of that list's remainder. With `group_by` and `group_id`, the response SHALL be the page of matching Services in that group, with `count` set to the group's matching total. Without `group_by`, the response SHALL be as before and SHALL NOT include `groups` or `servicesCount`. An unsupported `group_by` value SHALL be rejected as a validation error.

#### Scenario: Group counts accompany the ungrouped Services
- **WHEN** an Endpoint has 18 linked Services owned by 5 teams, 2 of them alone in their team, and consumers are requested with `group_by=team`
- **THEN** the response lists the 3 teams with at least two Services with their counts and returns the 2 single Services in the Services list

#### Scenario: Group members by group id
- **WHEN** consumers are requested with `group_by=team` and `group_id` set to a team that owns 4 linked Services
- **THEN** the response contains those 4 Services and a count of 4

#### Scenario: Search narrows group counts
- **WHEN** consumers are requested with `group_by=team` and `search=pay`, and 2 of a team's 5 Services match
- **THEN** that team's entry reports a count of 2

#### Scenario: Group by system
- **WHEN** consumers are requested with `group_by=system`
- **THEN** groups are the systems of the linked Services and Services without a system appear in the Services list

#### Scenario: No grouping requested
- **WHEN** consumers are requested without `group_by`
- **THEN** the response has no `groups` and is otherwise unchanged

#### Scenario: Unsupported grouping
- **WHEN** consumers are requested with `group_by=tag`
- **THEN** the response is a validation error

#### Scenario: Group members exceeding a page
- **WHEN** a group has 70 Services and its members are requested without `page_size`
- **THEN** the response contains the first 50 and a count of 70
