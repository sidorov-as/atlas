## ADDED Requirements

### Requirement: YAML ingestion fully reconciles described metadata links
Ingestion SHALL accept an optional `description` on each `metadata.links[]`
entry in `catalog-info.yaml`. On every successful upsert it SHALL replace the
YAML-managed entity's complete metadata-link list, including descriptions,
with the manifest declaration.

#### Scenario: Ingestion stores a described dashboard link
- **WHEN** a System manifest declares a link with a title, description, URL,
  and type
- **THEN** the retrieved System and its document-links API expose those four
  values

#### Scenario: Removed YAML link disappears after re-ingestion
- **WHEN** a YAML-managed System is re-ingested with one previously declared
  metadata link removed
- **THEN** that link is absent from the System's subsequent document-links API
  response

#### Scenario: YAML-managed links cannot be manually changed
- **WHEN** a user attempts to PATCH `metadata.links` on a YAML-managed System
- **THEN** the request is rejected and the manifest-derived links remain
  unchanged
