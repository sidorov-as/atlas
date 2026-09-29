## ADDED Requirements

### Requirement: Message headers schema is resolved against the document's own components
A message's `headers` (a Schema Object, present in both AsyncAPI 2.x and 3.0) that is (or contains) a `$ref` SHALL be resolved against the document's `components.schemas`, recursively, via the same shared resolver `payload` already uses (`resolve-spec-refs`'s `spec_refs.resolve_schema`, `merge_siblings=False` default). A message with no `headers` field SHALL yield no `headers` entry (not an empty-object placeholder).

#### Scenario: A message headers schema that is a $ref is resolved
- **WHEN** a message's `headers` is `{"$ref": "#/components/schemas/EventEnvelope"}` and `#/components/schemas/EventEnvelope` is an inline object schema
- **THEN** the resulting `ApiOperation` message's `headers` has that schema's expanded `type`/`properties`/`required`, not the bare `$ref` string

#### Scenario: A message with no headers yields no headers entry
- **WHEN** a message has no `headers` field at all
- **THEN** the resulting message entry's `headers` is absent/`None`, not an empty schema object

#### Scenario: A self-referential headers schema stops at the cycle, not before
- **WHEN** a message's `headers` schema has a property whose own (possibly nested) `$ref` chain would resolve back to a schema currently being expanded on the same path
- **THEN** resolution expands normally up to that point, and that occurrence is left as an unresolved `{"$ref": ...}` node instead of recursing again, identical to how `payload` already degrades

### Requirement: Operation externalDocs is imported when present
An Operation Object's `externalDocs` (`{description?, url}`, present identically in both AsyncAPI 2.x and 3.0) SHALL be parsed into the resulting `ApiOperation.external_docs`. An operation with no `externalDocs`, or an `externalDocs` object missing `url`, SHALL yield an empty `external_docs`.

#### Scenario: Operation externalDocs is imported
- **WHEN** an operation (either AsyncAPI version) has an `externalDocs` object with a `url` and a `description`
- **THEN** the resulting `ApiOperation.external_docs` has that `url` and `description`

#### Scenario: Operation externalDocs without a url is dropped
- **WHEN** an operation's `externalDocs` object has a `description` but no `url`
- **THEN** the resulting `ApiOperation.external_docs` is empty, and the rest of the operation still imports normally

#### Scenario: A malformed headers or externalDocs block does not abort the operation's import
- **WHEN** a channel/operation's `headers` or `externalDocs` block is malformed in a way that raises during parsing
- **THEN** that one channel/operation is logged and skipped, and the rest of the spec's operations still import normally, matching this parser's existing "one bad operation doesn't blank the API" posture
