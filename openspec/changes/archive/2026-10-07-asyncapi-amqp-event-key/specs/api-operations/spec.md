## ADDED Requirements

### Requirement: An Operation's channel address is the event name shared across APIs
An Operation's `channel_address` SHALL be the name under which the same real-world event is addressed in every API document that mentions it. Operations from different APIs sharing a `channel_address` SHALL be treated as describing one event, whichever of them publishes and whichever subscribes.

#### Scenario: Publisher and subscribers of one event share an address
- **WHEN** API X has a `send` Operation, and APIs Y and Z each have a `receive` Operation, all with `channel_address` `rk-a`
- **THEN** the three Operations are treated as one event with one publisher and two subscribers

### Requirement: An Operation records how its event is delivered
An Operation SHALL carry a `delivery` object holding any of `exchange`, `queue` and `vhost`, defaulting to an empty object. `delivery` SHALL describe the delivery channel only and SHALL NOT take part in an Operation's identity, its `operation_key`, or its grouping by `channel_address`. The Operation read model SHALL expose `delivery`.

#### Scenario: Delivery is exposed with the Operation
- **WHEN** an Operation with `delivery` `{"queue": "queue-1"}` is read through the API
- **THEN** the response includes that `delivery` object

#### Scenario: Delivery does not affect grouping
- **WHEN** two Operations in one API share a `channel_address` and differ in `delivery`
- **THEN** they are listed in the same channel section
