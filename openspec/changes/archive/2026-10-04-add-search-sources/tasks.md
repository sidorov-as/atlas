## 1. Audit timestamps

- [x] 1.1 Add `created_at` and `updated_at` to flows with a migration in the catalog app history that fills existing rows
- [x] 1.2 Add `created_at` and `updated_at` to the database schema facet with a migration that fills existing rows
- [x] 1.3 Show both as read-only in each model's admin
- [x] 1.4 Test migrations on a database with existing rows and on a fresh database

## 2. Flow source

- [x] 2.1 Write the step-text flattening function (title, summary, external label) with tests for empty and malformed steps
- [x] 2.2 Implement the flow source: documents, id mapping, watched models including the owning system
- [x] 2.3 Implement `resolve` with existing flow read rules and owning-system access
- [x] 2.4 Register the source in the flows runtime hook
- [x] 2.5 Test rename, delete and system removal propagation

## 3. API source

- [x] 3.1 Implement endpoint and operation documents with status filtering
- [x] 3.2 Implement `resolve` using the existing endpoint read permission checks and live API naming
- [x] 3.3 Register the source in the APIs runtime hook
- [x] 3.4 Test removed and restored items, permission filtering and that raw specifications are not indexed

## 4. Database schema source

- [x] 4.1 Write the table and column flattening function from the parsed structure with a shape-guard test
- [x] 4.2 Implement documents keyed to the owning entity with title from the owner and degrade on failed parse
- [x] 4.3 Watch the facet and the owning entity; map entity changes to the schema document
- [x] 4.4 Implement `resolve` using owning-resource access and facet rules
- [x] 4.5 Register the source in the plugin runtime hook
- [x] 4.6 Test edit, owner rename, failed parse and permission filtering

## 5. Front end and labels

- [x] 5.1 Provide a display label per new kind and verify result links in the existing dialog
- [x] 5.2 Confirm routing for flow, endpoint, operation and schema links

## 6. Documentation

- [x] 6.1 Update the index schema page with each source's fields and id rules
- [x] 6.2 Document the flattening rules and the whole-entity link behaviour

## 7. Verification

- [x] 7.1 Add end-to-end tests that edit each content type and find it through the search endpoint after an indexing run
- [x] 7.2 Verify a distribution without the search plugin is unaffected
- [x] 7.3 Run the full local CI target and fix regressions
