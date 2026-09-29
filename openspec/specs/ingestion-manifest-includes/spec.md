# ingestion-manifest-includes Specification

## Purpose
Lets a discovered `catalog-info.yaml` compose additional manifest fragments via a `kind: Include` document, so entity declarations can be split across files within a repository while still being ingested as a single logical document pool.

## Requirements

### Requirement: `kind: Include` composes additional manifest fragments
A raw manifest document with `kind: Include` SHALL be recognized wherever an ordinary entity document can appear (a top-level document in a discovered `catalog-info.yaml`, or a document within a fragment reached by another `Include`), and SHALL NOT be treated as an entity document: it SHALL never reach entity-kind schema validation, and its `spec.paths` SHALL each be resolved, fetched, and parsed into further raw documents that are folded into the same document pool as the file that declared the `Include`.

#### Scenario: An Include document composes fragments into the pool
- **WHEN** a discovered `catalog-info.yaml` contains a `kind: Include` document with `spec.paths: [.manifests/db-catalog-info.yaml]`, alongside an ordinary `kind: Component` document
- **THEN** both the Component from the including file and every entity document found in `.manifests/db-catalog-info.yaml` are ingested from that run

#### Scenario: An Include document is never validated as an entity
- **WHEN** ingestion processes a `kind: Include` document
- **THEN** it is not passed to entity-kind schema validation and never produces an "invalid manifest document" failure on account of its own `kind`

### Requirement: Include paths resolve relative to the including file's directory
Each entry in an `Include` document's `spec.paths` SHALL be resolved relative to the repository directory containing the file in which that `Include` document appears, not the repository root. An entry that is an absolute path, contains a `..` segment, or contains a NUL or control character SHALL be rejected and reported as a failed resolution rather than fetched, and the resolved path SHALL be verified to remain within the repository checkout (including after following any symlink) immediately before it is fetched.

#### Scenario: A relative include path resolves against its own directory
- **WHEN** `services/payments/catalog-info.yaml` contains `kind: Include` with `spec.paths: [.manifests/apis-catalog-info.yaml]`
- **THEN** the fetched fragment is `services/payments/.manifests/apis-catalog-info.yaml`, regardless of the repository's overall layout

#### Scenario: An absolute include path is rejected
- **WHEN** an `Include` document declares `spec.paths: [/etc/passwd]`
- **THEN** that path is not fetched, the entry is rejected and reported as a failed resolution, and the rest of the including file's own directly-declared documents still ingest normally

#### Scenario: A traversal include path is rejected
- **WHEN** an `Include` document declares `spec.paths: [../../etc/passwd]`
- **THEN** that path is not fetched, the entry is rejected and reported as a failed resolution, and the rest of the including file's own directly-declared documents still ingest normally

#### Scenario: A symlink that escapes the checkout is rejected
- **WHEN** an `Include` document's `spec.paths` entry resolves to a path that is, or passes through, a symlink pointing outside the repository checkout
- **THEN** that path is not fetched, the entry is rejected and reported as a failed resolution, and the rest of the including file's own directly-declared documents still ingest normally

### Requirement: Include paths support glob patterns
An `Include` document's `spec.paths` entries SHALL support glob patterns in addition to explicit file paths, matched relative to the including file's directory.

#### Scenario: A glob path includes every matching fragment
- **WHEN** an `Include` document declares `spec.paths: [.manifests/*.yaml]` and that directory contains two fragment files
- **THEN** both fragments are fetched, parsed, and folded into the document pool

### Requirement: Include composition is recursive with cycle detection
A fragment reached via an `Include` document MAY itself contain further `kind: Include` documents, resolved and expanded the same way. The resolver SHALL track the set of repository-relative paths already visited in the current resolution chain, and SHALL reject (rather than infinitely recurse on) an `Include` path that revisits a path already in that chain. The resolver SHALL also enforce a maximum `Include` recursion depth and a maximum total number of files included in a single ingestion run, rejecting and reporting further expansion once either limit is reached rather than continuing unbounded.

#### Scenario: A nested Include is expanded
- **WHEN** `catalog-info.yaml` includes `.manifests/a.yaml`, and `.manifests/a.yaml` itself contains a `kind: Include` document pointing at `.manifests/b.yaml`
- **THEN** entities declared in `.manifests/b.yaml` are also ingested from that run

#### Scenario: A cycle is detected and rejected, not followed forever
- **WHEN** `.manifests/a.yaml` includes `.manifests/b.yaml`, and `.manifests/b.yaml` includes `.manifests/a.yaml` back
- **THEN** the cycle is detected, that Include is rejected and reported, and ingestion of the rest of the repository's manifests proceeds unaffected

#### Scenario: Excessive Include depth is rejected
- **WHEN** a chain of `Include` documents nests deeper than the configured maximum recursion depth, with no cycle present
- **THEN** further expansion beyond the limit is rejected and reported, and the successfully-resolved fragments up to that point still ingest

#### Scenario: Excessive total included files is rejected
- **WHEN** a single ingestion run's `Include` resolution would fetch more files than the configured maximum total
- **THEN** further fetches beyond the limit are rejected and reported, and the successfully-resolved fragments up to that point still ingest

### Requirement: An included fragment must not be named `catalog-info.yaml`
An `Include` path that resolves to a file whose basename is `catalog-info.yaml` SHALL be rejected and reported rather than fetched, since such a path would otherwise also be reachable through manifest discovery's own repository-wide walk and be ingested a second time.

#### Scenario: An include path named catalog-info.yaml is rejected
- **WHEN** an `Include` document's `spec.paths` resolves to `services/payments/extra/catalog-info.yaml`
- **THEN** that path is not fetched, the `Include` entry is rejected and reported, and the rest of the including file's own directly-declared documents still ingest normally

### Requirement: A failed or unresolved Include is isolated like any other per-manifest failure
An `Include` path or glob entry that resolves to no file, or whose fetch fails, SHALL be skipped and reported for that run, without blocking ingestion of the rest of the including file's directly-declared documents, other `Include` entries in the same document, or the rest of the repository's manifests.

#### Scenario: One broken include path doesn't block the rest of the file
- **WHEN** a `catalog-info.yaml` contains an `Include` document with two paths, one of which does not exist in the repository, alongside an ordinary `kind: System` document
- **THEN** the missing path is skipped and reported, the existing path's fragment is still ingested, and the System document is still ingested
