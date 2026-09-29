## Purpose

A reusable, severity-differentiated confirmation dialog (hook + component) for gating destructive or state-changing actions across the catalog frontend, replacing the native browser `window.confirm()`.

## Requirements

### Requirement: Destructive and state-changing catalog actions confirm via a styled dialog, not the native browser confirm
Any catalog frontend action that today gates on the browser's native `window.confirm()` SHALL instead gate on a Gravity UI-styled confirmation dialog, presenting the same message copy the action already uses. This applies to Remove and Purge on entity list/detail pages, Delete on Architecture Relationships, Delete on Flows, and Unlink on Endpoint/Operation linked services.

#### Scenario: Remove shows a styled dialog instead of the native confirm
- **WHEN** a user clicks Remove on an entity's list row or detail page
- **THEN** a Gravity UI dialog opens showing the existing Remove confirmation message, and no native browser `confirm()` dialog is shown

#### Scenario: Purge shows a styled dialog instead of the native confirm
- **WHEN** a user with Purge access clicks Purge on a `removed` entity's detail page
- **THEN** a Gravity UI dialog opens showing the existing Purge confirmation message, and no native browser `confirm()` dialog is shown

#### Scenario: Deleting an Architecture Relationship shows a styled dialog
- **WHEN** a user clicks the delete control on an outgoing manual Architecture Relationship in the Relations tab
- **THEN** a Gravity UI dialog opens showing the existing delete-relationship confirmation message, and no native browser `confirm()` dialog is shown

#### Scenario: Deleting a Flow shows a styled dialog
- **WHEN** a user clicks Delete on a Flow from the Flows list or a Flow's detail page
- **THEN** a Gravity UI dialog opens showing the existing delete-flow confirmation message, and no native browser `confirm()` dialog is shown

#### Scenario: Unlinking a service shows a styled dialog
- **WHEN** a user clicks Unlink on a linked service row in an Endpoint's or Operation's linked-services tab
- **THEN** a Gravity UI dialog opens showing the existing unlink confirmation message, and no native browser `confirm()` dialog is shown

### Requirement: Confirmation dialog visually distinguishes irreversible actions from reversible or non-destructive ones
The confirmation dialog SHALL render with a `danger`-styled confirm control for actions that permanently and irreversibly destroy data, and a `default`-styled confirm control for actions that are reversible or that do not destroy an entity. Purge, deleting an Architecture Relationship, and deleting a Flow are irreversible. Remove (revivable) and Unlink (removes a relation, not an entity) are not.

#### Scenario: Purge renders with danger styling
- **WHEN** the Purge confirmation dialog opens
- **THEN** its confirm control is rendered with danger styling, distinct from a default-styled confirm control

#### Scenario: Remove renders with default styling
- **WHEN** the Remove confirmation dialog opens
- **THEN** its confirm control is rendered with default (non-danger) styling

#### Scenario: Unlink renders with default styling
- **WHEN** an Unlink confirmation dialog opens
- **THEN** its confirm control is rendered with default (non-danger) styling

#### Scenario: Delete relationship and delete flow render with danger styling
- **WHEN** the delete-relationship or delete-flow confirmation dialog opens
- **THEN** its confirm control is rendered with danger styling

### Requirement: Declining or dismissing the confirmation dialog performs no action
Clicking the dialog's cancel control, clicking outside the dialog, or pressing Escape SHALL close the dialog without invoking the guarded action, leaving all state unchanged. Clicking the dialog's confirm control SHALL close the dialog and invoke the guarded action exactly once.

#### Scenario: Cancelling leaves the entity unchanged
- **WHEN** a user opens a Remove, Purge, delete-relationship, delete-flow, or Unlink confirmation dialog and clicks Cancel
- **THEN** the dialog closes and the underlying entity, relationship, flow, or link is unchanged

#### Scenario: Dismissing via outside click or Escape leaves the entity unchanged
- **WHEN** a user opens a confirmation dialog and clicks outside it or presses Escape
- **THEN** the dialog closes and the underlying entity, relationship, flow, or link is unchanged

#### Scenario: Confirming invokes the action once
- **WHEN** a user opens a confirmation dialog and clicks the confirm control
- **THEN** the dialog closes and the guarded action is invoked exactly once
