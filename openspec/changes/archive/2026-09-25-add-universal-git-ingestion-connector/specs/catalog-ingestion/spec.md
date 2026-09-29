## MODIFIED Requirements

### Requirement: Registered repository configuration
A Registered Repository SHALL hold `{source_id, path, default branch}` as operational config, managed via Django admin. `source_id` SHALL reference a source declared in `atlas.ingestion` plugin config; `path` SHALL be the repository's path relative to that source's `baseUrl`. No ingestion credential SHALL be stored on a Registered Repository or anywhere else in the database.

#### Scenario: Repository registered via admin
- **WHEN** an operator adds a Registered Repository through Django admin with a `source_id` and `path`
- **THEN** the ingestor includes it in the next discovery run, authenticating using the credential configured for that `source_id`

#### Scenario: Path is validated against URL injection
- **WHEN** an operator saves a Registered Repository whose `path` is empty, begins with `/`, contains a `..` segment, contains control or whitespace characters, or contains `://`
- **THEN** Django admin rejects the save with a validation error

#### Scenario: Unknown source is rejected
- **WHEN** an operator saves a Registered Repository whose `source_id` does not match any source currently declared in `atlas.ingestion` plugin config
- **THEN** Django admin rejects the save with a validation error naming the unresolved `source_id`

### Requirement: Manifest discovery via the connector interface
On each run, the connector SHALL list files matching `**/catalog-info.yaml` in each registered repository's default branch by performing a shallow, single-branch clone of that repository, and a single provider-agnostic `GitConnector` SHALL be the only v1 implementation of that interface, serving any source reachable over HTTPS or SSH.

#### Scenario: Discovery finds a nested manifest
- **WHEN** a registered repository contains `services/user-management/catalog-info.yaml`
- **THEN** the connector's `list_manifest_paths` includes that path

#### Scenario: Discovery works against a non-GitHub source
- **WHEN** a registered repository's `source_id` references a source whose `baseUrl` is a self-hosted Gitea, GitLab, or Bitbucket instance
- **THEN** discovery, fetch, and head-SHA resolution succeed identically to a `github.com`-backed source, with no provider-specific code path

## ADDED Requirements

### Requirement: Ingestion sources are deployment-level configuration, not database rows
`atlas.ingestion` plugin config SHALL declare a `sources` list, each with an `id`, `baseUrl`, `authKind` (`basic`, `bearer`, or `ssh-key`), and a `credential` resolved through the plugin configuration system's secret-reference mechanism. Sources SHALL be resolved once at process startup; a Registered Repository SHALL only ever reference a source by `id`, never embed or store a credential itself.

#### Scenario: Source credential never reaches the database
- **WHEN** an ingestion pass authenticates against a configured source
- **THEN** the credential used comes from the resolved plugin configuration, and no database row, migration, or admin form field ever holds that credential value

### Requirement: SSH sources require verified host keys
A source with `authKind: ssh-key` SHALL require either explicit known-hosts content/path or an explicit development-only opt-in to accept unknown host keys; it SHALL NOT silently trust-on-first-use, and a scheduled ingestion pass SHALL NOT block on an interactive host-key prompt.

#### Scenario: SSH source without host-key configuration fails closed
- **WHEN** a source declares `authKind: ssh-key` without known-hosts content/path or an explicit unknown-host-acceptance opt-in
- **THEN** composition or startup fails with an error naming the missing host-key configuration, rather than allowing an unverified connection at ingestion time
