# search-contract Specification

## Purpose
Engine-neutral document, source and engine contracts, registration, and selection of the engine in use.

## Requirements

### Requirement: The search contract is engine-neutral and plugin-owned
The Python plugin API SHALL define the search document, source, engine and hit types and the registration functions. The contract SHALL NOT name or depend on any concrete search engine, and a plugin SHALL be able to register a source without depending on the search plugin.

#### Scenario: A source registers when search is not installed
- **WHEN** a plugin registers a search source and no search plugin is selected
- **THEN** registration succeeds, nothing is indexed, and the plugin continues to work normally

#### Scenario: Contract has no engine dependency
- **WHEN** the plugin API package is imported
- **THEN** no search engine client library is imported or required

### Requirement: Documents have stable, self-sufficient identifiers
A search document SHALL carry a string id of the form `<kind>:<key>` unique across all sources, a `kind`, a `title`, and plain-text `body`. The id alone SHALL be sufficient for its source to load the live object.

#### Scenario: Id resolves to the live object
- **WHEN** a source receives a document id it previously produced
- **THEN** it can load the corresponding live object using only that id

#### Scenario: Duplicate document ids across sources
- **WHEN** two registered sources produce the same document id
- **THEN** composition or reconcile fails identifying the id and both sources

### Requirement: Document body size is bounded
The contract SHALL bound the size of a document's body, truncating at a word boundary and logging a warning when the bound is exceeded. A source MAY truncate earlier. The bound SHALL be configurable.

#### Scenario: Oversized body
- **WHEN** a source produces a body larger than the bound
- **THEN** the indexed body is truncated at a word boundary and a warning is logged

#### Scenario: Source truncates earlier
- **WHEN** a source limits its own body below the bound
- **THEN** the indexed body is the source's shorter text

### Requirement: Sources declare content, change tracking and authorization
A source SHALL declare the document kinds it owns, the models whose changes affect its documents, a mapping from a changed instance to the affected document ids, a way to produce documents for a list of ids or for everything, and a `resolve` operation that, given document ids and the requesting actor, returns live hits for accessible documents and no entry for inaccessible or missing ones.

#### Scenario: Resolve omits inaccessible documents
- **WHEN** `resolve` is called with ids of which the actor may read only some
- **THEN** only accessible documents are returned and the others are omitted without error

#### Scenario: A changed related model maps to its owner's document
- **WHEN** a watched model instance belongs to another object's document
- **THEN** the source's mapping returns the owning document's id so that document is reindexed

### Requirement: Engines expose a minimal portable interface
An engine SHALL support upserting documents, deleting by id, replacing the whole index atomically from a stream of documents, querying by text with an optional kind filter, limit and offset returning ordered candidate ids with scores, and reporting health. An engine SHALL declare capability flags, including whether it supplies highlights.

#### Scenario: Query returns ordered candidates
- **WHEN** an engine is queried with text
- **THEN** it returns candidate document ids ordered by relevance, each with a score

#### Scenario: Replace is atomic
- **WHEN** an engine replaces the index and the operation fails partway
- **THEN** the previous index content remains queryable

### Requirement: The engine in use is chosen at startup
When the search plugin starts, it SHALL use exactly one registered engine. If an `engine` setting names a plugin id, the engine registered by that plugin SHALL be used; otherwise the sole registered engine SHALL be used. Startup SHALL fail with an identifying message in every other case. Composition SHALL fail when `engine` names a plugin that is not selected or is disabled.

#### Scenario: No engine registered
- **WHEN** the search plugin starts and no engine is registered
- **THEN** startup fails stating that an engine plugin is required

#### Scenario: One engine and no setting
- **WHEN** one engine is registered and `engine` is not set
- **THEN** that engine is used

#### Scenario: Setting names a different plugin than the only engine
- **WHEN** one engine is registered and `engine` names another plugin
- **THEN** startup fails identifying the setting and the registered engine

#### Scenario: Two engines and no setting
- **WHEN** two engines are registered and `engine` is not set
- **THEN** startup fails identifying both and asking to set `engine`

#### Scenario: Two engines and a setting
- **WHEN** two engines are registered and `engine` names the plugin of one
- **THEN** that engine is used and the other is not

#### Scenario: Named engine plugin is not selected or is disabled
- **WHEN** `engine` names a plugin that is absent from the manifest or disabled
- **THEN** composition fails identifying the plugin

#### Scenario: Engine selected without search
- **WHEN** an engine plugin is selected and the search plugin is not
- **THEN** the engine registers but nothing uses it, and startup succeeds

### Requirement: Engines are verified by a shared conformance suite
The plugin API SHALL ship a conformance test suite that any engine adapter, including out-of-tree ones, can run against its implementation to verify upsert, delete, replace, query, filtering, pagination and ordering behaviour.

#### Scenario: An adapter runs the suite
- **WHEN** an adapter author runs the conformance suite against their engine
- **THEN** each portable behaviour is checked and failures identify the violated behaviour
