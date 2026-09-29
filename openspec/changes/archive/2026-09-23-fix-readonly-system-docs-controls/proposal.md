## Why

The System Docs tab still exposes document-link mutation controls to read-only users for manually managed Systems. Although the backend rejects the resulting PATCH request, the stale affordances violate the existing read-only UI contract and lead users into operations they cannot complete.

## What Changes

- Hide the System Docs `Add` action when the current session is read-only.
- Hide document-link edit and remove row actions when the current session is read-only.
- Preserve all permitted read behavior, including listing, searching, opening, copying, and paginating document links.
- Keep the existing YAML-managed System restriction intact and combine it with the session-level read-only restriction.
- Add focused frontend regression coverage for both writable and read-only sessions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `catalog-web-ui`: Clarify that the existing read-only mutation-control requirement applies to all System Docs document-link authoring controls while preserving read-only document access.

## Impact

- Affects the standard catalog frontend's System Docs tab and its component tests.
- Uses the existing session `isReadOnly` state and existing backend authorization boundary; no API, data model, dependency, or migration changes are required.
