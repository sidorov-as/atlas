## Why

Filling an Atlas catalog by hand, one form at a time, is slow, and the people best placed to describe a system are often looking at its code or talking through a business process. Atlas already has an MCP server, so an AI assistant can read and write the catalog, but a bare tool list does not tell the assistant how to survey a codebase, which questions to ask, in what order to write entities that reference each other, or how to build a flow from a conversation. Skills close that gap: instructions an assistant loads on demand that turn "point it at this repo" and "walk me through this process" into correct, reviewable catalog changes through the MCP server.

## What Changes

- Add a top-level `skills/` directory with three installable skills, in the same layout other skill collections use (one folder per skill, a `SKILL.md` with name and trigger description, plus on-demand `references/`):
  - `atlas-scout`: surveys a codebase, proposes a catalog model, interviews the user on structural decisions, and hands an approved plan to `atlas-curator`.
  - `atlas-flow`: builds a flow in dialogue, binding steps to existing catalog entities and API endpoints or operations, then saves it.
  - `atlas-curator`: the one skill that writes entities. It knows the writable kinds, the order entities must be created in, how to find owners, how to attach API specs, and how to author relationships.
- Every skill takes the Atlas MCP server as part of its contract: it checks which tools are available before acting and tells the user what is missing instead of guessing.
- Every write is preceded by a plan shown in the conversation and a summary of what will change, taken from the server's dry-run where available; nothing is written until the user confirms.
- Every skill carries a language rule: if the user asks for a particular language, the whole conversation continues in it, and the skill asks which language to use for entity titles and descriptions.
- Skills are documented as an installable set (installed together, because the planning skills depend on the curator), with install instructions and a short guide on the documentation site.

Out of scope: skills that create or edit ingestion manifests (a later change), importing C4 models, custom UI pages, removing or restoring entities (a later lifecycle change), and the MCP tools the skills use (delivered by the `mcp-authoring-tools` change).

## Capabilities

### New Capabilities

- `catalog-skills-distribution`: how the skills are laid out, named, installed, documented, and checked; the shared rules every skill follows (MCP preflight, language, confirmation before writes, no removal of entities or flows).
- `atlas-scout-skill`: the code-to-catalog workflow: discovery, reconciliation against the existing catalog, tiered interview, plan, handoff.
- `atlas-flow-skill`: the conversational flow-authoring workflow and the flow rules it must satisfy before saving.
- `atlas-curator-skill`: the entity-writing workflow: preflight, write order, owner lookup, API specs, relationships, idempotency, confirmation, and failure handling.

### Modified Capabilities

None. The MCP behavior the skills rely on is specified by the `mcp-authoring-tools` change; this change adds content and documentation only.

## Impact

- New `skills/` directory at the repository root (three skills, each with `SKILL.md` and `references/`).
- Documentation site: a page describing the skills, how to install them, and the MCP connection and token scopes they need.
- Root and `mcp/` README: pointers to the skills.
- A lightweight check in CI that each `SKILL.md` has valid frontmatter and that every referenced file exists.
- Depends on the `mcp-authoring-tools` change for relationship tools, kind introspection, and dry-run. Skills detect missing tools and degrade with a clear message, so they remain usable against an MCP server without them, at reduced capability.
- No backend, frontend, or schema changes.
