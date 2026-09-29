## MODIFIED Requirements

### Requirement: Reading a Flow surfaces live status of referenced Endpoints/Operations

When a Flow is read (list or detail), for each step carrying a non-empty `query_ref`/`event_ref`, the response SHALL additionally include the current `status` (`active`/`removed`) of the referenced Endpoint/Operation, and, for a `query_ref`, its current `deprecated` flag — resolved at read time via `atlas_plugin_apis.extension_points.resolve_endpoint`/`resolve_operation`, the same functions already used to validate `query_ref`/`event_ref` on save. This SHALL NOT modify the step's stored `query_ref`/`event_ref` snapshot (`method`/`path`/`direction`/`channel`/`summary` remain exactly as captured when the reference was chosen); the live status is additional, computed information, not a replacement for the snapshot. When the referenced Endpoint/Operation no longer resolves at all (e.g. it was hard-deleted via its owning API's deletion), the read SHALL still succeed, presenting the step's stored snapshot without a live status rather than failing the Flow read. When the running distribution does not have `atlas.apis` installed, reading a Flow containing `query_ref`/`event_ref` steps SHALL still succeed, presenting each such step's stored snapshot without a live status.

For an `event_ref` whose resolved Operation currently resolves, the response SHALL additionally include the Operation's current `direction` and `channel_address` whenever either disagrees with the step's stored `event_ref.direction`/`event_ref.channel` — this is additional, computed information alongside `status`/`deprecated`, not a replacement for the stored snapshot, and follows the same never-mutate-the-snapshot rule as the rest of this requirement. No equivalent comparison is made for `method`/`path`: an `ApiEndpoint`'s `(method, path)` is its own upsert identity, so a `query_ref` snapshot's `method`/`path` cannot disagree with its resolved Endpoint's current values.

For either a `query_ref` or an `event_ref` whose resolved Endpoint/Operation currently resolves, the response SHALL additionally include that Endpoint's/Operation's current `summary` whenever it disagrees with the step's stored `query_ref.summary`/`event_ref.summary` (flow-editor-structural-integrity design.md Decision 7's second addendum) — independently of the `direction`/`channel` comparison above, since an Endpoint's/Operation's `summary` is an ordinary mutable field with no upsert-identity guarantee (unlike `method`/`path`), so it can drift the same way `event_ref.direction`/`event_ref.channel` already could, and can do so whether or not `direction`/`channel` also drifted.

#### Scenario: Reading a Flow reports a removed Endpoint's current status

- **WHEN** a Flow containing a step whose `query_ref` resolves to an Endpoint with `status: removed` is read
- **THEN** the response includes that step's stored `query_ref` snapshot unchanged, plus the Endpoint's current `status: removed`

#### Scenario: Reading a Flow reports a deprecated Endpoint's current status

- **WHEN** a Flow containing a step whose `query_ref` resolves to an Endpoint with `deprecated: true` is read
- **THEN** the response includes that step's stored `query_ref` snapshot unchanged, plus `deprecated: true`

#### Scenario: Reading a Flow reports a removed Operation's current status

- **WHEN** a Flow containing a step whose `event_ref` resolves to an Operation with `status: removed` is read
- **THEN** the response includes that step's stored `event_ref` snapshot unchanged, plus the Operation's current `status: removed`

#### Scenario: Reading a Flow with an active, non-deprecated, non-drifted reference reports current status only

- **WHEN** a Flow containing a step whose `query_ref` resolves to an Endpoint that is `active`, not deprecated, and whose current `summary` matches the stored snapshot, is read
- **THEN** the response reflects that active, non-deprecated status alongside the unchanged stored snapshot, with no drift reported

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

#### Scenario: Reading a Flow never reports a drifted method/path for a query_ref

- **WHEN** a Flow containing a step whose `query_ref` resolves to an Endpoint is read
- **THEN** the response never includes a drifted `method`/`path` for that step, regardless of the resolved Endpoint's current values (only `summary` can be reported as drifted for a `query_ref`)

#### Scenario: Reading a Flow reports a query_ref's summary drift

- **WHEN** a Flow containing a step whose `query_ref.summary` is `"List orders"` is read, and the resolved Endpoint's current `summary` is `"List all orders"`
- **THEN** the response includes that step's stored `query_ref` snapshot unchanged, plus the Endpoint's current `summary: "List all orders"`

#### Scenario: Reading a Flow reports an event_ref's summary drift independent of direction/channel

- **WHEN** a Flow containing a step whose `event_ref.summary` is `"Old summary"` is read, its `direction`/`channel` match the resolved Operation's current values, and the resolved Operation's current `summary` is `"New summary"`
- **THEN** the response includes that step's stored `event_ref` snapshot unchanged, plus the Operation's current `summary: "New summary"`, with no drifted `direction`/`channel_address` reported

#### Scenario: Reading a Flow reports no summary drift when the stored summary matches

- **WHEN** a Flow containing a step whose `query_ref.summary`/`event_ref.summary` exactly matches its resolved Endpoint's/Operation's current `summary` (including when both are blank) is read
- **THEN** the response includes that step's stored snapshot, with no drifted `summary` reported for it
