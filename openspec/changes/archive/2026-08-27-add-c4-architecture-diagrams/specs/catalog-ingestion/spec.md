## ADDED Requirements

### Requirement: YAML manifests declare architecture relationships in entity specs
The ingestion pipeline SHALL accept outgoing `spec.relationships` declarations for supported catalog entities, validate their fields and target refs, and reconcile them as YAML-origin Architecture Relationships after entity upsert and reference resolution.

#### Scenario: Manifest declares an API call
- **WHEN** a Component manifest declares a relationship to another Component with label `Makes API calls to`, technology `REST/HTTPS`, and kind `synchronous`
- **THEN** ingestion creates or updates the matching YAML-origin Architecture Relationship

#### Scenario: Reference order within a manifest does not matter
- **WHEN** a manifest declares an Architecture Relationship whose target is defined later in the same multi-document file
- **THEN** ingestion resolves the target after entity upsert and creates the relationship

#### Scenario: Re-ingestion removes a deleted declaration
- **WHEN** a YAML-managed source entity is re-ingested without one of its prior `spec.relationships` declarations
- **THEN** the corresponding YAML-origin Architecture Relationship is removed while manual relationships remain unchanged

#### Scenario: Unresolved declared target is isolated as a manifest error
- **WHEN** a manifest declares an Architecture Relationship to an unknown target ref
- **THEN** the invalid declaration is reported and no partial YAML-origin relationship is created for it
