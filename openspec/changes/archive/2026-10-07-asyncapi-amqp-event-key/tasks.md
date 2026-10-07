## 1. Model and schema

- [x] 1.1 Add `delivery` (JSON object, default empty) to `ApiOperation` and a migration
- [x] 1.2 Add `delivery` to the importer-owned fields list used by the upsert, so it is refreshed on every sync
- [x] 1.3 Expose `delivery` in the Operation read schemas (API and MCP) and the frontend Operation type

## 2. AMQP adapter in the import

- [x] 2.1 Add the adapter: returns the event key and the `delivery` object for an AMQP operation, accepting `cc` as a list or a string, trimming, ignoring empty values, treating wildcards as literals
- [x] 2.2 Apply it in the 3.x path (operation `bindings.amqp.cc`, channel `bindings.amqp` for exchange, queue, vhost)
- [x] 2.3 Apply it in the 2.x path (the `publish`/`subscribe` block's `bindings.amqp.cc`, channel bindings for delivery)
- [x] 2.4 Bind the adapter to AMQP: skip it for other protocols; when the protocol is unresolved, apply it only if the operation carries `bindings.amqp`
- [x] 2.5 Fall back to the channel's own address when no usable `cc` exists
- [x] 2.6 Keep `operation_key` derivation unchanged in both paths

## 3. Graph aggregation

- [x] 3.1 Restrict the channel aggregation in `OperationConsumersController` to `status=active` Operations
- [x] 3.2 Make `channel_participants` and any other caller of the aggregation consistent with it (extension points, MCP usage views)

## 4. Tests

- [x] 4.1 Import tests, 3.x: publisher on an exchange channel, subscriber on a queue channel, shared key, `delivery` for each, missing and empty `cc`
- [x] 4.2 Import tests, 2.x: string `cc`, composite channel key, publisher and listener of one key in one document, distinct `operation_key` values
- [x] 4.3 Import tests: wildcard kept literal, non-AMQP document untouched, exchange not part of the key, in-place update on re-import keeps `id` and links
- [x] 4.4 Graph tests: three Operations from three APIs on one key produce one publisher and two subscribers; a removed Operation is excluded and a revived one returns
- [x] 4.5 Update existing tests and the demo seed that assume `channel_address` equals the document's channel address for AMQP documents
- [x] 4.6 Acceptance check on the reference documents: the four known events show 5/8, 5/5, 3/2 and 0/2 publishers/subscribers

## 5. Documentation

- [x] 5.1 Update the plugin docs and any import description to state that AMQP Operations are grouped by the `cc` event key and that exchange, queue and vhost are in `delivery`
- [x] 5.2 Record the known limits: wildcard keys are not matched, equal keys on different exchanges merge, events a generator dropped from its documents cannot be recovered
