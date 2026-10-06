# search-meilisearch-engine Specification

## Purpose
Meilisearch search engine adapter: id handling, relevance, write acknowledgment, atomic replace, highlights, configuration and health.

## Requirements

### Requirement: Meilisearch is a selectable engine plugin
The adapter SHALL be an engine plugin that registers an engine through the engine contract, and selecting it in place of any other engine plugin SHALL require no change to the search plugin, sources or UI.

#### Scenario: Selected instead of the default engine
- **WHEN** a manifest selects the Meilisearch plugin and not the PostgreSQL engine plugin
- **THEN** search works through Meilisearch with the same endpoints and UI

#### Scenario: Both engines selected
- **WHEN** a manifest selects both engine plugins
- **THEN** composition fails because exactly one engine is allowed

### Requirement: Conformance
The adapter SHALL pass the shared engine conformance suite against a real instance.

#### Scenario: Suite passes
- **WHEN** the conformance suite runs against the adapter and an instance
- **THEN** all checks pass

### Requirement: Document ids survive the engine's id rules
The adapter SHALL map any search document id to a value the engine accepts as an identifier and SHALL return the original document id from queries.

#### Scenario: Id containing separators
- **WHEN** a document with an id such as `kind:key` is indexed and later found
- **THEN** the query returns the original `kind:key` id

#### Scenario: Distinct ids stay distinct
- **WHEN** two different document ids are indexed
- **THEN** both are stored as separate documents

### Requirement: Index configuration supports relevance and filtering
The adapter SHALL configure the index so that titles rank above summaries and summaries above body text, and so that results can be filtered by kind.

#### Scenario: Title outranks body
- **WHEN** one document has the term in its title and another only in its body
- **THEN** the title match ranks first

#### Scenario: Filter by kind
- **WHEN** a query lists kinds
- **THEN** only documents of those kinds are returned

### Requirement: Writes complete before success is reported
The adapter SHALL report a write as successful only after the engine has finished applying it, and SHALL report failure or timeout otherwise, so the indexing job keeps its pending changes.

#### Scenario: Engine accepts but fails to apply
- **WHEN** the engine accepts a write request and later marks it failed
- **THEN** the adapter reports failure

#### Scenario: Engine does not finish in time
- **WHEN** a write does not complete within the configured timeout
- **THEN** the adapter reports failure and the change stays pending

### Requirement: Atomic replace
The adapter SHALL implement replace-all by building a fresh index and swapping it in so readers see either the old or the new content, and SHALL remove the superseded index afterward.

#### Scenario: Rebuild while querying
- **WHEN** a rebuild runs while queries arrive
- **THEN** each query sees a complete index

#### Scenario: Rebuild fails partway
- **WHEN** building the new index fails
- **THEN** the previous index stays active and the temporary index is discarded

### Requirement: Native highlights and typo tolerance are declared
The adapter SHALL declare that it supplies highlights and typo tolerance, SHALL return highlights in a form the search plugin can render without injecting markup, and SHALL return the offsets of everything the engine matched in the returned highlight, including typos and word forms of the query. Each offset range SHALL cover the whole word it touches, where a word ends at anything that is not a letter or digit, between a lowercase and an uppercase letter, and next to a script written without spaces.

#### Scenario: Misspelled query
- **WHEN** a query contains a small typo of an indexed word
- **THEN** the intended document is still returned

#### Scenario: Misspelled query highlight
- **WHEN** a query contains a small typo of a word in the returned highlight
- **THEN** the candidate's match offsets cover that word

#### Scenario: Partly matched word
- **WHEN** the engine marks only the matched part of a word, as it does for a typo or a prefix of the query
- **THEN** the candidate's match offsets cover that whole word

#### Scenario: Word boundaries the engine uses
- **WHEN** a match touches a word joined by an underscore, hyphen or camelCase boundary to other words, or a word in a script written without spaces
- **THEN** the offsets stop at that boundary instead of covering the neighbouring word or phrase

#### Scenario: Highlight with markup in content
- **WHEN** indexed text contains HTML
- **THEN** the returned highlight carries no executable markup

#### Scenario: Offsets agree with stripped text
- **WHEN** the highlight contains HTML tags or runs of whitespace that are removed or collapsed before it is returned
- **THEN** the match offsets address the same words in the returned text as in the engine's formatted text

### Requirement: Configuration and secrets
The adapter SHALL read its endpoint, access key and timeouts from its own namespaced plugin configuration, with the key resolved as a secret and never logged, exposed to the frontend or stored in the lock.

#### Scenario: Missing key
- **WHEN** the configuration lacks a required key for an instance that enforces one
- **THEN** composition or startup fails with a message naming the setting, not its value

#### Scenario: Key not exposed
- **WHEN** the plugin's public configuration projection is read
- **THEN** it contains no key

### Requirement: Operator-configured endpoint
The adapter's connection target SHALL be operator-supplied configuration, not user input, and requests to it SHALL use only that configured target.

#### Scenario: Private network target
- **WHEN** the configured endpoint is an internal service address
- **THEN** the adapter connects to it normally

### Requirement: Health reporting
The adapter SHALL report health from the engine's own health check so the status endpoint and search requests reflect an unreachable instance.

#### Scenario: Instance down
- **WHEN** the instance is unreachable
- **THEN** health reports unhealthy and search returns the unavailable response
