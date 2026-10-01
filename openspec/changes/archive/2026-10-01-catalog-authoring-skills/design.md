## Context

Atlas's MCP server gives an assistant tools to search the catalog, read and write System, Component, Resource, and API entities, and create flows. Tools alone do not carry the know-how: which fields a kind needs, that a Component needs an existing system and owner group, that Groups cannot be created over MCP, that endpoints are parsed from an attached OpenAPI or AsyncAPI document and never written directly, that a flow step may reference an entity or a specific endpoint, or that nothing should be written before the user agrees.

The shape of the solution follows a proven pattern from other catalog products: a small set of skills, each a folder with a `SKILL.md` (name, trigger description, workflow) and `references/` loaded on demand, installable into an assistant, with one skill that knows the write format and others that gather and plan.

Facts about the current MCP surface that shape the design (verified against a running stack):
- Writable kinds are System, Component, Resource, and API. Group and User are read-only.
- Component `type` is one of `service`, `website`, `library`, `worker`; `lifecycle` is `experimental`, `production`, or `deprecated`. Resource `type` is `database`, `cache`, `bucket`, `queue`, or `cluster`. API `type` is `openapi`, `grpc`, `asyncapi`, or `graphql`, with `specSource` `none`, `inline`, or `url` and `specContent` up to 2 MiB.
- Today `spec.relationships` is silently dropped and relationship tools do not exist; the `mcp-authoring-tools` change adds relationship tools, kind introspection, dry-run, and flow validation, and makes unknown fields an error.
- A flow belongs to one home system; its steps can reference an entity, an API endpoint, an API operation, an external participant, or another flow, and may not form cycles.

## Goals / Non-Goals

**Goals:**
- Let a user point an assistant at a codebase and end up with an accurate, reviewable set of catalog entities.
- Let a user describe a process in conversation and end up with a valid, well-linked flow.
- Keep the assistant honest: it checks what the server can do, shows what will change, and writes only after confirmation.
- Work in whatever language the user chooses.

**Non-Goals:**
- Ingestion manifests, C4 import, custom UI pages.
- Creating Groups or Users, or writing endpoints/operations directly.
- Removing, restoring, or purging entities, and deleting flows. The MCP server offers no restore and no dependents report yet, so a mistaken removal could not be undone through MCP; entity lifecycle belongs to a later change with those tools.
- Changing any Atlas backend or frontend behavior.

## Decisions

### D1. Three skills in `skills/`, installed together

`skills/atlas-scout`, `skills/atlas-flow`, `skills/atlas-curator`, each with `SKILL.md` and `references/`. `atlas-scout` and `atlas-flow` refer to the curator's references by relative path. The documentation says the set is installed together.

Alternatives considered:
- One skill with many references. Rejected: a single trigger description cannot separate "survey my repo", "walk me through this process", and "add this service"; assistants load skills by description, so distinct triggers matter.
- Duplicate shared reference content in each skill so each installs alone. Rejected: the entity format would exist in several places and drift.
- Per-skill install with a declared dependency. Rejected for now: depends on tooling the skills format does not guarantee.

### D2. One writer for entities; flows are written by the flow skill

`atlas-scout` and `atlas-flow` never create or change entities themselves; `atlas-scout` produces an approved plan and hands it to `atlas-curator`, and `atlas-flow`, if it finds a referenced entity missing, offers to hand a one-entity plan to `atlas-curator`. `atlas-flow` does write flows, because the flow format is its own domain and `atlas-curator` has no flow knowledge.

Alternatives considered:
- The curator writes flows too. Rejected: it would own two unrelated formats and its context would bloat.
- Each skill writes what it plans. Rejected: write ordering, idempotency, and confirmation logic would be duplicated three ways.

### D3. The MCP server is part of each skill's contract, with a preflight

Each skill's first step is to establish which Atlas MCP tools are available and refuse politely if none are, instructing the user how to connect. A skill lists the tools it requires and the tools that unlock extra behavior:

- Required for any entity work: `search_catalog`, `get_entity`, `create_entity`, `update_entity`.
- Strongly preferred: `describe_kinds` (field and enum truth), `create_relationship`/`list_relationships` (authoring relationships), `dryRun` support (accurate summaries).
- Flow work: `list_flows`, `get_flow`, `create_flow`, `update_flow`, `search_flow_icons`, `validate_flow`, and, for endpoint and operation steps, `search_api_endpoints` and `search_api_operations`.

When a preferred tool is missing, the skill says so, states what it cannot do (for example, "I can create the services but not their relationships"), and continues with the reduced behavior only if the user agrees. The skills identify the token scopes needed (`catalog:write`, `flows:write`) and report a permission error as a connection problem to fix, not as something to retry.

Alternatives considered:
- Assume every tool exists. Rejected: the tool list varies with the installed plugins and server version.
- Replace the MCP calls with a helper CLI. Rejected: it would add a second integration path to maintain.

### D4. The plan and the change summary live in the conversation

Before writing, the skill shows the user, in the conversation, the proposed entities (and relationships, flows) with a status for each of `new`, `update`, `unchanged`, `investigate`, and, once the plan is agreed, a change summary that says exactly what will be created or modified. When `dryRun` is available the summary is built from the server's dry-run response, not from the skill's own prediction. The user must confirm the summary before any write. A plan file on disk is produced only if the user asks for one.

Alternatives considered:
- Always write a plan file. Rejected: writes go straight to a live system, so the confirmation gate is the control that matters; a file adds a step without adding safety.
- Confirm once per entity. Rejected: too chatty for a survey that may produce dozens of entities; one summary per batch, with the option to expand any item.

