## MODIFIED Requirements

### Requirement: Scout hands an approved plan to the curator
After the interview `atlas-scout` SHALL present the proposed plan in the conversation, listing every entity, relationship, and Endpoint or Operation link with its status, and SHALL hand the plan to `atlas-curator` for the write only after the user approves it. It SHALL write a plan file only if the user asks for one.

#### Scenario: Plan is approved
- **WHEN** the user approves the plan
- **THEN** the skill passes it to `atlas-curator` and does not itself create any entity

#### Scenario: Plan is declined
- **WHEN** the user rejects or wants to change the plan
- **THEN** the skill revises it and writes nothing

## ADDED Requirements

### Requirement: Scout plans Endpoint and Operation links from call sites it finds
When `atlas-scout` finds in the code an HTTP client call that matches a cataloged Endpoint, or a message publish or subscribe that matches a cataloged Operation's channel, it SHALL add a link row to the plan: the Service, the target (API with method and path, or API with channel and direction), and for an operation the role. It SHALL take the target from the catalog's `search_api_endpoints` or `search_api_operations` rather than infer it, and SHALL list a call site with no matching Endpoint or Operation under what it could not determine. It MAY show the code location of the call site next to the row for the reviewer; the location is text in the plan and is not recorded in the catalog.

#### Scenario: Client call matched to an endpoint
- **WHEN** a service's code calls `GET /bookings/{id}` and `api:booking` has that Endpoint
- **THEN** the plan lists a link row from that Service to the Endpoint, with the code location shown as text

#### Scenario: Publisher found
- **WHEN** code publishes to a queue that an AsyncAPI document in the catalog declares as a channel
- **THEN** the plan lists a link row with the role `publisher`

#### Scenario: No matching endpoint
- **WHEN** a call site matches no Endpoint or Operation in the catalog
- **THEN** it appears under what could not be determined, not as a link row

#### Scenario: Existing link is shown as unchanged
- **WHEN** the catalog already links the Service to that target
- **THEN** the plan marks the row as unchanged
