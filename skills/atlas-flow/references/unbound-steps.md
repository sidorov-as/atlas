# Unbound steps

An unbound step is an `external_label` step that stands in for an entity that is missing from the catalog. Saving
with external steps is deliberate: the flow is valid at once, and the dialogue is not interrupted.

## Before saving

In the summary list each unbound step: its step id, its label, and the entity it could be bound to (suggest a kind
and name, for example "component `notification-service`"). Do not list a genuinely external party the user said
should stay external.

## After saving

If there are unbound steps, offer to document the missing entities through `atlas-curator`. If the user agrees,
hand over a one-entity-per-item plan in the curator's format (kind, name, and the fields you know; the curator asks
for owner and anything else it needs, and shows its own summary). Do not create entities yourself.

## Re-binding after the entities exist

1. Confirm the entity now exists with `search_catalog`.
2. Read the flow with `get_flow` (it may have changed since).
3. In the step list, for each corresponding step: remove `external_label`, set `entity_ref` to the new entity's
   ref, and remove any `title` or `summary` (a ref-backed step cannot have them). Change no other step.
4. Validate, show the user which steps change, and on confirmation save the **complete** merged step list with
   `update_flow`, because an update replaces the steps.
5. Report which steps are now bound and which remain external.
