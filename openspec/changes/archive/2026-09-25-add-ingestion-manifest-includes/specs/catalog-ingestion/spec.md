## ADDED Requirements

### Requirement: Manifest-processing failures are persisted and admin-visible
In addition to being logged, a manifest-processing failure that is already isolated per repository-relative path (connector fetch failure, YAML parse failure, manifest schema-validation failure, and a failed or unresolved `Include` per the `ingestion-manifest-includes` capability) SHALL be recorded as an `IngestionIssue`, keyed by `(repository, path)`, viewable through Django admin without access to application logs. Recording an `IngestionIssue` SHALL NOT change the existing per-manifest failure isolation behavior: the failing path is still skipped and the rest of that run still proceeds.

#### Scenario: A fetch failure is recorded and visible in admin
- **WHEN** a registered repository's connector fails to fetch a discovered `catalog-info.yaml` path during a run
- **THEN** that failure is logged as before, and an `IngestionIssue` for that repository and path is visible in Django admin

#### Scenario: A parse failure is recorded and visible in admin
- **WHEN** a discovered manifest file's content fails to parse as YAML
- **THEN** that failure is logged as before, and an `IngestionIssue` for that repository and path is visible in Django admin

#### Scenario: A schema-validation failure is recorded and visible in admin
- **WHEN** a manifest document fails entity-kind schema validation (the existing "One invalid document doesn't block the rest" scenario)
- **THEN** that failure is logged as before, and an `IngestionIssue` for that repository and path is visible in Django admin

### Requirement: An IngestionIssue is self-clearing
An `IngestionIssue` for a given `(repository, path)` SHALL be marked inactive once that same repository and path complete a subsequent ingestion run without the failure that created it, mirroring the existing self-clearing behavior of `ConflictRecord`.

#### Scenario: A fixed manifest clears its prior issue
- **WHEN** a `catalog-info.yaml` that previously failed schema validation is corrected and the repository is re-ingested successfully
- **THEN** the corresponding `IngestionIssue` becomes inactive without being deleted

#### Scenario: A recurring failure updates the existing issue rather than duplicating it
- **WHEN** the same repository and path fail ingestion in the same way across multiple consecutive runs
- **THEN** a single `IngestionIssue` row for that `(repository, path)` has its message and last-seen time updated, rather than a new row being created per run
