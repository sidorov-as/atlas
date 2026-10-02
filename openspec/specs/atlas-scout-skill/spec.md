# atlas-scout-skill Specification

## Purpose

The `atlas-scout` skill: surveys a codebase, interviews the user, and hands an approved catalog plan to `atlas-curator` (TBD: refine).

## Requirements

### Requirement: Scout surveys the codebase before asking questions
`atlas-scout` SHALL read the codebase the user designates, confirming scope first when it is a monorepo, and SHALL form a candidate model of systems, components (with type), resources (with type), APIs, and relationships before asking any structural question. It SHALL treat a plain library, a deployable service, a web frontend, and a background worker as distinct and SHALL map message brokers and data stores to Resources.

#### Scenario: Scope is confirmed for a monorepo
- **WHEN** the designated directory holds several independently deployable units
- **THEN** the skill confirms whether to cover the whole repository or a subdirectory before surveying

#### Scenario: Evidence is retained
- **WHEN** the skill proposes a candidate entity
- **THEN** it records the file path and line that support it

### Requirement: Scout reconciles with the existing catalog
`atlas-scout` SHALL look up existing catalog entities through the MCP server and assign each candidate a status of `new`, `update`, `unchanged`, or `investigate`, matching on kind and name first and on similar names second. An existing entity with no counterpart in the code SHALL be marked `investigate` and SHALL NOT be proposed for removal.

#### Scenario: Existing entity is recognized
- **WHEN** a candidate matches an entity already in the catalog
- **THEN** it is marked `update` if the code differs from the catalog and `unchanged` otherwise, and is not proposed as a new entity

#### Scenario: Stale entity is flagged
- **WHEN** a catalog entity in the surveyed system has no counterpart in the code
- **THEN** it is marked `investigate` and left untouched

### Requirement: Scout interviews only on structural decisions, one question at a time
`atlas-scout` SHALL ask only about decisions that change the catalog's structure: system boundaries, which units are components and of what type, which stores are resources and of what type, which interfaces are APIs and whether a spec is available, who owns each system, and how components relate. It SHALL ask one question at a time, each with a recommended answer and its supporting evidence, and SHALL NOT ask about titles, descriptions, or tags.

#### Scenario: Question carries a recommendation
- **WHEN** the skill asks a structural question
- **THEN** the question states the recommended answer and the evidence behind it

#### Scenario: Cosmetic fields are not asked about
- **WHEN** the skill needs a title or description for an entity
- **THEN** it drafts one from the code and does not ask the user

### Requirement: Scout hands an approved plan to the curator
After the interview `atlas-scout` SHALL present the proposed plan in the conversation, listing every entity, relationship, and Endpoint or Operation link with its status, and SHALL hand the plan to `atlas-curator` for the write only after the user approves it. It SHALL write a plan file only if the user asks for one.

#### Scenario: Plan is approved
- **WHEN** the user approves the plan
- **THEN** the skill passes it to `atlas-curator` and does not itself create any entity

#### Scenario: Plan is declined
- **WHEN** the user rejects or wants to change the plan
- **THEN** the skill revises it and writes nothing

### Requirement: Scout reports what it could not determine
When the code does not settle a question, such as whether a component is a service or a worker, `atlas-scout` SHALL say so, ask the user, and SHALL NOT silently choose.

#### Scenario: Ambiguity becomes a question
- **WHEN** the evidence for a component's type is ambiguous
- **THEN** the skill marks it uncertain and asks the user to decide

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
