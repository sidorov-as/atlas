## RENAMED Requirements
- FROM: `### Requirement: Message payload schema is stored unresolved`
- TO: `### Requirement: Message identity and payload schema are resolved against the document's own components`

## MODIFIED Requirements

### Requirement: Message identity and payload schema are resolved against the document's own components
When a channel's message reference — a channel's `messages.<name>` entry (whether reached via an operation's `messages[]` entry or, absent any `messages[]` narrowing, taken as one of "every message this channel defines"), or (for 2.x) a `publish`/`subscribe`/`oneOf` message field — is itself an unresolved `$ref` rather than the real Message Object, the parser SHALL dereference it against the same document (typically into `components.messages`), following as many further `$ref` hops as the document actually chains, to find the real message object before mapping it. Whether a node is "the real Message Object" or "still a reference" is determined structurally (does it carry a `$ref` key), not by whether it happens to have a `payload` — every Message Object field, including `payload`, is optional per AsyncAPI's own spec, so a message with only a `name`/`title`/`summary` and no `payload` is still the real object, not a reference waiting to be resolved further. A message's payload schema that is (or contains) a `$ref` SHALL be resolved against the document's `components.schemas`, recursively; sibling keys next to that `$ref` are discarded (not merged — AsyncAPI's Reference Object semantics, both 2.x and 3.0, treat sibling keys as meaningless). The only cases where a `$ref` is left unresolved (schema) or a message reference yields a name-only stub (identity) are: the pointer does not resolve to anything defined in the document, or resolving it would re-enter a `$ref` already being expanded along the same resolution path (a reference cycle) — this applies equally to a single hop and to a chain of several.

#### Scenario: A message payload that is a $ref is resolved
- **WHEN** an operation's message payload is `{"$ref": "#/components/schemas/BookingConfirmed"}` and `#/components/schemas/BookingConfirmed` is an inline object schema
- **THEN** the resulting `ApiOperation` message's schema has that schema's expanded `type`/`properties`/`required`, not the bare `$ref` string

#### Scenario: A channel's message-map entry that is itself a $ref is dereferenced
- **WHEN** a 3.0 channel's `messages.<name>` entry is `{"$ref": "#/components/messages/OrderCreated"}` and `#/components/messages/OrderCreated` is an inline message object with a `payload`
- **THEN** an operation referencing that channel message's resulting entry has the real message's `name`/`payload`/`summary`, not a name-only stub with no schema

#### Scenario: A 2.x bare-$ref message field is dereferenced
- **WHEN** a 2.x channel's `publish`/`subscribe`/`oneOf` `message` field is `{"$ref": "#/components/messages/X"}` and `#/components/messages/X` is an inline message object with a `payload`
- **THEN** the resulting message entry has that message's real `name`/`payload`, the same as the equivalent 3.0 case, instead of an entry with an empty `name` and no schema

#### Scenario: A genuinely unresolvable message reference still yields a name-only entry
- **WHEN** a message reference's `$ref` points at something not defined anywhere in the document
- **THEN** the resulting message entry falls back to a name derived from the `$ref`'s last path segment, with no schema or example, exactly as today

#### Scenario: A multi-hop message reference chain is fully dereferenced
- **WHEN** a channel's `messages.<name>` entry is `{"$ref": "#/components/messages/A"}`, `#/components/messages/A` is itself `{"$ref": "#/components/messages/B"}`, and `#/components/messages/B` is an inline message object with a `payload`
- **THEN** the resulting message entry has `B`'s real `name`/`payload`, following both hops, not just the first

#### Scenario: A message-identity reference cycle stops without looping
- **WHEN** a channel's `messages.<name>` entry is `{"$ref": "#/components/messages/A"}` and `#/components/messages/A` is `{"$ref": "#/components/messages/B"}` whose own value is `{"$ref": "#/components/messages/A"}` (a cycle between `A` and `B`, neither ever inline)
- **THEN** dereferencing stops at the point the cycle is detected and falls back to a name-only entry, the same shape as a dangling reference, without looping or raising

#### Scenario: A channel's implicit message set dereferences $ref entries too
- **WHEN** an operation has no `messages[]` narrowing (so every message the channel defines is in scope) and one of the channel's `messages.<name>` entries is itself `{"$ref": "#/components/messages/OrderCreated"}` pointing at an inline message object with a `payload`
- **THEN** that message is included in the operation's message list with its real payload, not silently omitted for lacking an inline `payload` at the channel-map-entry level

#### Scenario: A self-referential schema stops at the cycle, not before
- **WHEN** a message payload schema has a property whose own (possibly nested) `$ref` chain would resolve back to a schema currently being expanded on the same path
- **THEN** resolution expands normally up to that point, and that occurrence is left as an unresolved `{"$ref": ...}` node instead of recursing again

#### Scenario: A sibling key next to a message payload's $ref is not preserved
- **WHEN** a message's payload is `{"$ref": "#/components/schemas/OrderCreated", "description": "override"}`
- **THEN** the resulting schema is `OrderCreated`'s expanded content only — the sibling `description` is discarded, matching AsyncAPI's own Reference Object semantics (contrast with the OpenAPI-side scenario, where sibling keys are merged)

#### Scenario: A sibling key does not survive a cycle or dangling message reference either
- **WHEN** a message reference resolves through a cycle or a dangling pointer, and the unresolved `$ref` node that triggered that outcome happened to carry an extra key alongside `$ref`
- **THEN** the resulting stub carries no leftover sibling content — AsyncAPI's discard-siblings behavior applies the same way whether the reference resolves, cycles, or dangles, not only on the successful-resolve path

#### Scenario: A Message Object with no payload is still the final object, not a stub
- **WHEN** a channel's `messages.<name>` entry (or, absent any `messages[]` narrowing, one of the channel's implicit message set) resolves — after zero or more `$ref` hops — to an inline Message Object that has only `name`/`title`/`summary` fields and no `payload` at all
- **THEN** the resulting message entry has that real `name`/`title`/`summary` with `schema: None`, not a name-only stub and not an entry silently omitted from the message list — the absence of `payload` is not mistaken for "still an unresolved reference"

#### Scenario: A $ref inside example/default/enum/const data is never touched
- **WHEN** a message payload schema has an `example` (or `examples[].payload`, `default`, `enum`, or `const`) value that itself contains a key literally named `$ref` (e.g. `example: {"$ref": "not-a-reference"}`), as arbitrary data an author wrote, not a schema reference
- **THEN** that value is stored exactly as written, untouched by resolution — only `properties`/`items`/`additionalProperties`/`allOf`/`oneOf`/`anyOf`/`not` are ever walked looking for a `$ref` to resolve
