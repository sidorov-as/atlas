## ADDED Requirements

### Requirement: The participant summary carries its system
The Service summary returned with an Operation's linked Services and channel participants SHALL include the Service's system reference, id and display name, or null when the Service has none.

#### Scenario: Participant with a system
- **WHEN** a channel participant belongs to the system "core"
- **THEN** its summary carries that system's reference, id and name

#### Scenario: Participant without a system
- **WHEN** a channel participant has no system
- **THEN** its system fields are null

### Requirement: The Service summary tolerates a Service without an owner
The Service summary returned with an Operation's linked Services and channel participants SHALL carry null team reference, id and name for a Service that has no owner, instead of failing the request.

#### Scenario: Participant without an owner
- **WHEN** a channel participant has no owner
- **THEN** the response succeeds and its team fields are null

### Requirement: The channel participants data can be grouped by team or system per role
The Operation consumers API SHALL accept `group_by` with the value `team` or `system`. With `group_by` and without `group_id`, the response SHALL include `publisherGroups` and `subscriberGroups`, each listing the teams or systems that hold at least two participants of that role matching `search`, with id, name and the number of matching participants of that role, ordered by name; the participants list SHALL then contain only matching participants not in a listed group of their own role, paginated and ordered as before, and `count` SHALL still be the total of all matching participants while `participantsCount` SHALL give the size of that list's remainder. With `group_by`, `group_id` and `role`, the response SHALL be the page of matching participants of that role in that group, with `count` set to that total. A request with `group_id` and without `role` SHALL be rejected as a validation error. Without `group_by`, the response SHALL be as before and SHALL NOT include group lists or `participantsCount`. An unsupported `group_by` value SHALL be rejected as a validation error. Document-owner implied roles SHALL be grouped like any other participant.

#### Scenario: Groups per role
- **WHEN** a channel has publishers from 3 teams with at least two Services each and subscribers from 4 such teams, and consumers are requested with `group_by=team`
- **THEN** `publisherGroups` lists 3 teams and `subscriberGroups` lists 4 teams, each with its role's count

#### Scenario: The same team on both sides
- **WHEN** a team has 3 publishers and 2 subscribers on the channel
- **THEN** it appears in `publisherGroups` with a count of 3 and in `subscriberGroups` with a count of 2

#### Scenario: Group members by group id and role
- **WHEN** consumers are requested with `group_by=team`, `group_id` of a team and `role=subscriber`
- **THEN** the response contains that team's subscribers on the channel and a count equal to their number

#### Scenario: Group id without role
- **WHEN** consumers are requested with `group_id` and no `role`
- **THEN** the response is a validation error

#### Scenario: Search narrows group counts
- **WHEN** consumers are requested with `group_by=team` and `search=notif` and 1 of a team's 3 subscribers matches
- **THEN** that team's entry in `subscriberGroups` is omitted if fewer than two matching participants remain, and its remaining participant is returned in the participants list

#### Scenario: No grouping requested
- **WHEN** consumers are requested without `group_by`
- **THEN** the response has no group lists and is otherwise unchanged

#### Scenario: Document-owner implied publisher is grouped
- **WHEN** the channel's provider Service is the implied publisher and shares a team with another publisher
- **THEN** both are counted in that team's publisher group
