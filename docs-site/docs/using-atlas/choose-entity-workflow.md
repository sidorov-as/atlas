---
title: Choose the correct entity workflow
description: Match manual, YAML-managed, active, removed, and unavailable entity states to the supported maintenance action.
audience:
  - catalog-user
  - operator
page-type: task
---

# Choose the correct entity workflow

Before changing an entity, check its source, lifecycle status, and kind
availability. A YAML-managed entity can be active or removed, and a retained
entity can become unavailable when its kind's plugin is inactive.

## Outcome

You will identify the authoritative source and supported action, avoiding
competing claims, repository-ownership conflicts, and confusion between
removal and plugin availability.

## Prerequisites

- You can open the entity's detail page. If it is hidden from its list, enable
  **Show removed**.
- You understand which Team owns the entity.
- For YAML-managed entities, you can identify the repository named in the
  read-only banner or contact its maintainer.

## Permissions

Reading state indicators requires only an authenticated session. Manual edits,
Remove, and Revive require membership in the owner Group or a superuser.
Purge requires a Purge Grant for that owner Group or the superuser override.
Provenance and unavailable-kind checks still reject writes after permission
checks would otherwise allow them.

## 1. Identify the three axes

Check the detail header and banners:

1. **Source:** no repository banner means `manual`; `managed by
   catalog-info.yaml in ...` means `yaml` and names the source repository.
2. **Lifecycle:** no badge means `active`; a **Removed** badge means the entity
   is retained but hidden from default lists.
3. **Availability:** normal tabs mean the kind handler is active; **This entity
   is unavailable** means the providing plugin is not active and kind-specific
   data cannot be loaded.

For definitions, see [Life of an entity](../concepts/life-of-an-entity.md).
The `deprecated` lifecycle value on a Component and deprecated warning icons on
relations are descriptive compatibility signals, not the `removed` catalog
status.

## 2. Match the state to its supported action

| Observed state | Authoritative action | What not to do |
| --- | --- | --- |
| Manual + active | Use **Edit** for data changes or **Remove** to decommission it. | Do not add a YAML declaration with the same ref unless you intend to resolve the claim through adoption. |
| Manual + removed | Use **Revive** to restore the same entity, or **Purge** with a grant to delete it permanently. | Do not create another entity with the same ref; the removed record still reserves it. |
| YAML + active | Edit the declaring `catalog-info.yaml` and run ingestion. | Do not call manual edit, Remove, or Revive; all are provenance-blocked. |
| YAML + removed | Re-declare the same ref in the same repository and ingest to revive it, or use granted **Purge** to free the ref permanently. | Do not declare the ref from another repository while the original claim remains. |
| Unavailable | Re-enable or reinstall a compatible plugin for the kind, then inspect the restored data. | Do not edit or purge while the handler is unavailable; writes cannot validate kind-specific data safely. |

Purge is the only exception to the YAML write block. It is available only to a
grant holder after the entity is removed; it cannot delete an active entity.

## 3. Decide whether adoption is appropriate

Adoption hands an **active manual** System, Component, Resource, or API to an
already registered repository. It immediately changes the provenance. The next
successful ingestion replaces the entity's fields with the repository's data.

Adopt only when all of these are true:

- the repository intentionally declares the same entity ref;
- the current manual entity is the record you want that repository to take
  over;
- a member of the current owner Group or a superuser approves the handoff; and
- you have reviewed the manifest because its next ingestion fully reconciles
  the entity rather than partially merging changes.

There is no reverse "make manual" operation. If the entity is already YAML
managed, continue using that source repository. Follow
[Troubleshoot repository ingestion](troubleshoot-ingestion.md#resolve-claim-conflicts)
for the supported adoption endpoint and other conflict cases.

## 4. Verify the chosen workflow

After the action, reload the detail page to verify the state:

- a manual edit appears in the rendered metadata and **History**;
- Remove adds the **Removed** badge and default lists hide the entity;
- Revive removes the badge and default lists show it again;
- successful repository management shows the repository read-only banner and
  the manifest's current fields;
- restoring a plugin removes the unavailable banner and restores the
  kind-specific tabs for the same entity;
- Purge returns you to the list and the old detail URL no longer resolves.

## Common problems

### Edit or Remove is missing

The entity is YAML-managed, unavailable, already removed, or a kind without a
catalog edit route (Team). Read the banner and use the matching row in the
state table.

### A YAML edit did not change the entity

Confirm that ingestion ran, inspect its warnings, and check for an active claim
conflict. Use [Register and ingest a repository](ingest-repository.md) and the
focused troubleshooting guide.

### A new declaration reports a removed-entity conflict

The removed record still owns the ref. Revive it if the original entity should
remain authoritative. Purge it only if the record should be permanently
deleted and the new claimant should be allowed to create a replacement.

### Re-enabling a plugin did not restore the entity

The distribution must select a compatible plugin version that registers the
same kind. Check plugin health and composition. Do not reconstruct the retained
row manually.

## Next steps

- [Create or edit catalog entities](create-edit-entities.md).
- [Register and ingest a repository](ingest-repository.md).
- [Manage an entity's lifecycle](manage-entity-lifecycle.md).
- Read [Life of an entity](../concepts/life-of-an-entity.md) for the model
  behind these choices.
