## 1. Collection scaffold and shared rules

- [x] 1.1 Create `skills/atlas-scout`, `skills/atlas-flow`, and `skills/atlas-curator`, each with a `SKILL.md` (frontmatter `name` equal to the folder, trigger `description`) and a `references/` folder
- [x] 1.2 Write the shared preamble used by every `SKILL.md`: MCP preflight (required and preferred tools, what to do when missing), language rule, confirmation-before-write rule, no-removal rule
- [x] 1.3 Add `skills/README.md` listing the skills, how they relate, and installation instructions

## 2. atlas-curator

- [x] 2.1 Write `SKILL.md`: preflight, kind introspection use, write order, search-before-create, read-merge-write for list fields, owner selection, summary and confirmation, ledger and partial-failure reporting
- [x] 2.2 Write `references/entities.md`: System, Component, Resource, and API fields, enums, required fields, naming rules, and an example of each, marked as the fallback when kind introspection is unavailable
- [x] 2.3 Write `references/api-specs.md`: inline versus URL, size limit, SSRF-safe fetch limits, verifying sync flags and endpoint or operation counts, gRPC and GraphQL behavior
- [x] 2.4 Write `references/relationships.md`: label, technology, interaction kinds, duplicate checking, YAML-origin rule, why relationships do not go in `spec`
- [x] 2.5 Write `references/conventions.md`: identifier style, drafting titles and descriptions in the chosen language, tags, owner lookup

## 3. atlas-scout

- [x] 3.1 Write `SKILL.md`: phases (locate, survey, reconcile, interview, plan, handoff), conversational rules, evidence citing, statuses `new`/`update`/`unchanged`/`investigate`
- [x] 3.2 Write `references/discovery.md`: detection heuristics per stack for deployable units, web frontends, workers, libraries, data stores and brokers mapped to Resource types, API specs and route definitions, inter-service calls
- [x] 3.3 Write `references/interview.md`: the structural question bank with recommended-answer templates and the topics that must not be asked about
- [x] 3.4 Write the plan format shown in conversation and the handoff text to `atlas-curator`

## 4. atlas-flow

- [x] 4.1 Write `SKILL.md`: dialogue phases (purpose, home system, steps, branching), entity and endpoint binding, validation, summary, save, edit of existing flows
- [x] 4.2 Write `references/flow-model.md`: step fields, step kinds (entity, endpoint, operation, external, nested flow), transitions and labels, `color` (not the deprecated `label_theme`), snake_case field names, limits, acyclicity, one reference kind per step, and a note that the tool schema is the source of truth for fields
- [x] 4.3 Write `references/binding.md`: how to search entities, endpoints, and operations and choose the right reference; how to treat participants missing from the catalog
- [x] 4.4 Write the handling for missing flow tools and the `flows:write` scope
- [x] 4.5 Write the unbound-step workflow: external steps for missing entities, listing them in the summary, offering curator handoff after saving, and re-binding steps through a read-merge-write update

## 5. Documentation

- [x] 5.1 Add a documentation-site page for the skills: what they do, install steps, connecting the MCP server, required token scopes, a worked example, and the language behavior
- [x] 5.2 Add the page to the site navigation and link to it from `mcp/README.md` and the root README

## 6. Checks

- [x] 6.1 Add a script that verifies each `SKILL.md` has valid frontmatter and that every relative reference in the skills collection resolves
- [x] 6.2 Add a CI workflow step running the script on changes under `skills/`
- [x] 6.3 Write the manual verification checklist and store it with the skills: nothing written before confirmation, a second run creates no duplicates, every proposed entity cites a file and line, ambiguous cases become questions, the language rule holds (including English identifiers), and a server without the newer tools produces a clear reduced-capability message; run it on any small repository for `atlas-scout` and on the demo catalog for `atlas-flow` and `atlas-curator`

## 7. Verification

- [x] 7.1 Run the structural check locally and in CI
- [x] 7.2 Run the manual checklist against the local demo stack with the `mcp-authoring-tools` change applied, and again against an MCP server without its tools to confirm reduced-capability messaging
- [x] 7.3 Run `openspec validate catalog-authoring-skills`
