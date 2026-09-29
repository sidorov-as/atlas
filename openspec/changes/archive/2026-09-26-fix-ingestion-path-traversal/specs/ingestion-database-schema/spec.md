## MODIFIED Requirements

### Requirement: A Resource manifest may declare its Database Schema source
A `Resource` manifest document SHALL be able to declare an optional `spec.databaseSchema` with a `dialect` and a `sourceSqlPath` pointing at a `.sql` file in the repository, resolved relative to the directory of the manifest file (or included fragment, per the `ingestion-manifest-includes` capability) that declares it. A `sourceSqlPath` that is an absolute path, contains a `..` segment, or contains a NUL or control character SHALL be rejected and reported as a failed resolution rather than fetched, and the resolved path SHALL be verified to remain within the repository checkout (including after following any symlink) immediately before it is fetched. A fetched file that exceeds the configured maximum size SHALL also be rejected and reported rather than applied to the facet.

#### Scenario: A Resource declares its schema source
- **WHEN** a Resource manifest declares `spec.databaseSchema: {dialect: postgresql, sourceSqlPath: db/schema.sql}`
- **THEN** ingestion resolves `db/schema.sql` relative to that manifest's own directory and fetches its content

#### Scenario: An absolute sourceSqlPath is rejected
- **WHEN** a Resource manifest declares `spec.databaseSchema.sourceSqlPath: /etc/passwd`
- **THEN** that path is not fetched, no `DatabaseSchema` Facet write is attempted from it, and the failure is recorded as an ingestion issue while the Resource's own entity fields still upsert normally

#### Scenario: A traversal sourceSqlPath is rejected
- **WHEN** a Resource manifest declares `spec.databaseSchema.sourceSqlPath: ../../etc/passwd`
- **THEN** that path is not fetched, no `DatabaseSchema` Facet write is attempted from it, and the failure is recorded as an ingestion issue while the Resource's own entity fields still upsert normally

#### Scenario: An oversized sourceSqlPath file is rejected
- **WHEN** the file resolved from a Resource manifest's `sourceSqlPath` exceeds the configured maximum fetched-file size
- **THEN** the file is not applied to the `DatabaseSchema` Facet, and the failure is recorded as an ingestion issue while the Resource's own entity fields still upsert normally
