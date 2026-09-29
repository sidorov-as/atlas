## Context

`SystemDocsTab` is a mixed read/write view. It lists document links through the read-only docs endpoint, while add, edit, and remove operations update the System's complete `metadata.links` list through the existing System PATCH endpoint. Today the component gates authoring only on whether the System is manually managed; it does not include the current session's `isReadOnly` state. Other catalog controls already combine their local eligibility rules with the session-level restriction and hide mutation affordances.

The backend remains the authorization boundary and already denies PATCH requests from read-only accounts. This change aligns the frontend with that boundary without changing permissions or API behavior.

## Goals / Non-Goals

**Goals:**

- Remove every document-link mutation entry point from the System Docs tab for read-only sessions.
- Preserve document-link read and utility actions for read-only sessions.
- Preserve the existing YAML-managed provenance restriction.
- Add regression coverage at the component boundary where the controls are composed.

**Non-Goals:**

- Changing backend authorization or the System PATCH contract.
- Changing how document links are stored, ordered, searched, or paginated.
- Introducing a generic permission abstraction for all plugin tabs.
- Auditing unrelated pages beyond the reported System Docs surface.

## Decisions

### Combine provenance and session state into one authoring predicate

The Docs tab will derive a single authoring predicate from both existing conditions: the System must be manually managed and the current session must not be read-only. The predicate will gate the top-level `Add` action, row-level edit/remove actions, and the add/edit dialog.

This keeps the two independent restrictions explicit: clearing read-only does not make a YAML-managed System editable, and changing provenance does not override a read-only account. Passing a new permission prop from `SystemDetailPage` was considered, but rejected because the tab already owns the provenance-specific behavior and can consume the same session context used by comparable mixed views.

### Hide mutation affordances instead of disabling them

Mutation controls will be absent for read-only sessions. This follows the existing `catalog-web-ui` contract and established behavior in entity lists, detail actions, relationships, and linked-service tabs. Disabled controls were considered, but would leave unusable actions visible and diverge from the stated UI convention.

### Preserve non-mutating link actions

Search, pagination, opening external links, and copying URLs remain available. These actions do not mutate Atlas state and are part of the useful read-only view.

### Cover the complete control set in one focused regression test

The System Docs component test will provide a read-only session and assert that `Add` and the table mutation-action menu are absent while document data and non-mutating actions remain available. Existing writable-session and YAML-managed tests continue to cover the other branches.

## Risks / Trade-offs

- [A future mutation control is added without using the shared local predicate] → Keep the predicate named for Docs authoring and use it at every mutation rendering site; test both the top-level and row-level surfaces.
- [Session state changes while an authoring dialog is open] → Gate the dialog itself with the derived predicate so a re-render removes writable interaction after session refresh.
- [Frontend hiding is mistaken for authorization] → Retain the existing backend read-only guard and describe the UI gate only as affordance alignment.

## Migration Plan

No data or API migration is required. Deploy the frontend change normally; rollback consists of reverting the component and test changes, while backend enforcement remains intact throughout.

## Open Questions

None.
