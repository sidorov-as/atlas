## MODIFIED Requirements

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