### D5. Interview only on structural decisions, one question at a time, with a recommendation

`atlas-scout` follows the tiered approach: system boundaries, which units are Components and of what type, which stores are Resources and of what type, which interfaces are APIs and whether a spec exists, and how components relate. Each question carries the recommended answer and the evidence (file path and line) behind it. Titles, descriptions, and tags are drafted by the skill without asking.

### D6. Write order and idempotency are the curator's responsibility

Order: Systems, then Resources and APIs, then Components, then references between them (`dependsOn`, `providesApis`, `consumesApis`), then Architecture Relationships. Before each create the curator searches by name and kind; an existing entity becomes an update or "unchanged", never a duplicate. For list-valued fields it reads the entity first and sends the merged value, because a patch replaces a list rather than appending. The curator keeps a ledger of what it created in this session so a failure part-way through can be reported precisely and resumed.

No skill calls `remove_entity`, `purge_entity`, or `delete_flow`, even when asked. When the user asks to remove or delete an entity or flow, the skill explains that removal is done in the Atlas web UI, where removed entities can be restored, and offers to list what would be affected using the search tools. Entities present in the catalog but not found in code are reported as `investigate` and left alone. The one deletion a skill may perform is `delete_relationship` for a manual relationship, only on an explicit user request and after a dry-run summary, because a relationship carries no identity beyond its fields and can be recreated.

### D7. Owners come from existing Groups

Groups cannot be created over MCP, so the skill lists existing groups with `search_catalog` and asks the user to choose an owner per system (defaulting one choice across the batch). If the right group does not exist, the skill stops and tells the user to create it in Atlas, rather than substituting another.

### D8. API specs are attached, not transcribed

If the codebase contains an OpenAPI or AsyncAPI document, the curator attaches it with `specSource` `inline` and the file text as `specContent` (warning if it exceeds 2 MiB), or `specSource` `url` when the user gives a public HTTPS address. After the write it reads the entity back and reports `specResolveFailed` or sync-failure flags, and confirms the expected endpoints or operations appeared through `search_api_endpoints` or `search_api_operations`. If there is no document, the API is created with `specSource` `none` and the user is told endpoints will appear once a spec is attached. gRPC and GraphQL are stored but not parsed, and the skill says so.

### D9. Language rule

Each skill begins with the same instruction: if the user asks for a specific language, conduct all later discussion, plans, and summaries in it. The skill asks once which language to use for entity titles and descriptions and applies the answer to everything it writes. Entity `name` identifiers, field names, and enum values stay in English because the server requires them.

### D10a. Participants missing from the catalog become external steps, then are bound afterward

When a step involves an entity that is not in the catalog, `atlas-flow` records it as an external step with a clear label so the dialogue keeps its flow and the saved flow is valid at once. Before saving, the summary lists these unbound steps. After the flow is saved, the skill offers to document the missing entities through `atlas-curator`, and once they exist it re-reads the flow and replaces the external label of each corresponding step with an entity reference, saving the complete merged step list.

Alternatives considered:
- Create each missing entity through the curator in the middle of the dialogue. Rejected: it interrupts the process description with owner and system questions and creates entities from minimal information.
- Refuse to save until every participant exists in the catalog. Rejected: the user gets nothing until they have documented unrelated parts of the catalog first.

### D10. Skills are verified structurally in CI and behaviorally on a demo stack

CI checks each `SKILL.md` for valid frontmatter (name matches folder, non-empty trigger description) and that every relative reference resolves. Behavioral checking is a short manual checklist of invariants, run by a maintainer against any small repository and the local demo stack. The invariants do not depend on a particular repository: nothing is written before confirmation; a second run creates no duplicates; every proposed entity cites a file and line; ambiguous cases become questions; the language rule holds; and against a server lacking the newer tools, the skill states what it cannot do. No sample repository or expected output is shipped, because the skills are model instructions whose output is not deterministic and nothing would check such an example automatically.

Alternatives considered:
- Ship a small sample repository with an expected result. Rejected: no automated check would use it, a maintainer's manual run cannot match an exact expected result, and it would go stale unnoticed.
- Automated end-to-end tests with a model in CI. Rejected: cost, nondeterminism, and credentials in CI.
- No verification. Rejected: broken references and renamed tools would go unnoticed.

## Risks / Trade-offs

- [Skills name MCP tools and fields that later change] → The curator treats `describe_kinds` as the source of truth when available; its static reference is a fallback; the CI check catches broken file references but not tool renames, so the manual scenario is re-run when the MCP surface changes.
- [A long `SKILL.md` degrades model behavior] → Keep each `SKILL.md` to workflow and rules; move heuristics and formats into `references/` loaded on demand.
- [A write fails part-way, leaving a half-built catalog] → The ledger plus search-before-create makes a retry safe; the skill reports what exists and what is pending.
- [The assistant over-infers architecture from code] → Every proposed entity cites evidence; ambiguous cases become questions; the confirmation gate stops unreviewed writes.
- [Users install one skill and miss its dependency] → Documentation and each skill's preflight state the dependency on `atlas-curator` and stop with an install hint if it is absent.
- [Descriptions in the user's language mix with English identifiers] → The skill asks once and states the convention up front.

## Migration Plan

Additive. Merge the skills and docs; no deployment steps. Because skills rely on tools from `mcp-authoring-tools`, ship after it, or ship earlier with the reduced-capability behavior described in D3.

## Open Questions

None.
