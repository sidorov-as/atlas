---
name: atlas-flow
description: Builds an Atlas flow in conversation, binding each step to existing catalog entities and API endpoints or operations, then saves it through the Atlas MCP server. Use when the user wants to describe, model, or edit a business or technical process, sequence, or flow in Atlas.
---

# Atlas Flow

Turns a described process into a saved flow.

## When to use

The user wants to describe, model, or edit a process, sequence, or flow in Atlas: "walk me through our checkout
process", "add a step to the onboarding flow". This skill writes **flows** itself. It never writes entities; for a
missing entity it hands off to `atlas-curator`. It never deletes a flow.

## Preflight

Run the preflight from the shared rules, then check the flow tools. See
[references/tools-and-scopes.md](references/tools-and-scopes.md) for what to do when flow tools or the
`flows:write` scope are missing. Also check that `atlas-curator` is installed.

## Rules of conduct

- One question at a time. Propose the flow's name and description yourself; do not ask about them.
- Establish the home system before drafting any steps.
- Never bind a step to something you have not confirmed exists in the catalog.
- Never invent icons: use names returned by `search_flow_icons`, or leave the icon out.
- Use the field names from the flow tool schema (snake_case inside `steps`, for example `entity_ref`,
  `next_steps`). The tool schema is the source of truth; see [references/flow-model.md](references/flow-model.md).
- Nothing is saved before the user confirms the summary.

## Workflow

### 1. Purpose

Ask what the process is for and where it starts and ends. Let the user describe it in their own words first, then
restate it briefly.

### 2. Home system

Search for systems with `search_catalog` (`kind: system`) and offer the likely matches. A flow belongs to exactly
one existing system. If none fits, say so; creating a system is `atlas-curator`'s job, so offer the handoff and wait.

### 3. Steps

Walk through the process in order, one step per question. For each step find out who or what acts and what
happens. Bind it as described in [references/binding.md](references/binding.md): an entity, a specific endpoint
or operation, another flow, an external participant, or a plain step. Pick an icon only when one clearly fits, using
`search_flow_icons`.

### 4. Branching

Ask where the process can go more than one way and where paths rejoin. A branch is a step with several labeled
transitions (`next_steps`); a rejoin is several steps whose transitions lead to the same step. The graph must be
acyclic: a loop ("retry") is modeled as a separate step or described in the step's text, not as a transition back.

### 5. Validate

Check the draft against [references/flow-model.md](references/flow-model.md): unique step ids, every transition
targets an existing step, no cycle, one reference per step, limits. Use `validate_flow` when available: it reports
every violation without saving. If the draft has a cycle, name the steps involved and fix it with the user. Without
`validate_flow`, do the checks yourself and rely on the server's error at save time.

### 6. Summary and confirmation

Show the flow: name, system, description, and each step with what it is bound to and where it leads. List
**unbound steps** (external participants standing in for missing entities) separately, with the entity each could be
bound to; see [references/unbound-steps.md](references/unbound-steps.md). Ask for confirmation. Save nothing until
the user confirms.

### 7. Save

Call `create_flow`. When `dryRun` is supported you may preview first. Report the saved flow (id, name, system). A
permission error is reported with the required scope, not retried.

### 8. After saving

If the flow has unbound steps, offer to document the missing entities through `atlas-curator`, and bind the steps
afterwards. Follow [references/unbound-steps.md](references/unbound-steps.md).

## Editing an existing flow

Find it with `list_flows`, read it with `get_flow`, and change only what the user asked for. An update **replaces**
the whole step list, so send the complete merged list (every existing step, with the change applied), never only the
new step. Validate and show a summary of the change before saving. Deleting a flow is not done by this skill: see
the no-removal rule.

## References

- [references/flow-model.md](references/flow-model.md): step fields, kinds, transitions, limits
- [references/binding.md](references/binding.md): finding the right entity, endpoint, or operation
- [references/tools-and-scopes.md](references/tools-and-scopes.md): missing tools and scopes
- [references/unbound-steps.md](references/unbound-steps.md): external steps and re-binding
- [../atlas-curator/references/shared-rules.md](../atlas-curator/references/shared-rules.md): rules shared by all Atlas
  skills

## Shared rules

Read `../atlas-curator/references/shared-rules.md` before the first catalog read or write.
If that file is not available, stop and tell the user to install the full set of Atlas
skills. In short:

1. **Preflight.** Check which Atlas MCP tools exist; stop if none, name what is missing,
   continue at reduced capability only if the user agrees. Report permission errors; do not retry.
2. **Language.** Follow the user's language; ask once which language to use for titles and
   descriptions; keep `name` identifiers, field names, and enum values in English.
3. **Confirm.** Show a summary of what will change and write nothing until the user confirms.
4. **No removal.** Never remove, purge, or delete entities or flows; removal is done in the Atlas web UI.
