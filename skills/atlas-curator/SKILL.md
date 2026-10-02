---
name: atlas-curator
description: Writes Atlas catalog entities (System, Component, Resource, API) and relationships through the Atlas MCP server, in the right order, without duplicates, after the user confirms. Use when the user asks to add, document, register, or update a service, system, database, queue, API, or relationship in the Atlas catalog, or when atlas-scout or atlas-flow hands over a plan.
---

# Atlas Curator

The only skill that writes catalog entities.

## When to use

The user wants entities in the Atlas catalog created or updated: "add this service", "document these
databases", "register this API", or another skill (`atlas-scout`, `atlas-flow`) hands over an approved plan.
This skill writes Systems, Components, Resources, APIs, the relationships between them, and the links from Services
to API endpoints and operations. It does not
create Groups or Users (see [Unsupported requests](#unsupported-requests)) and never removes an entity. It removes a usage link only on explicit request after a dry-run.

## Workflow

### 1. Preflight and kinds

Run the preflight from the shared rules. Then learn the writable kinds:

- If `describe_kinds` exists, call it and take fields, enum values, required fields, and limits from it. It is the
  source of truth.
- If not, use [references/entities.md](references/entities.md) and tell the user it may be out of date.

Send only fields the kind defines; unknown keys are rejected by the server. Never put `relationships` in `spec`
(see [references/relationships.md](references/relationships.md)).

### 2. Gather the plan

Take the plan from the user or from `atlas-scout`/`atlas-flow`. For each item, know the kind, `name`, the spec
fields, and the relationships. Ask once which language to use for titles and descriptions (shared rules), then
draft them following [references/conventions.md](references/conventions.md). Ask about a missing required field
only if it cannot be drafted or looked up.

### 3. Owners

Groups cannot be created over MCP. List existing groups with `search_catalog` (`kind: group`) and ask the user to
choose an owner for each System, offering one choice for the whole batch. Components, Resources, and APIs
use the owner of their system unless the user says otherwise. If the intended group does not exist, stop and tell
the user to create it in Atlas. Never substitute another group.

### 4. Search before create

For every item, search by kind and name (`search_catalog`) and read the match with `get_entity` when there is one.
Mark each item `new`, `update` (fields differ), or `unchanged`. An existing entity is never created again. Matching
by name alone is not enough when the match is a different kind or clearly a different thing: ask.

### 5. Summary and confirmation

Build the change summary, one line per entity and relationship with its status and the fields set. When write tools
support `dryRun`, make a dry-run call for every create and update and build the summary from the responses, not
from a prediction. Show it, and write nothing until the user explicitly confirms. Mention API specs that will be
attached, relationships that cannot be created, and anything skipped.

### 6. Write in dependency order

1. Systems
2. Resources and APIs
3. Components
4. References between entities (`dependsOn`, `providesApis`, `consumesApis`, and any `system` not yet set)
5. Architecture Relationships (see [references/relationships.md](references/relationships.md))
6. Endpoint and Operation links, after the API specification is attached and its endpoints or operations are
   confirmed (see [references/usage-links.md](references/usage-links.md))

Components reference systems, APIs, and resources, so those must exist first. For APIs with a spec follow
[references/api-specs.md](references/api-specs.md).

**List fields are replaced, not appended.** Before changing `dependsOn`, `providesApis`, or `consumesApis`, read
the entity and send the merged list so existing values stay unless the user asked to drop them.

### 7. Ledger and failures

Keep a ledger of what you created or changed this session (kind, ref, action). After the last write, report it:
what was created, updated, left unchanged, and what was skipped or failed. If a write fails part-way, stop, list
what is already written and what is still pending, and explain that re-applying the same plan is safe because of
search-before-create. A permission error is reported with the required scope and is not retried.

## Unsupported requests

- **Group, User, or any other kind the server does not write**: explain that groups and users are managed in Atlas
  itself and create nothing.
- **Remove, delete, purge, restore an entity**: follow the no-removal rule in the shared rules.
- **Endpoints and operations themselves**: never written directly; they appear when an API spec is attached. The
  links from Services to them are written with the usage link tools
  ([references/usage-links.md](references/usage-links.md)). If those tools are missing, say the links cannot be
  recorded and ask whether to continue without them.

## References

- [references/entities.md](references/entities.md): fields, enums, and examples per kind (fallback)
- [references/api-specs.md](references/api-specs.md): attaching and verifying API specs
- [references/relationships.md](references/relationships.md): authoring relationships
- [references/usage-links.md](references/usage-links.md): linking Services to endpoints and operations
- [references/conventions.md](references/conventions.md): names, titles, descriptions, tags, owners
- [references/shared-rules.md](references/shared-rules.md): rules shared by all Atlas skills

## Shared rules

Read [references/shared-rules.md](references/shared-rules.md) before the first catalog read or write.
If that file is not available, stop and tell the user to install the full set of Atlas
skills. In short:

1. **Preflight.** Check which Atlas MCP tools exist; stop if none, name what is missing,
   continue at reduced capability only if the user agrees. Report permission errors; do not retry.
2. **Language.** Follow the user's language; ask once which language to use for titles and
   descriptions; keep `name` identifiers, field names, and enum values in English.
3. **Confirm.** Show a summary of what will change and write nothing until the user confirms.
4. **No removal.** Never remove, purge, or delete entities or flows; removal is done in the Atlas web UI.
