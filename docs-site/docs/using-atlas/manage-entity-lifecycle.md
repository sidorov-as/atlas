---
title: Manage an entity's lifecycle
description: Remove, revive, and permanently purge supported catalog entities without losing track of permissions or references.
audience:
  - catalog-user
  - operator
page-type: task
---

# Manage an entity's lifecycle

Systems, Components, Resources, and APIs use a two-stage lifecycle. **Remove**
is reversible and preserves the record; **Purge** is permanent and is available
only after removal. There is no direct catalog **Delete** action.

## Outcome

Use this process to decommission or restore an entity while preserving its
audit trail. Permanently purge it only after checking permissions and
references.

## Prerequisites

- You can open the entity's detail page. Use **Show removed** in its list to
  find an already removed entity.
- The entity is a System, Component, Resource, or API. Teams and Actors do not
  participate in this lifecycle.
- Before Purge, you have reviewed dependent catalog records, relationships,
  and Flows that may reference the entity.

## Permissions

For manual entities, Remove and Revive require owner-Group membership or a
superuser. A YAML-managed entity rejects manual Remove and Revive because its
repository is authoritative.

Purge requires a **Purge Grant** for the entity's owner Group or a superuser;
ordinary ownership is not enough. A user with appropriate Django admin model
access can record a grant in `/admin/` under **Purge grants**. A grant is
scoped to one owner Group and does not grant editing rights.

## 1. Remove a manual active entity

From the active list, choose the row action **Remove**, or open the detail page
and choose **Remove**. Confirm the prompt.

Remove changes only the lifecycle status to `removed`:

- the entity remains at the same identity and keeps its metadata, details,
  relations, and audit history;
- default lists and searches hide it, while **Show removed** reveals it;
- its kind/name remains reserved, so another manual or YAML claim cannot take
  over the same ref; and
- removing a System does not automatically mark its Components, Resources, or
  APIs removed. Their views warn that the parent System is removed.

Open **History** and confirm a **Removed** event, then enable **Show removed**
and confirm the **Removed** badge in the list and detail header.

## 2. Revive a manual removed entity

Open the removed entity's detail page and select **Revive**. The entity returns
to `active` with the same id, details, relations, and history. Verify that the
Removed badge disappears, the entity returns to the default list, and History
now contains **Revived**.

For a YAML-managed entity, do not use a manual API or UI action. Restore the
matching declaration in the same source repository and run ingestion; that
repository reconciliation revives the same record.

## 3. Prepare an irreversible purge

You can purge an entity only after it has been removed. Before selecting it:

1. Confirm that permanent deletion, rather than Revive, is the intended result.
2. Confirm your Purge Grant or superuser access for the current owner Group.
3. Inspect the error-free Relations tab and every known dependency. Active
   references block Purge with a named list.
4. For a System, rehome or remove its Components, Resources, APIs, and Flows;
   containment still blocks deletion.
5. For a Resource or API, remove or decommission active Components that depend
   on it or provide/consume it. For any entity, update active Flows or other
   references named by the server before retrying.

Do not use Purge to hide a record temporarily or work around an uncertain
ingestion conflict. It deletes the entity and permanently frees its ref after
all active blockers are resolved.

## 4. Purge and verify

On a removed detail page, select **Purge** and confirm the irreversible prompt.
Atlas checks the lifecycle state, Purge Grant, and reference blockers inside
the deletion transaction. If accepted, it deletes the catalog row and
kind-specific details, returns you to the kind list, and the old detail URL no
longer resolves.

Purge can remove some references from already removed records, but never active
references. For each named blocker, correct the reference before retrying;
do not delete its source blindly.

Verify the outcome by searching the active and **Show removed** lists, then
opening the old detail URL. Neither list should show the purged entity, and the
URL should no longer resolve. The entity's own History tab is unavailable after
Purge, so verify before leaving the page when the removal/revival audit record
matters.

## Lifecycle matrix

| Source and status | Available actions | Preservation behavior |
| --- | --- | --- |
| Manual, active | Edit, Remove | Remove retains identity, data, relations, and history. |
| Manual, removed | Revive; Purge with a grant | Revive restores the same identity; Purge removes it permanently. |
| YAML, active | Change the manifest and ingest | Manual write actions are blocked. |
| YAML, removed | Re-declare from the same repository; Purge with a grant | Re-declaration revives the same identity; Purge frees the ref. |
| Unavailable | Restore a compatible kind plugin | Edits and lifecycle writes are rejected while the handler is inactive. |

## Common problems

### Purge is not visible

The entity must be removed first, and its kind must be available. Remove an
eligible manual entity, or allow the owning repository to reconcile a
YAML-managed entity to removed before considering Purge.

### Purge is forbidden

Owner membership does not authorize Purge. Ask the appropriate administrator
to grant Purge for the entity's owner Group, or use a superuser account.

### Purge reports active references

Follow the named reference list. Correct, rehome, remove, or decommission the
active dependents through their own supported workflow, then retry. A removed
but unpurged dependent may still have structural containment constraints, so
do not assume it is harmless without checking the server response.

### A removed YAML entity blocks a repository migration or unregistration

It still claims its ref and its repository. Either restore its original source
or deliberately purge it with a grant; see
[Troubleshoot repository ingestion](troubleshoot-ingestion.md#unregister-a-repository-safely).

## Next steps

- [Choose the correct entity workflow](choose-entity-workflow.md).
- [Troubleshoot repository ingestion](troubleshoot-ingestion.md).
- [Life of an entity](../concepts/life-of-an-entity.md) for the full lifecycle
  and provenance model.
