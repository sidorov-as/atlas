## ADDED Requirements

### Requirement: An AMQP adapter derives the event key from the operation's cc binding
For a document whose operation uses the AMQP protocol, the importer SHALL derive the Operation's `channel_address` from the operation's `bindings.amqp.cc`, not from the channel's own address. In a 3.x document `cc` is a list on the `operations` entry; in a 2.x document `cc` is a string on the channel's `publish` or `subscribe` block; both shapes SHALL be accepted. Values SHALL be trimmed. A value that is empty or whitespace-only SHALL be treated as absent. When the operation has no usable `cc`, `channel_address` SHALL be the channel's own address (for 3.x the channel's `address`, for 2.x the channel key), exactly as before this requirement. Values containing wildcard characters (`*`, `#`) SHALL be stored as literal strings without pattern matching. The event key SHALL be the `cc` value alone; the exchange SHALL NOT take part in it. Operations whose protocol is not AMQP SHALL keep their current `channel_address`.

#### Scenario: A 3.x publisher on an exchange channel takes the cc as its event key
- **WHEN** a 3.x operation `action: send` references a channel whose address is the exchange name and whose operation binding is `cc: ["rk-a"]`
- **THEN** the resulting `ApiOperation.channel_address` is `rk-a`

#### Scenario: A 3.x subscriber on a queue channel takes the cc as its event key
- **WHEN** a 3.x operation `action: receive` references a channel whose address is the queue name and whose operation binding is `cc: ["rk-a"]`
- **THEN** the resulting `ApiOperation.channel_address` is `rk-a`, the same value as the publisher's

#### Scenario: A 2.x block with a string cc takes it as its event key
- **WHEN** a 2.x channel keyed `rk-a:exchange-1:Publisher` has a `publish` block with `bindings.amqp.cc` equal to the string `rk-a`
- **THEN** the resulting `ApiOperation.channel_address` is `rk-a`, not the composite channel key

#### Scenario: An empty cc falls back to the channel address
- **WHEN** an operation's `cc` is `[""]`, `""`, or whitespace only
- **THEN** its `channel_address` is the channel's own address

#### Scenario: A missing cc falls back to the channel address
- **WHEN** an AMQP operation has no `bindings.amqp.cc`
- **THEN** its `channel_address` is the channel's own address

#### Scenario: A wildcard cc is kept as a literal
- **WHEN** an operation's `cc` is `["orders.event.#"]`
- **THEN** its `channel_address` is `orders.event.#` and it is not matched against concrete keys by pattern

#### Scenario: The exchange does not participate in the event key
- **WHEN** two operations in different documents carry the same `cc` and different exchanges, or one of them has no exchange in its document
- **THEN** both resulting Operations have the same `channel_address`

#### Scenario: A non-AMQP document keeps its channel address
- **WHEN** a document's servers declare a protocol other than `amqp`
- **THEN** every Operation's `channel_address` is the channel's own address, with no cc consulted

### Requirement: operation_key does not depend on the event key
The importer SHALL derive `operation_key` exactly as before, independently of the AMQP adapter: the `operations` map key for 3.x, and the channel key plus the mapped direction for 2.x. Changing an Operation's `channel_address` through the adapter SHALL NOT change its `operation_key`.

#### Scenario: A 3.x operation keeps its map key
- **WHEN** a 3.x document's operation under key `exchange-1` has `cc: ["rk-a"]`
- **THEN** its `operation_key` is `exchange-1` and its `channel_address` is `rk-a`

#### Scenario: A 2.x operation keeps its channel key and direction
- **WHEN** a 2.x document's `rk-a:exchange-1:Publisher` channel has a `publish` block with `cc` equal to `rk-a`
- **THEN** its `operation_key` is derived from `rk-a:exchange-1:Publisher` and `receive`, not from `rk-a`

#### Scenario: A publisher and a listener of one key in one 2.x document do not collide
- **WHEN** one 2.x document has channels `rk-a:exchange-1:Publisher` and `rk-a:exchange-1:HandleEvent` with the same `cc`
- **THEN** two Operations are created with distinct `operation_key` values and the same `channel_address`

#### Scenario: Re-import after an event-key change updates the row in place
- **WHEN** an existing `ApiOperation` has the same `operation_key` as a re-parsed operation but a different `channel_address`
- **THEN** the row is updated in place, keeping its `id` and any `ServiceOperationUsage` links

### Requirement: Delivery details are imported from the channel's AMQP bindings
For an AMQP operation, the importer SHALL populate `ApiOperation.delivery` with a single object holding any of `exchange` (the channel's `bindings.amqp.exchange.name`), `queue` (the channel's `bindings.amqp.queue.name`) and `vhost` (from either binding), taken from the channel the operation references. Keys with no value in the document SHALL be omitted; an operation with none of them SHALL store an empty object. `delivery` SHALL be refreshed on every successful sync, like the other document-owned fields.

#### Scenario: An exchange channel records the exchange and vhost
- **WHEN** a channel has `bindings.amqp` with `exchange: { name: "exchange-1", vhost: "vhost-1" }`
- **THEN** the Operation's `delivery` is `{"exchange": "exchange-1", "vhost": "vhost-1"}`

#### Scenario: A queue channel records the queue and has no exchange
- **WHEN** a channel has `bindings.amqp` with `queue: { name: "queue-1", vhost: "vhost-1" }` and no exchange
- **THEN** the Operation's `delivery` is `{"queue": "queue-1", "vhost": "vhost-1"}`

#### Scenario: A channel without AMQP bindings stores an empty delivery
- **WHEN** an operation's channel has no `bindings.amqp`
- **THEN** the Operation's `delivery` is `{}`

#### Scenario: Delivery follows the document on re-import
- **WHEN** a re-parsed operation's queue name differs from the stored `delivery.queue`
- **THEN** `delivery` is updated in place and the row's `id` is unchanged
