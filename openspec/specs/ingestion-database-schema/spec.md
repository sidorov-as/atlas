# ingestion-database-schema Specification

## Purpose
Ingestion of a Resource's `DatabaseSchema` Facet from a manifest-declared `spec.databaseSchema` (dialect and `sourceSqlPath`), via the `atlas.ingestion.facet_writers.v1` extension point, so a Resource's ER-Diagram-backing Facet stays in sync with a `.sql` file the team already maintains in its repository.

## Requirements

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

### Requirement: Ingestion applies the declared schema to the Resource's Database Schema facet
When a Resource with a declared `spec.databaseSchema` is upserted, ingestion SHALL fetch the referenced file's content and apply it to that Resource's `DatabaseSchema` Facet (dialect and parsed source SQL) if the `atlas.database-schema` plugin is active for the distribution, using the same parsing behavior the plugin's own manual editor uses. This SHALL happen after the Resource's own entity fields are upserted through the Entity Service, as a separate step that does not itself go through the Entity Service.

#### Scenario: A declared schema populates the facet
- **WHEN** a Resource manifest declaring `spec.databaseSchema` is ingested for the first time, and `atlas.database-schema` is active for the distribution
- **THEN** the Resource's `DatabaseSchema` Facet is created with the declared dialect and the fetched file's parsed contents

#### Scenario: Re-ingestion updates the facet in place
- **WHEN** a Resource's referenced `.sql` file changes and the repository is re-ingested
- **THEN** the Resource's existing `DatabaseSchema` Facet is updated to match the new content, not duplicated

#### Scenario: No effect when the plugin isn't active
- **WHEN** a Resource manifest declares `spec.databaseSchema` but the distribution does not select `atlas.database-schema`
- **THEN** ingestion of that Resource's own fields still succeeds, and no Database Schema facet write is attempted

### Requirement: Dropping the declaration clears the facet
When a Resource that previously had a `spec.databaseSchema` declaration is re-ingested without one, ingestion SHALL clear that Resource's `DatabaseSchema` Facet rather than leaving its previously-ingested content in place.

#### Scenario: Removing the declaration clears previously-ingested schema data
- **WHEN** a Resource manifest that previously declared `spec.databaseSchema` is re-ingested with that declaration removed
- **THEN** the Resource's `DatabaseSchema` Facet is cleared
