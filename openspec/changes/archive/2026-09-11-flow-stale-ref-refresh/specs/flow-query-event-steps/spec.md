## MODIFIED Requirements

### Requirement: Reading a Flow surfaces live status of referenced Endpoints/Operations

When a Flow is read (list or detail), for each step carrying a non-empty `query_ref`/`event_ref`, the response SHALL additionally include the current `status` (`active`/`removed`) of the referenced Endpoint/Operation, and, for a `query_ref`, its current `deprecated` flag — resolved at read time via `atlas_plugin_apis.extension_points.resolve_endpoint`/`resolve_operation`, the same functions already used to validate `query_ref`/`event_ref` on save. This SHALL NOT modify the step's stored `query_ref`/`event_ref` snapshot (`method`/`path`/`direction`/`channel` remain exactly as captured when the reference was chosen); the live status is additional, computed information, not a replacement for the snapshot. When the referenced Endpoint/Operation no longer resolves at all (e.g. it was hard-deleted via its owning API's deletion), the read SHALL still succeed, presenting the step's stored snapshot without a live status rather than failing the Flow read. When the running distribution does not have `atlas.apis` installed, reading a Flow containing `query_ref`/`event_ref` steps SHALL still succeed, presenting each such step's stored snapshot without a live status.

For an `event_ref` whose resolved Operation currently resolves, the response SHALL additionally include the Operation's current `direction` and `channel_address` whenever either disagrees with the step's stored `event_ref.direction`/`event_ref.channel` — this is additional, computed information alongside `status`/`deprecated`, not a replacement for the stored snapshot, and follows the same never-mutate-the-snapshot rule as the rest of this requirement. No equivalent comparison is made for `query_ref`: an `ApiEndpoint`'s `(method, path)` is its own upsert identity, so a `query_ref` snapshot's `method`/`path` cannot disagree with its resolved Endpoint's current values.

#### Scenario: Reading a Flow reports a removed Endpoint's current status

- **WHEN** a Flow containing a step whose `query_ref` resolves to an Endpoint with `status: removed` is read
- **THEN** the response includes that step's stored `query_ref` snapshot unchanged, plus the Endpoint's current `status: removed`

#### Scenario: Reading a Flow reports a deprecated Endpoint's current status

- **WHEN** a Flow containing a step whose `query_ref` resolves to an Endpoint with `deprecated: true` is read
- **THEN** the response includes that step's stored `query_ref` snapshot unchanged, plus `deprecated: true`

#### Scenario: Reading a Flow reports a removed Operation's current status

- **WHEN** a Flow containing a step whose `event_ref` resolves to an Operation with `status: removed` is read
- **THEN** the response includes that step's stored `event_ref` snapshot unchanged, plus the Operation's current `status: removed`

#### Scenario: Reading a Flow with an active, non-deprecated reference reports current status

- **WHEN** a Flow containing a step whose `query_ref` resolves to an Endpoint that is `active` and not deprecated is read
- **THEN** the response reflects that active, non-deprecated status alongside the unchanged stored snapshot

#### Scenario: Reading a Flow whose reference no longer resolves at all does not fail the read

- **WHEN** a Flow containing a step whose `query_ref.endpoint` no longer resolves to any Endpoint is read
- **THEN** the read succeeds, the step's stored `query_ref` snapshot is presented, and no live status is included for that step

#### Scenario: Reading a Flow with query_ref/event_ref steps succeeds without atlas.apis installed

- **WHEN** a Flow containing steps with `query_ref`/`event_ref` is read in a distribution that does not have `atlas.apis` installed
- **THEN** the read succeeds, each such step's stored snapshot is presented, and no live status is included for any of them

#### Scenario: Reading a Flow reports an Event's direction/channel drift

- **WHEN** a Flow containing a step whose `event_ref` is `{direction: "send", channel: "orders.created"}` is read, and the resolved Operation's current `direction`/`channel_address` is `receive`/`orders.events`
- **THEN** the response includes that step's stored `event_ref` snapshot unchanged, plus the Operation's current `direction: "receive"` and `channel_address: "orders.events"`

#### Scenario: Reading a Flow reports no drift when the Event snapshot still matches

- **WHEN** a Flow containing a step whose `event_ref` is `{direction: "send", channel: "orders.created"}` is read, and the resolved Operation's current `direction`/`channel_address` is unchanged (`send`/`orders.created`)
- **THEN** the response includes that step's stored `event_ref` snapshot, with no drifted `direction`/`channel_address` reported for it

#### Scenario: Reading a Flow never reports drift for a query_ref

- **WHEN** a Flow containing a step whose `query_ref` resolves to an Endpoint is read
- **THEN** the response never includes a drifted `method`/`path` for that step, regardless of the resolved Endpoint's current values
